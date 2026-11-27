"""Bounded plan/check/repair workflows with one common tool set and checker."""

import json

from .constraints import evaluate
from .provider import BudgetError, ServiceError
from .tools import Tools

SEARCH = ["find_activities", "find_restaurants", "find_hotels"]
ALL_TOOLS = SEARCH + ["check_plan"]
CONDITIONS = ("baseline", "treatment", "without_feasibility", "without_repair", "strong_coordinator")


def task(case):
    return (
        "Plan a Riyadh trip from the supplied datasets. Use find_activities, find_restaurants and find_hotels. "
        "Choose one hotel and exactly two activities and two restaurants per day. "
        "Number days from 1. Never repeat an activity. Restaurants may repeat. "
        "Use only IDs returned by search tools. Match hotel and restaurant budget categories. "
        "Prioritize the requested interests. Search returns coordinates; center_id can rank nearby places. "
        "If constraints are present, meet every stated limit. Distance means the sum of straight-line "
        "great-circle legs: hotel, activity 1, restaurant 1, activity 2, restaurant 2, hotel, each day. "
        "Hotel cost is median_price times the explicit number of nights, in SAR. "
        "Each interest quota counts distinct activities over the whole trip. These are dataset checks, "
        "not live prices, road distances, opening hours or bookings. "
        "Use check_plan to inspect a complete draft when needed. "
        'A full plan has only {"hotel_id":"...","days":[{"day":1,"activities":["...","..."],'
        '"restaurants":["...","..."]}]}. Return only JSON.\nRequest: '+json.dumps(case, ensure_ascii=False)
    )


def run_workflow(case, seed, condition, backend, data, model, emit, *, coordinator_model=None,
                 max_repairs=3, request_cap=60):
    if condition not in CONDITIONS or type(max_repairs) is not int or not 0<=max_repairs<=3:
        raise ValueError("Unknown condition or repair limit")
    if type(request_cap) is not int or request_cap<1 or request_cap>60:
        raise ValueError("Per-record HTTP cap must be from 1 to 60")
    if condition == "strong_coordinator" and not coordinator_model:
        raise ValueError("Strong-coordinator condition requires an explicit model")
    start_requests = backend.count
    tools = Tools(data, case, emit)
    common = task(case)
    stage, rounds, plan, repair_attempts = None, [], None, 0
    error = None

    def invoke(role, instructions, context, allowed=ALL_TOOLS):
        nonlocal stage, repair_attempts
        stage = role
        remaining = request_cap-(backend.count-start_requests)
        if remaining<=0:
            raise BudgetError("Per-record HTTP request cap reached")
        if role in ("generalist_repair", "coordinator_repair"):
            repair_attempts += 1
        chosen = coordinator_model if condition=="strong_coordinator" and role.startswith("coordinator") else model
        # The complete search-result context is shared between serial roles, so
        # specialists do not have exclusive access to hidden candidate information.
        prompt = common+"\nRole: "+role+"\n"+instructions+"\nContext: "+json.dumps(context, ensure_ascii=False, allow_nan=False)
        emit({"kind": "agent_started", "stage": role, "model": chosen, "prompt": prompt,
              "allowed_tools": allowed, "max_requests": min(12, remaining)})
        value = backend.complete(prompt, tools, seed, chosen, emit, allowed=allowed, max_requests=min(12, remaining))
        emit({"kind": "agent_finished", "stage": role, "output": value})
        return value

    def context(extra):
        return {**extra, "search_results": [e for e in events if e.get("kind")=="tool_result"
                                             and e.get("name") in SEARCH and e.get("status")=="success"]}

    # Capture the same events that are written to the journal; no fixture data or
    # witness itinerary is ever supplied to the model.
    events = []
    original_emit = emit
    def capture(event):
        event = {**event, "stage": event.get("stage", stage)}
        events.append(event)
        original_emit(event)
    emit = capture
    tools.emit = capture

    try:
        if condition == "baseline":
            plan = invoke("generalist", "Build the complete plan. You handle preferences and feasibility.", {})
        else:
            dispatch = invoke("coordinator_dispatch", "Delegate the activity and feasibility tasks. Return JSON with activity_task and feasibility_task strings.", {}, allowed=[])
            if (not isinstance(dispatch, dict) or not all(isinstance(dispatch.get(k), str) and dispatch[k].strip()
                                                         for k in ("activity_task", "feasibility_task"))):
                raise ValueError("Coordinator returned an invalid task message")
            activities = invoke("activities", "Choose activities for each day. Return JSON with days and notes. Follow activity_task.",
                                context({"dispatch": dispatch}), allowed=["find_activities", "find_hotels"])
            if not isinstance(activities, dict):
                raise ValueError("Activity specialist returned no JSON message")
            if condition == "without_feasibility":
                plan = invoke("coordinator_plan", "Build a complete plan from the activity suggestions. Handle feasibility yourself.",
                              context({"dispatch": dispatch, "activities": activities}))
            else:
                draft = invoke("feasibility", "Build a complete draft including hotel and restaurants. Check the whole draft with check_plan. Follow feasibility_task.",
                               context({"dispatch": dispatch, "activities": activities}))
                plan = invoke("coordinator_plan", "Integrate the draft and activity suggestions into one complete plan. Resolve reported concerns.",
                              context({"activities": activities, "draft": draft}))
        limit = 0 if condition=="without_repair" else max_repairs
        for round_number in range(limit+1):
            checked = evaluate(plan, case, data)
            grounding = tools.grounding_errors(plan)
            broken = {v["rule"] for v in checked["constraints"]["violations"]}
            # Primary metrics retain M5's definitions. Grounding is a separate
            # additional success requirement, not a changed IFR definition.
            row = {"round": round_number, "plan": plan, "evaluation": checked,
                   "grounding_errors": grounding, "violation_rules": sorted(broken),
                   "fixed_since_previous": sorted(set(rounds[-1]["violation_rules"])-broken) if rounds else [],
                   "introduced_since_previous": sorted(broken-set(rounds[-1]["violation_rules"])) if rounds else [],
                   "tool_calls_so_far": sum(e["kind"]=="tool_call" for e in events)}
            rounds.append(row)
            emit({"kind": "round_evaluated", **row})
            if plan is None or (checked["constraints"]["passed"] and not grounding) or round_number==limit:
                break
            feedback = {"check": checked["constraints"], "grounding_errors": grounding}
            if condition not in ("baseline", "without_feasibility"):
                review = invoke("feasibility_review", "Review this complete plan and the exact checker findings. Return JSON describing fixes; do not replace measured findings.",
                                context({"plan": plan, **feedback}), allowed=["check_plan"])
                feedback["specialist_review"] = review
            role = "generalist_repair" if condition=="baseline" else "coordinator_repair"
            plan = invoke(role, "Repair the complete plan using these findings. Return the full plan, not a patch.",
                          context({"previous_plan": plan, **feedback}))
    except (ServiceError, BudgetError, ValueError, TypeError, KeyError) as exc:
        error = {"type": type(exc).__name__, "status": getattr(exc, "status", None), "stage": stage,
                 "message": str(exc) if isinstance(exc, (ServiceError, BudgetError)) else "Invalid workflow message or tool result"}
        emit({"kind": "workflow_failed", "error": error})
        # A failed required stage does not turn an intermediate draft into a final output.
        plan = None
    final = evaluate(plan, case, data)
    grounding = tools.grounding_errors(plan)
    return {"itinerary": plan, "evaluation": final, "grounding_errors": grounding,
            "success": final["constraints"]["passed"] and not grounding,
            "rounds": rounds, "repair_rounds": repair_attempts, "error": error,
            "http_requests": backend.count-start_requests,
            "tool_calls": sum(e["kind"]=="tool_call" for e in events),
            "RTC": 100*len({e["name"] for e in events if e["kind"]=="tool_call" and e["name"] in SEARCH})/3}
