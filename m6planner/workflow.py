"""Serial hub with typed messages and a shared HTTP budget; no live calls on import."""

from copy import deepcopy
import hashlib
import json
import time

from m5eval.generation import (GeminiBackend, RETRY_CODES, RequestBudgetExceeded,
                              build_prompt, make_tools, normalize_response,
                              requested_tool_names, utc_now)
from m5eval.scoring import load_datasets, parse_itinerary, validate_case
from .policy import Pacer, Policy, retry_delay


class MessageError(ValueError):
    pass


def decode_message(text, kind):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise MessageError("Duplicate message key")
            result[key] = value
        return result

    try:
        value = json.loads(normalize_response(text), object_pairs_hook=unique,
                           parse_constant=lambda v: (_ for _ in ()).throw(MessageError("Nonfinite JSON")))
    except (TypeError, ValueError) as error:
        raise MessageError(f"Invalid {kind} JSON") from error
    fields = {"dispatch": {"type", "activity_task", "budget_task"},
              "activities": {"type", "days", "notes"},
              "budget": {"type", "hotel_id", "days", "checks", "notes"}}
    if not isinstance(value, dict) or set(value) != fields[kind] or value["type"] != kind:
        raise MessageError(f"Invalid {kind} message envelope")
    if kind == "dispatch":
        if any(not isinstance(value[k], str) or not value[k].strip() for k in ("activity_task", "budget_task")):
            raise MessageError("Dispatch tasks must be nonempty strings")
    else:
        if not isinstance(value["days"], list) or not isinstance(value["notes"], str):
            raise MessageError("Invalid specialist message types")
        item_key = "activities" if kind == "activities" else "restaurants"
        for day in value["days"]:
            if (not isinstance(day, dict) or set(day) != {"day", item_key}
                    or type(day["day"]) is not int or not isinstance(day[item_key], list)
                    or any(not isinstance(i, str) for i in day[item_key])):
                raise MessageError("Invalid specialist day message types")
        if kind == "budget" and (not isinstance(value["hotel_id"], str) or not isinstance(value["checks"], list)
                                  or any(not isinstance(i, str) for i in value["checks"])):
            raise MessageError("Invalid budget message types")
    # Counts/matching/repetition are task outcomes, not a license for hidden repair.
    return value


def prompts(case, stage, messages, candidates):
    common = build_prompt(case)
    # Preserve all baseline task knowledge, replacing only the architecture wording.
    common = common.replace("You are a single-agent Riyadh travel planner.",
                            "You are a member of a coordinated three-agent Riyadh travel planner.")
    common = common.replace("Use all three tools:", "The team collectively uses all three tools:")
    common = common.split("Return ONLY valid JSON", 1)[0]
    context = json.dumps({"user_input": case, "messages": messages,
                          "observed_tool_results": candidates}, ensure_ascii=False, allow_nan=False)
    schemas = {
        "coordinator_dispatch": 'You are the Coordinator. Delegate the activities and budget tasks. No tools in this stage. Return ONLY JSON: {"type":"dispatch","activity_task":"...","budget_task":"..."}.',
        "activities": 'You are the Attraction and Preference specialist. Use find_activities and select the activities. Return ONLY JSON: {"type":"activities","days":[{"day":1,"activities":["id","id"]}],"notes":"..."}.',
        "budget": 'You are the Budget and Structural Feasibility specialist. Read the activities message, use find_restaurants and find_hotels, select restaurants and hotel, and report structural and budget concerns to the Coordinator. Return ONLY JSON: {"type":"budget","hotel_id":"id","days":[{"day":1,"restaurants":["id","id"]}],"checks":["..."],"notes":"..."}.',
        "coordinator_final": 'You are the Coordinator. Integrate both specialists and resolve their reported conflicts using only observed tool results. No further tool calls or conversation. Return ONLY valid JSON with hotel_id and days; each day has integer day, activities and restaurants. No markdown or explanations.',
    }
    return common + "\nRole and message format:\n" + schemas[stage] + "\nContext:\n" + context


class ControlledBackend:
    """Add HTTP-layer pacing and nested caps to the preserved pinned SDK adapter."""

    def __init__(self, backend, *, policy=None, pacer=None):
        if not isinstance(backend, GeminiBackend):
            raise TypeError("Use the preserved GeminiBackend with live or mocked HTTP")
        self.backend, self.policy = backend, policy or Policy()
        if backend.timeout_ms != self.policy.timeout_ms:
            raise ValueError("Backend timeout differs from shared policy")
        self.pacer = pacer or Pacer(self.policy.pacing_seconds)
        self.session_cap = backend.max_http_requests
        self.mode = backend.mode

    @property
    def request_count(self):
        return self.backend.request_count

    @property
    def remaining(self):
        return self.session_cap - self.request_count

    def send(self, *, prompt, tools, seed, stage_cap, attempt_start, record_start, emit):
        start = self.request_count
        limit = min(self.session_cap, record_start + self.policy.http_per_record,
                    attempt_start + self.policy.http_per_attempt, start + stage_cap)
        if start >= limit:
            raise RequestBudgetExceeded("Shared M6 HTTP cap reached")
        self.backend.max_http_requests = limit

        def capture(event):
            if event["kind"] == "http_request":
                self.pacer.before_http(emit)
                event = {**event, "started_at_utc": utc_now()}
            emit(event)

        return self.backend.send(prompt=prompt, tools=tools, seed=seed, model=self.policy.model,
                                 temperature=self.policy.temperature, maximum_remote_calls=stage_cap, emit=capture)

    def close(self):
        self.backend.close()


def usage_totals(trace):
    responses = [e for e in trace if e["kind"] == "http_response"]
    usage = [e["body"]["usageMetadata"] for e in responses if isinstance(e.get("body"), dict)
             and isinstance(e["body"].get("usageMetadata"), dict)]
    totals = {}
    for name in ("promptTokenCount", "candidatesTokenCount", "totalTokenCount", "thoughtsTokenCount", "cachedContentTokenCount"):
        values = [u[name] for u in usage if type(u.get(name)) is int and u[name] >= 0]
        totals[name] = sum(values) if values else None
    return {"observed_tokens": totals, "http_responses": len(responses), "responses_with_usage": len(usage),
            "scope": "Observed usage across all agents/attempts; missing provider usage is unknown, not zero.",
            "actual_cost_usd": None, "estimated_cost_usd": None}


def generate_condition(case, seed, condition, backend, data_dir, emit, *, clock=time.perf_counter, sleep=time.sleep):
    if condition not in ("baseline", "treatment"):
        raise ValueError("Unknown condition")
    if type(seed) is not int:
        raise ValueError("Integer requested seed required")
    validate_case(case, load_datasets(data_dir))
    policy = backend.policy
    # Reserve the full worst-case record cap before starting; never manufacture a quota failure mid-record.
    if backend.remaining < policy.http_per_record:
        raise RequestBudgetExceeded("Insufficient approved session capacity for another complete record")
    started, record_start = clock(), backend.request_count
    trace, attempts = [], []
    stage, attempt_number = None, 0
    result = {"generation_success": False, "itinerary": None, "raw_text": None,
              "normalized_text": None, "condition": condition, "provider_mode": backend.mode,
              "trace": trace, "attempts": attempts, "generation_error": None,
              "parser_policy": "Preserved M5 normalization and m5-offline-v3 strict final parser"}

    def capture(event):
        event = {**deepcopy(event), "event_number": len(trace) + 1,
                 "attempt": attempt_number, "stage": stage}
        trace.append(event)
        emit(event)

    for attempt_number in range(1, policy.max_attempts + 1):
        attempt_start, event_start = backend.request_count, len(trace)
        attempts.append({"number": attempt_number, "status": "started"})
        stage = None
        capture({"kind": "attempt_started", "started_at_utc": utc_now()})
        messages, tool_results = {}, []  # No abandoned attempt state reaches a new attempt.
        try:
            all_tools = make_tools(data_dir, capture)
            by_name = {tool.__name__: tool for tool in all_tools}
            stages = [("baseline", policy.http_per_attempt, all_tools)] if condition == "baseline" else [
                ("coordinator_dispatch", policy.coordinator_dispatch, []),
                ("activities", policy.activities, [by_name["find_activities"]]),
                ("budget", policy.budget, [by_name["find_restaurants"], by_name["find_hotels"]]),
                ("coordinator_final", policy.coordinator_final, []),
            ]
            for stage, cap, tools in stages:
                prompt = build_prompt(case) if condition == "baseline" else prompts(case, stage, messages, tool_results)
                capture({"kind": "agent_started", "prompt": prompt,
                         "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                         "http_budget": cap, "tools": [t.__name__ for t in tools]})
                offset = len(trace)
                output = backend.send(prompt=prompt, tools=tools, seed=seed, stage_cap=cap,
                                      attempt_start=attempt_start, record_start=record_start, emit=capture)
                capture({"kind": "agent_response", "raw_text": output.get("text"),
                         "response": output.get("response"), "history": output.get("history")})
                tool_results.extend({"name": e["name"], "result": deepcopy(e["result"])} for e in trace[offset:]
                                    if e["kind"] == "tool_result" and e.get("status") == "success")
                if stage in ("baseline", "coordinator_final"):
                    result.update(raw_text=output.get("text"), normalized_text=normalize_response(output.get("text")))
                    itinerary, errors = parse_itinerary(result["normalized_text"])
                    result.update(itinerary=itinerary, parse_errors=errors, generation_success=itinerary is not None)
                    if itinerary is None:
                        raise MessageError("Final output failed the preserved M5 JSON parser")
                else:
                    kind = "dispatch" if stage == "coordinator_dispatch" else stage
                    messages[kind] = decode_message(output.get("text"), kind)
                    capture({"kind": "message", "sender": stage, "payload": deepcopy(messages[kind])})
            result["generation_error"] = None
            attempts[-1]["status"] = "completed"
            capture({"kind": "attempt_completed", "finished_at_utc": utc_now()})
            break
        except Exception as error:
            code = getattr(error, "code", None)
            result.update(generation_success=False, itinerary=None,
                          generation_error={"type": type(error).__name__, "code": code, "stage": stage,
                                            "message": str(error) if isinstance(error, (MessageError, RequestBudgetExceeded))
                                            else "See sanitized provider events and recorded error type"})
            attempts[-1].update(status="failed", error=deepcopy(result["generation_error"]))
            capture({"kind": "attempt_failed", "error": deepcopy(result["generation_error"]), "finished_at_utc": utc_now()})
            if code not in RETRY_CODES or attempt_number == policy.max_attempts:
                break
            delay = retry_delay(trace[event_start:], attempt_number)
            before = clock()
            sleep(delay)
            capture({"kind": "retry_wait", "requested_ms": delay * 1000, "elapsed_ms": (clock() - before) * 1000})

    result["tool_calls"] = requested_tool_names(trace, attempt=attempt_number)
    result["all_attempt_tool_calls"] = requested_tool_names(trace)
    result["executed_tool_calls"] = [e["name"] for e in trace if e["kind"] == "tool_call" and e["attempt"] == attempt_number]
    result["tool_coverage_scope"] = "Distinct required names in first-candidate HTTP responses, across all agents in final workflow attempt"
    total_ms = (clock() - started) * 1000
    pacing_ms = sum(e["elapsed_ms"] for e in trace if e["kind"] == "pacing_wait")
    retry_ms = sum(e["elapsed_ms"] for e in trace if e["kind"] == "retry_wait")
    result["timing"] = {"system_wall_ms": total_ms, "pacing_wait_ms": pacing_ms, "retry_wait_ms": retry_ms,
                        "processing_ms": max(0, total_ms - pacing_ms - retry_ms),
                        "scope": "Once per case/seed/condition; includes tools, logging, attempts and scheduled waits; excludes setup/download"}
    result["usage"] = usage_totals(trace)
    result["http_requests"] = backend.request_count - record_start
    return result
