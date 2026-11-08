"""Append-only evidence records for future approved experiments."""

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re

from .scoring import score_itinerary, tool_coverage

SENSITIVE_FIELDS = {"apikey", "authorization", "accesstoken", "refreshtoken", "idtoken",
                    "clientsecret", "password", "secret", "credentials", "cookie", "setcookie"}
SECRET = re.compile(r"AIza[0-9A-Za-z_-]{30,}|(?:ghp_|github_pat_)[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|(?i:Bearer)\s+[A-Za-z0-9_.~+/-]{16,}")


def _safe(value):
    if isinstance(value, dict):
        if any(not isinstance(k, str) for k in value):
            raise ValueError("Evidence object keys must be strings")
        return {k: "[REDACTED]" if re.sub(r"[^a-z]", "", k.lower()) in SENSITIVE_FIELDS else _safe(v)
                for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe(v) for v in value]
    if isinstance(value, str) and SECRET.search(value):
        raise ValueError("Credential-like text in evidence; redact before saving")
    return value


def build_record(case, seed, generation, datasets, metadata, *, experiment_version, run_id):
    if (type(seed) is not int or not isinstance(run_id, str) or not run_id
            or not isinstance(experiment_version, str) or not experiment_version):
        raise ValueError("Explicit run ID, experiment version and integer seed required")
    if type(generation.get("generation_success")) is not bool:
        raise ValueError("Record the actual generation_success status explicitly")
    for key in ("model", "temperature", "code_commit", "dataset_sha256"):
        if key not in metadata:
            raise ValueError(f"Missing metadata: {key}")
    itinerary = generation.get("itinerary")
    if not generation["generation_success"] and itinerary is not None:
        raise ValueError("A failed generation cannot also contain a completed itinerary")
    score = score_itinerary(itinerary, case, datasets)
    return _safe({
        "run_id": run_id, "experiment_version": experiment_version,
        "case_id": case["case_id"], "seed": seed, "user_input": deepcopy(case),
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "generation_success": generation["generation_success"],
        "generation_result": deepcopy(generation), "evaluation": score,
        "RTC": tool_coverage(generation.get("tool_calls")),
        "metadata": deepcopy(metadata),
        "trace_available": isinstance(generation.get("trace"), list) and bool(generation["trace"]),
    })


def save_record(path, record):
    path = Path(path)
    payload = json.dumps(_safe(record), ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    payload.encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as f:
        f.write(payload)
