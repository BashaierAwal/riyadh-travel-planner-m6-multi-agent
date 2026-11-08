"""Gemini adapter with observable tool and HTTP evidence."""

from copy import deepcopy
from datetime import datetime, timezone
from functools import wraps
import hashlib
import importlib.metadata
import inspect
import json
import math
from pathlib import Path
import time
from types import FunctionType

import numpy as np
import pandas as pd

from . import baseline_tools
from .records import SECRET, _safe
from .scoring import parse_itinerary

SDK_VERSION = "1.30.0"
DEFAULT_MODEL = "gemini-3.5-flash-lite"
POLICY_VERSION = "m5-gemini-v3"
RETRY_CODES = {429, 500, 502, 503, 504}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def build_prompt(case):
    trip_duration, interests, budget_level = (case[k] for k in ("trip_duration", "interests", "budget_level"))
    return (
        "You are a single-agent Riyadh travel planner. "
        f"Plan a {trip_duration}-day trip. "
        f"User interests: {json.dumps(interests)}. "
        f"Budget level: {budget_level}. "
        "Use all three tools: find_activities, "
        "find_restaurants, and find_hotels. "
        "Select exactly one hotel for the whole trip. "
        "Select exactly two activities and two restaurants per day. "
        "Do not repeat activities. "
        "Only select place_ids returned by the tools. "
        "Use the requested budget level for hotels and restaurants. "
        "Prioritize activities matching the user's interests. "
        "Return ONLY valid JSON with keys hotel_id and days. "
        "Each day must contain day, activities, and restaurants. "
        "Activities and restaurants must each contain exactly two IDs. "
        "Do not include markdown or explanations."
    )


def json_safe(value):
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, (float, np.floating)):
        return float(value) if math.isfinite(float(value)) else None
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def normalize_response(text):
    """Apply the archived fence/prefix normalization; retain the untouched text separately."""
    if not isinstance(text, str):
        return None
    candidate = text.strip()
    if candidate.startswith("json\n") and candidate[5:].lstrip().startswith("{"):
        candidate = candidate[5:].lstrip()
    if candidate.startswith("```"):
        candidate = candidate.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    return candidate


def requested_tool_names(trace, *, attempt=None):
    names = []
    for event in trace:
        if event["kind"] != "http_response" or (attempt is not None and event["attempt"] != attempt):
            continue
        body = event.get("body")
        if not isinstance(body, dict):
            continue
        candidates = body.get("candidates")
        if not isinstance(candidates, list):
            continue
        for candidate in candidates[:1]:
            if not isinstance(candidate, dict) or not isinstance(candidate.get("content"), dict):
                continue
            parts = candidate["content"].get("parts", [])
            if not isinstance(parts, list):
                continue
            for part in parts:
                call = part.get("functionCall") if isinstance(part, dict) else None
                if isinstance(call, dict) and isinstance(call.get("name"), str):
                    names.append(call["name"])
    return names


def make_tools(data_dir, emit):
    namespace = {"pd": pd, "INTEREST_OPTIONS": baseline_tools.INTEREST_OPTIONS,
                 "BUDGET_OPTIONS": baseline_tools.BUDGET_OPTIONS}
    for name in ("activities", "restaurants", "hotels"):
        namespace[name] = pd.read_csv(Path(data_dir) / f"{name}.csv", float_precision="round_trip")
    names = ("search_activities", "search_restaurants", "search_hotels",
             "find_activities", "find_restaurants", "find_hotels")
    for name in names:
        original = getattr(baseline_tools, name)
        function = FunctionType(original.__code__, namespace, name, original.__defaults__, original.__closure__)
        function.__annotations__ = original.__annotations__.copy()
        function.__doc__ = original.__doc__
        namespace[name] = function

    def logged(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            bound = inspect.signature(function).bind(*args, **kwargs)
            bound.apply_defaults()
            call = {"kind": "tool_call", "name": function.__name__,
                    "arguments": json_safe(deepcopy(bound.arguments)), "started_at_utc": utc_now()}
            emit(call)
            try:
                result = json_safe(function(*args, **kwargs))
                emit({"kind": "tool_result", "name": function.__name__, "result": deepcopy(result),
                      "status": "success", "finished_at_utc": utc_now()})
                return result
            except Exception as error:
                emit({"kind": "tool_result", "name": function.__name__, "status": "error",
                      "error_type": type(error).__name__, "finished_at_utc": utc_now()})
                raise
        return wrapper

    return [logged(namespace[name]) for name in names[3:]]


class RequestBudgetExceeded(RuntimeError):
    pass


class ProviderFailure(RuntimeError):
    def __init__(self, error_type, code, message):
        super().__init__(message)
        self.error_type, self.code = error_type, code


class GeminiBackend:
    """Explicitly approved, request-capped client; construction itself makes no model call."""

    def __init__(self, api_key, *, allow_live=False, max_http_requests=10, timeout_ms=30000,
                 mock_transport=None):
        if allow_live is not True:
            raise PermissionError("Live Gemini calls require explicit approval")
        if not isinstance(api_key, str) or len(api_key) < 8:
            raise ValueError("A nonempty API key is required; never put it in the notebook")
        if type(max_http_requests) is not int or max_http_requests < 1:
            raise ValueError("A positive HTTP-request cap is required")
        if type(timeout_ms) is not int or timeout_ms < 1:
            raise ValueError("timeout_ms must be positive")
        if importlib.metadata.version("google-genai") != SDK_VERSION:
            raise RuntimeError(f"Install the pinned google-genai=={SDK_VERSION}")
        import httpx
        from google import genai
        from google.genai import types
        if getattr(genai, "__version__", None) != SDK_VERSION:
            raise RuntimeError("Restart the runtime after installing the pinned Gemini SDK")
        if mock_transport is not None and not isinstance(mock_transport, httpx.MockTransport):
            raise ValueError("Tests may inject only an httpx.MockTransport")
        self.mode = "sdk_mock" if mock_transport is not None else "live"
        self.request_count = 0
        self.max_http_requests = max_http_requests
        self._emit = None
        self._types = types
        self._api_key = api_key
        backend = self

        class RecordingTransport(httpx.BaseTransport):
            def __init__(self):
                self.wrapped = mock_transport if mock_transport is not None else httpx.HTTPTransport(retries=0)

            def handle_request(self, request):
                if backend.request_count >= backend.max_http_requests:
                    raise RequestBudgetExceeded("Approved HTTP-request cap reached")
                if backend._emit is None:
                    raise RuntimeError("An evidence sink is required before sending")
                backend.request_count += 1
                number = backend.request_count
                body = json.loads(request.content)
                backend._emit(backend.sanitize({"kind": "http_request", "request_number": number,
                                              "method": request.method, "path": request.url.path,
                                              "body": body, "started_at_utc": utc_now()}))
                start = time.perf_counter()
                try:
                    response = self.wrapped.handle_request(request)
                    response.read()
                    try:
                        body = response.json()
                    except ValueError:
                        body = {"non_json_body": response.text}
                    backend._emit(backend.sanitize({"kind": "http_response", "request_number": number,
                                                  "status_code": response.status_code, "body": body,
                                                  "elapsed_ms": 1000*(time.perf_counter()-start),
                                                  "retry_after": response.headers.get("retry-after"),
                                                  "finished_at_utc": utc_now()}))
                    return response
                except Exception as error:
                    backend._emit({"kind": "http_failure", "request_number": number,
                                   "error_type": type(error).__name__, "finished_at_utc": utc_now()})
                    raise

            def close(self):
                self.wrapped.close()

        self._client = genai.Client(vertexai=False, api_key=api_key, http_options=types.HttpOptions(
            timeout=timeout_ms, retry_options=types.HttpRetryOptions(attempts=1),
            client_args={"transport": RecordingTransport(), "trust_env": False}))
        self.timeout_ms = timeout_ms

    def sanitize(self, value):
        def clean(item):
            if isinstance(item, dict):
                return {k: clean(v) for k, v in item.items()}
            if isinstance(item, (list, tuple)):
                return [clean(v) for v in item]
            if isinstance(item, str):
                return SECRET.sub("[REDACTED]", item.replace(self._api_key, "[REDACTED]"))
            return json_safe(item)
        return _safe(clean(value))

    def send(self, *, prompt, tools, seed, model, temperature, maximum_remote_calls, emit):
        if self._emit is not None:
            raise RuntimeError("Concurrent backend use is not supported")
        self._emit = emit
        try:
            response = self._client.models.generate_content(
                model=model, contents=prompt,
                config=self._types.GenerateContentConfig(
                    tools=tools, temperature=temperature, seed=seed,
                    automatic_function_calling=self._types.AutomaticFunctionCallingConfig(
                        maximum_remote_calls=maximum_remote_calls, ignore_call_history=False)))
            return {"text": self.sanitize(response.text),
                    "response": self.sanitize(response.model_dump(mode="json", exclude_none=True)),
                    "history": self.sanitize([m.model_dump(mode="json", exclude_none=True)
                                              for m in (response.automatic_function_calling_history or [])])}
        except RequestBudgetExceeded:
            raise
        except Exception as error:
            raise ProviderFailure(type(error).__name__, getattr(error, "code", None),
                                  self.sanitize(str(error))) from None
        finally:
            self._emit = None

    def close(self):
        # The preserved 1.30.0 client predates the public Client.close method.
        self._client._api_client._httpx_client.close()


def generate(case, seed, backend, data_dir, emit, *, model=DEFAULT_MODEL, temperature=0,
             max_attempts=3, maximum_remote_calls=10, sleep=time.sleep):
    from .scoring import load_datasets, validate_case
    validate_case(case, load_datasets(data_dir))
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("An explicit model ID is required")
    if type(temperature) not in (int, float) or temperature != 0:
        raise ValueError("The frozen baseline requires temperature 0")
    if type(max_attempts) is not int or not 1 <= max_attempts <= 3:
        raise ValueError("Use one to three bounded attempts")
    if type(maximum_remote_calls) is not int or not 1 <= maximum_remote_calls <= 10:
        raise ValueError("Use one to ten remote calls per SDK attempt")
    prompt = build_prompt(case)
    trace, attempts = [], []

    def capture(event):
        event = {**event, "event_number": len(trace)+1, "attempt": len(attempts)}
        trace.append(event)
        emit(event)

    tools = make_tools(data_dir, capture)
    result = {"generation_success": False, "itinerary": None, "raw_text": None,
              "normalized_text": None, "model": model, "prompt": prompt,
              "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
              "tool_calls": [], "trace": trace, "attempts": attempts,
              "parser_policy": "archived prefix/fence normalization plus strict v3 JSON parsing",
              "provider_mode": backend.mode, "provider_history": None, "response": None}
    started = time.perf_counter()
    for number in range(1, max_attempts+1):
        attempt = {"number": number, "started_at_utc": utc_now(), "status": "started"}
        attempts.append(attempt)
        capture({"kind": "attempt_started", "started_at_utc": attempt["started_at_utc"]})
        try:
            output = backend.send(prompt=prompt, tools=tools, seed=seed, model=model,
                                  temperature=temperature, maximum_remote_calls=maximum_remote_calls, emit=capture)
            result.update(raw_text=output.get("text"), response=output.get("response"),
                          provider_history=output.get("history"))
            result["normalized_text"] = normalize_response(result["raw_text"])
            itinerary, errors = parse_itinerary(result["normalized_text"])
            result["parse_errors"] = errors
            result["generation_success"] = itinerary is not None
            result["itinerary"] = itinerary
            result["generation_error"] = None if itinerary is not None else {
                "type": "ParseError", "code": None, "message": "Response did not parse as an itinerary object"}
            attempt.update(status="response_received", finished_at_utc=utc_now())
            capture({"kind": "model_response", "raw_text": result["raw_text"],
                     "normalized_text": result["normalized_text"], "parse_errors": errors,
                     "response": result["response"], "history": result["provider_history"]})
            break
        except Exception as error:
            code = getattr(error, "code", None)
            attempt.update(status="failed", finished_at_utc=utc_now(), error_type=type(error).__name__, code=code)
            result["generation_error"] = {"type": type(error).__name__, "code": code,
                                          "provider_error_type": getattr(error, "error_type", None),
                                          "message": str(error) if isinstance(error, (ProviderFailure, RequestBudgetExceeded)) else "See recorded error type"}
            capture({"kind": "attempt_failed", "error": result["generation_error"]})
            if code not in RETRY_CODES or number == max_attempts:
                break
            delay = 5 * number
            capture({"kind": "retry_wait", "seconds": delay})
            sleep(delay)
    result["executed_tool_calls"] = [event["name"] for event in trace
                                     if event["kind"] == "tool_call" and event["attempt"] == len(attempts)]
    if backend.mode == "fixture":
        result["all_attempt_tool_calls"] = [event["name"] for event in trace if event["kind"] == "tool_call"]
        result["tool_calls"] = result["executed_tool_calls"].copy()
    else:
        result["all_attempt_tool_calls"] = requested_tool_names(trace)
        result["tool_calls"] = requested_tool_names(trace, attempt=len(attempts))
    result["tool_coverage_scope"] = "model-requested names in final attempt only; execution names recorded separately; fixture names come from local tools"
    result["wall_time_ms"] = 1000*(time.perf_counter()-started)
    return result
