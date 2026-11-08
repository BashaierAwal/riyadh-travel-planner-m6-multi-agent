"""Shared, bounded execution policy for BOTH experimental conditions."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import math
import time

from m5eval.generation import DEFAULT_MODEL


@dataclass(frozen=True)
class Policy:
    model: str = DEFAULT_MODEL
    temperature: int = 0
    timeout_ms: int = 30000
    max_attempts: int = 3
    http_per_attempt: int = 10
    coordinator_dispatch: int = 1
    activities: int = 4
    budget: int = 4
    coordinator_final: int = 1
    pacing_seconds: int = 12
    sdk_retry_attempts: int = 1

    def __post_init__(self):
        # One fixed preregistered policy; changes require a new policy version.
        expected = (DEFAULT_MODEL, 0, 30000, 3, 10, 1, 4, 4, 1, 12, 1)
        if tuple(asdict(self).values()) != expected or any(
                type(v) is not int for k, v in asdict(self).items() if k != "model"):
            raise ValueError("Use the frozen M6 policy; version and approve policy changes separately")

    @property
    def http_per_record(self):
        return self.http_per_attempt * self.max_attempts


class Pacer:
    """One process-wide start-to-start scheduler, retained across cases/conditions."""

    def __init__(self, seconds=12, *, clock=time.perf_counter, sleep=time.sleep):
        self.seconds, self.clock, self.sleep = seconds, clock, sleep
        self.last_start = None

    def before_http(self, emit):
        delay = 0 if self.last_start is None else max(0, self.last_start + self.seconds - self.clock())
        if delay:
            start = self.clock()
            self.sleep(delay)
            emit({"kind": "pacing_wait", "requested_ms": delay * 1000,
                  "elapsed_ms": (self.clock() - start) * 1000})
        self.last_start = self.clock()


def retry_delay(events, attempt, *, now=None):
    """Honor both HTTP Retry-After forms and Google RetryInfo, in addition to 5/10s."""
    delays = [5 * attempt]
    now = now or datetime.now(timezone.utc)
    for event in events:
        if event.get("kind") != "http_response":
            continue
        raw = event.get("retry_after")
        if raw:
            try:
                delays.append(max(0, float(raw)))
            except (ValueError, TypeError):
                try:
                    delays.append(max(0, (parsedate_to_datetime(raw) - now).total_seconds()))
                except (ValueError, TypeError, OverflowError):
                    pass
        body = event.get("body") or {}
        error = body.get("error", {}) if isinstance(body, dict) else {}
        details = error.get("details", []) if isinstance(error, dict) else []
        for detail in details if isinstance(details, list) else []:
            if isinstance(detail, dict) and str(detail.get("@type", "")).endswith("google.rpc.RetryInfo"):
                raw_delay = detail.get("retryDelay", "")
                try:
                    delays.append(max(0, float(raw_delay.removesuffix("s"))))
                except (ValueError, TypeError, AttributeError):
                    pass
    return max(d for d in delays if math.isfinite(d))
