"""Request-capped Gemini REST client with explicit tool calls and saved evidence.

No model call occurs on import. Credentials are read from an environment variable
or passed from Colab Secrets and are never written to evidence.
"""

import json
import re
import time
import urllib.error
import urllib.request

from .tools import declarations


class ServiceError(RuntimeError):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


class BudgetError(RuntimeError):
    pass


def clean_json(text):
    if not isinstance(text, str):
        return None
    raw = text.strip()
    if raw.startswith("```") and raw.endswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    def unique(pairs):
        result = {}
        for k, v in pairs:
            if k in result:
                raise ValueError("Duplicate JSON key")
            result[k] = v
        return result
    try:
        value = json.loads(raw, object_pairs_hook=unique,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))
        return value if isinstance(value, dict) else None
    except (ValueError, TypeError, RecursionError):
        return None


class Gemini:
    mode = "live"

    def __init__(self, key, max_requests, *, pacing=12, timeout=60, transport=None, clock=time.monotonic, sleep=time.sleep):
        if not isinstance(key, str) or len(key)<8:
            raise ValueError("A credential is required; do not save it in source or notebooks")
        if type(max_requests) is not int or max_requests<1:
            raise ValueError("Positive session request cap required")
        if pacing<12 or timeout<=0:
            raise ValueError("Use at least 12-second pacing and a positive timeout")
        self._key, self.cap, self.count = key, max_requests, 0
        self.pacing, self.timeout, self.clock, self.sleep = pacing, timeout, clock, sleep
        self.last = None
        self.transport = transport
        if transport:
            self.mode = "fixture"

    def sanitize(self, value):
        if isinstance(value, str):
            return re.sub(r"AIza[0-9A-Za-z_-]{20,}", "[REDACTED]", value.replace(self._key, "[REDACTED]"))
        if isinstance(value, list):
            return [self.sanitize(v) for v in value]
        if isinstance(value, dict):
            return {k: self.sanitize(v) for k, v in value.items()}
        return value

    def request(self, model, body, emit):
        if not isinstance(model, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", model):
            raise ValueError("Explicit model ID required")
        if self.count>=self.cap:
            raise BudgetError("Session request limit reached")
        delay = self.pacing if self.last is None else max(0, self.last+self.pacing-self.clock())
        if delay:
            before = self.clock()
            self.sleep(delay)
            emit({"kind": "pacing_wait", "requested_seconds": delay, "elapsed_seconds": self.clock()-before})
        self.last = self.clock()
        self.count += 1
        emit({"kind": "http_request", "number": self.count, "model": model, "body": self.sanitize(body)})
        before = self.clock()
        try:
            if self.transport:
                response = self.transport(model, body)
            else:
                request = urllib.request.Request(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                    data=json.dumps(body, allow_nan=False).encode(),
                    headers={"Content-Type": "application/json", "x-goog-api-key": self._key}, method="POST")
                with urllib.request.urlopen(request, timeout=self.timeout) as stream:
                    response = json.load(stream)
            emit({"kind": "http_response", "number": self.count, "status": 200,
                  "body": self.sanitize(response), "elapsed_seconds": self.clock()-before})
            return response
        except urllib.error.HTTPError as error:
            # Retain response evidence but never the request headers or credential.
            raw = error.read().decode("utf-8", errors="replace")
            emit({"kind": "http_response", "number": self.count, "status": error.code,
                  "body": self.sanitize(raw), "retry_after": error.headers.get("Retry-After"),
                  "elapsed_seconds": self.clock()-before})
            raise ServiceError(error.code, f"Provider returned HTTP {error.code}; batch stopped") from None
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            emit({"kind": "http_failure", "number": self.count, "type": type(error).__name__})
            raise ServiceError(None, "Connection or timeout failure; batch stopped") from None

    def complete(self, prompt, tools, seed, model, emit, *, allowed, max_requests=12):
        contents = [{"role": "user", "parts": [{"text": prompt}]}]
        for _ in range(max_requests):
            body = {"contents": contents, "generationConfig": {"temperature": 0, "seed": seed, "maxOutputTokens": 8192}}
            if allowed:
                body["tools"] = [{"functionDeclarations": declarations(allowed)}]
            response = self.request(model, body, emit)
            candidates = response.get("candidates", [])
            if not candidates or not isinstance(candidates[0].get("content"), dict):
                return None
            content = candidates[0]["content"]
            parts = content.get("parts", [])
            calls = [p["functionCall"] for p in parts if "functionCall" in p]
            if len(calls)>20:
                raise BudgetError("More than 20 tool calls in one model response")
            if not calls:
                text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
                emit({"kind": "model_output", "model": model, "raw_text": self.sanitize(text)})
                return clean_json(text)
            # Retain the full content including any thought signatures when continuing.
            contents.append(content)
            results = []
            for call in calls:
                name = call.get("name")
                if name not in allowed:
                    value = {"error": "Tool is unavailable in this stage"}
                else:
                    value = tools.call(name, call.get("args", {}))
                response_value = {"name": name, "response": {"result": value}}
                if "id" in call:
                    response_value["id"] = call["id"]
                results.append({"functionResponse": response_value})
            contents.append({"role": "user", "parts": results})
        raise BudgetError("Model stage request limit reached")
