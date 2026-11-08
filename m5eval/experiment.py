"""Versioned run storage and resumable, explicitly capped experiments."""

from dataclasses import asdict, dataclass
from copy import deepcopy
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re

from . import SCORER_VERSION
from .evaluate import ROOT, V2, read_json, sha256, verify_import
from .generation import DEFAULT_MODEL, POLICY_VERSION, SDK_VERSION, generate, utc_now
from .records import _safe, build_record, save_record
from .scoring import load_datasets, validate_case
from .statistics import summarize


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class RunSettings:
    model: str = DEFAULT_MODEL
    temperature: float = 0
    max_attempts: int = 3
    maximum_remote_calls: int = 10

    def __post_init__(self):
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("Explicit model ID required")
        if type(self.temperature) not in (int, float) or self.temperature != 0:
            raise ValueError("The frozen baseline requires temperature 0")
        if type(self.max_attempts) is not int or not 1 <= self.max_attempts <= 3:
            raise ValueError("max_attempts must be 1-3")
        if type(self.maximum_remote_calls) is not int or not 1 <= self.maximum_remote_calls <= 10:
            raise ValueError("maximum_remote_calls must be 1-10")


def source_fingerprint():
    paths = sorted((ROOT / "m5eval").glob("*.py")) + [ROOT / "requirements.txt", ROOT / "requirements-gemini.txt"]
    return {str(path.relative_to(ROOT)): sha256(path) for path in paths}


def _label(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", value):
        raise ValueError("Use a short label containing letters, digits, dots, underscores or hyphens")
    return value


class Experiment:
    def __init__(self, destination, version, cases, seeds, backend, *, settings=None, code_commit=None):
        self.root = (Path(destination) / _label(version)).resolve()
        for protected in (ROOT / "source", ROOT / "data", ROOT / "reference", ROOT / "audit",
                          ROOT / "m5eval", ROOT / "tests", ROOT / "reports", ROOT / "docs"):
            if self.root == protected or protected in self.root.parents:
                raise ValueError("Run output must be separate from preserved artifacts and reports")
        self.version, self.cases, self.seeds = version, deepcopy(cases), list(seeds)
        self.settings = settings or RunSettings()
        self.backend = backend
        self.datasets = load_datasets(ROOT / "data")
        if not cases or len({c["case_id"] for c in cases}) != len(cases):
            raise ValueError("Cases must have unique IDs")
        for case in cases:
            _label(case["case_id"])
            validate_case(case, self.datasets)
        if not self.seeds or any(type(seed) is not int for seed in self.seeds) or len(set(self.seeds)) != len(self.seeds):
            raise ValueError("Seeds must be distinct integers")
        if backend.mode not in ("live", "sdk_mock", "fixture"):
            raise ValueError("Unknown evidence mode")
        verify_import()
        self.identity = {
            "experiment_version": version, "evidence_mode": backend.mode,
            "scorer_version": SCORER_VERSION, "generation_policy": POLICY_VERSION,
            "settings": asdict(self.settings), "cases": deepcopy(self.cases), "seeds": self.seeds.copy(),
            "dataset_sha256": {name: sha256(ROOT / "data" / f"{name}.csv") for name in self.datasets},
            "source_sha256": source_fingerprint(), "code_commit": code_commit,
            "csv_float_precision": "round_trip", "expected_sdk_version": SDK_VERSION,
            "backend_options": {"http_request_cap": getattr(backend, "max_http_requests", None),
                                "timeout_ms": getattr(backend, "timeout_ms", None),
                                "sdk_retry_attempts": 1 if backend.mode != "fixture" else None},
            "python_packages": {name: importlib.metadata.version(name) for name in ("pandas", "numpy")},
        }
        for package in ("google-genai", "httpx", "pydantic", "tenacity", "google-auth"):
            try:
                self.identity["python_packages"][package] = importlib.metadata.version(package)
            except importlib.metadata.PackageNotFoundError:
                self.identity["python_packages"][package] = None
        self.identity_hash = fingerprint(self.identity)
        self.root.mkdir(parents=True, exist_ok=True)
        manifest = self.root / "manifest.json"
        if manifest.exists():
            saved = read_json(manifest)
            if saved.get("identity_sha256") != self.identity_hash or saved.get("identity") != self.identity:
                raise ValueError("Existing experiment has different inputs, mode, code or settings; use a new version")
        else:
            save_record(manifest, {"identity": self.identity, "identity_sha256": self.identity_hash,
                                   "created_at_utc": utc_now(), "original_v1_v2_modified": False})

    def run_path(self, case, seed):
        return self.root / f"{_label(case['case_id'])}_seed{seed}"

    def read_completed(self, case, seed):
        path = self.run_path(case, seed)
        record_path = path / "record.json"
        checksum = path / "record.sha256"
        if not record_path.is_file() or not checksum.is_file():
            raise ValueError("Existing run is incomplete; inspect its journal before authorizing a separate recovery version")
        if checksum.read_text().strip() != sha256(record_path):
            raise ValueError("Saved run checksum mismatch")
        record = read_json(record_path)
        if (record["metadata"]["experiment_identity_sha256"] != self.identity_hash
                or record["user_input"] != case or record["seed"] != seed
                or record["experiment_version"] != self.version):
            raise ValueError("Saved run does not match experiment identity")
        return record

    def run_case(self, case_id, seed, *, sleep=None):
        if seed not in self.seeds or type(seed) is not int:
            raise ValueError("Seed is not part of this experiment")
        case = next((c for c in self.cases if c["case_id"] == case_id), None)
        if case is None:
            raise ValueError("Case is not part of this experiment")
        folder = self.run_path(case, seed)
        if folder.exists():
            return self.read_completed(case, seed)
        folder.mkdir()
        save_record(folder / "request.json", {"case": case, "seed": seed,
                    "experiment_identity_sha256": self.identity_hash, "created_at_utc": utc_now()})
        journal = folder / "events.jsonl"

        def emit(event):
            payload = json.dumps(_safe(event), ensure_ascii=False, allow_nan=False) + "\n"
            with journal.open("a", encoding="utf-8") as f:
                f.write(payload)
                f.flush()

        options = asdict(self.settings)
        if sleep is not None:
            options["sleep"] = sleep
        generation = generate(case, seed, self.backend, ROOT / "data", emit, **options)
        metadata = {"model": self.settings.model, "temperature": self.settings.temperature,
                    "code_commit": self.identity["code_commit"],
                    "dataset_sha256": self.identity["dataset_sha256"],
                    "source_sha256": self.identity["source_sha256"],
                    "experiment_identity_sha256": self.identity_hash,
                    "evidence_mode": self.backend.mode, "seed_support_verified": False,
                    "generation_settings": asdict(self.settings), "cost_usd": None,
                    "wall_time_ms": generation["wall_time_ms"],
                    "provider_http_requests": sum(e["kind"] == "http_request" for e in generation["trace"]),
                    "live_http_requests": sum(e["kind"] == "http_request" for e in generation["trace"]) if self.backend.mode == "live" else 0,
                    "usage_scope": "Raw usageMetadata is retained per HTTP response; billing totals are not inferred."}
        record = build_record(case, seed, generation, self.datasets, metadata,
                              experiment_version=self.version, run_id=f"{case_id}_seed{seed}")
        save_record(folder / "record.json", record)
        (folder / "record.sha256").write_text(sha256(folder / "record.json") + "\n")
        return record

    def run_batch(self, *, max_new_runs):
        if type(max_new_runs) is not int or max_new_runs < 1:
            raise ValueError("An explicit positive new-run cap is required")
        completed = []
        for case in self.cases:
            for seed in self.seeds:
                path = self.run_path(case, seed)
                if path.exists():
                    self.read_completed(case, seed)
                    continue
                if len(completed) >= max_new_runs:
                    return completed
                record = self.run_case(case["case_id"], seed)
                completed.append(record)
                error = record["generation_result"].get("generation_error") or {}
                if not record["generation_success"] and error.get("type") in ("ProviderFailure", "RequestBudgetExceeded"):
                    return completed
        return completed

    def summary(self):
        rows = []
        for case in self.cases:
            for seed in self.seeds:
                record = self.read_completed(case, seed)
                rows.append({"case_id": case["case_id"], "seed": seed,
                             **{k: case[k] for k in ("trip_duration", "interests", "budget_level")},
                             **{k: record["evaluation"][k] for k in ("APM", "RBM", "HBM", "IFR")},
                             "tool_calls": record["generation_result"]["tool_calls"]})
        if len(self.cases) < 2 or len(self.seeds) < 2:
            return {"evidence_mode": self.backend.mode, "records": len(rows),
                    "status": "pilot only; not a three-seed baseline summary",
                    "scores": [{k: r[k] for k in ("case_id", "seed", "APM", "RBM", "HBM", "IFR")} for r in rows]}
        return {"evidence_mode": self.backend.mode, "records": len(rows),
                "is_formal_live_20_case_3_seed_cohort": self.backend.mode == "live" and len(self.cases) >= 20 and len(self.seeds) == 3,
                "statistics": summarize(rows, self.cases, self.seeds)}


def golden_cases():
    return read_json(V2 / "baseline_v2_implementation_reference.json")["golden_set"]
