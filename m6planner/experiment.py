"""Paired, counterbalanced, resumable M6 records, always separate from M5."""

from dataclasses import asdict
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import time

from m5eval import SCORER_VERSION
from m5eval.evaluate import ROOT, sha256
from m5eval.experiment import fingerprint, golden_cases
from m5eval.generation import SDK_VERSION, utc_now
from m5eval.records import _safe, build_record, save_record
from m5eval.scoring import load_datasets, score_itinerary, tool_coverage
from . import BASE_COMMIT, POLICY_VERSION
from .workflow import generate_condition


def source_hashes():
    paths = sorted((ROOT / "m5eval").glob("*.py")) + sorted((ROOT / "m6planner").glob("*.py"))
    paths += [ROOT / "requirements.txt", ROOT / "requirements-gemini.txt"]
    return {str(p.relative_to(ROOT)): sha256(p) for p in paths}


def label(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", value):
        raise ValueError("Use a short version label with letters, digits, dots, hyphens or underscores")
    return value


class PairedExperiment:
    def __init__(self, destination, version, backend, *, cases=None, seeds=(11, 22, 33), study_kind="pilot"):
        self.backend, self.version = backend, label(version)
        if study_kind not in ("pilot", "formal", "validation"):
            raise ValueError("Unknown study kind")
        self.root = (Path(destination) / version).resolve()
        # In this project tree only the dedicated output directory is writable by runs.
        allowed = (ROOT / "m6_runs").resolve()
        if (self.root == ROOT or ROOT in self.root.parents) and not (self.root == allowed or allowed in self.root.parents):
            raise ValueError("Use m6_runs or a separate output directory, never preserved project folders")
        self.cases = json.loads(json.dumps(golden_cases() if cases is None else cases))
        self.seeds = list(seeds)
        approved = {c["case_id"]: c for c in golden_cases()}
        if (not self.cases or len({c["case_id"] for c in self.cases}) != len(self.cases)
                or any(c != approved.get(c["case_id"]) for c in self.cases)):
            raise ValueError("Use unchanged, distinct golden cases")
        if (not self.seeds or len(set(self.seeds)) != len(self.seeds)
                or any(type(s) is not int or s not in (11, 22, 33) for s in self.seeds)):
            raise ValueError("Use distinct requested seeds from 11/22/33")
        if study_kind == "formal" and (self.cases != golden_cases() or self.seeds != [11, 22, 33]):
            raise ValueError("Formal study requires the unchanged full 20-case/3-seed cohort")
        if backend.mode not in ("live", "sdk_mock") or (study_kind == "validation" and backend.mode != "sdk_mock"):
            raise ValueError("Validation evidence must use mocked SDK HTTP")
        self.datasets = load_datasets(ROOT / "data")
        packages = {}
        for name in ("pandas", "numpy", "google-genai", "httpx", "pydantic"):
            try:
                packages[name] = importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError:
                packages[name] = None
        self.identity = {"version": version, "base_commit": BASE_COMMIT,
                         "source_sha256": source_hashes(), "generation_policy": POLICY_VERSION,
                         "policy": asdict(backend.policy), "scorer_version": SCORER_VERSION,
                         "cases": self.cases, "seeds": self.seeds, "study_kind": study_kind,
                         "evidence_mode": backend.mode, "expected_sdk_version": SDK_VERSION,
                         "packages": packages, "seed_support_verified": False,
                         "dataset_sha256": {name: sha256(ROOT / "data" / f"{name}.csv") for name in self.datasets},
                         "order_rule": "case-major, seed-minor; alternate baseline/treatment and treatment/baseline by pair index"}
        self.identity_hash = fingerprint(self.identity)
        self.root.mkdir(parents=True, exist_ok=True)
        manifest = self.root / "manifest.json"
        if manifest.exists():
            saved = json.loads(manifest.read_text())
            if saved.get("identity_sha256") != self.identity_hash or saved.get("identity") != self.identity:
                raise ValueError("Version identity changed; do not resume, use a separately approved version")
        else:
            save_record(manifest, {"identity": self.identity, "identity_sha256": self.identity_hash,
                                   "created_at_utc": utc_now()})

    def schedule(self):
        for index, (case, seed) in enumerate((c, s) for c in self.cases for s in self.seeds):
            order = ("baseline", "treatment") if index % 2 == 0 else ("treatment", "baseline")
            for condition in order:
                yield case, seed, condition

    def folder(self, case, seed, condition):
        return self.root / f"{condition}_{case['case_id']}_seed{seed}"

    def read_record(self, case, seed, condition):
        folder = self.folder(case, seed, condition)
        path = folder / "record.json"
        if not path.is_file() or not (folder / "record.sha256").is_file():
            raise ValueError("Interrupted record: preserve journal and inspect before separate recovery; no automatic rerun")
        if (folder / "record.sha256").read_text().strip() != sha256(path):
            raise ValueError("Record checksum mismatch")
        record = json.loads(path.read_text())
        meta = record.get("metadata", {})
        if (meta.get("experiment_identity_sha256") != self.identity_hash or meta.get("condition") != condition
                or record.get("user_input") != case or type(record.get("seed")) is not int or record["seed"] != seed
                or record.get("experiment_version") != self.version):
            raise ValueError("Record identity mismatch")
        events = [json.loads(line) for line in (folder / "events.jsonl").read_text().splitlines()]
        if events != record["generation_result"]["trace"]:
            raise ValueError("Journal/trace mismatch")
        if record["evaluation"] != score_itinerary(record["generation_result"]["itinerary"], case, self.datasets):
            raise ValueError("Saved scores do not reproduce")
        if record["RTC"] != tool_coverage(record["generation_result"]["tool_calls"]):
            raise ValueError("RTC does not reproduce")
        return record

    def run_record(self, case, seed, condition, *, clock=time.perf_counter, sleep=time.sleep):
        if not any(c == case and s == seed and k == condition for c, s, k in self.schedule()):
            raise ValueError("Record is not in approved schedule")
        folder = self.folder(case, seed, condition)
        if folder.exists():
            return self.read_record(case, seed, condition)
        # Check BEFORE creating a folder, so a session cap does not create a false interrupted run.
        if self.backend.remaining < self.backend.policy.http_per_record:
            raise ValueError("Not enough session capacity reserved for another complete record")
        folder.mkdir()
        save_record(folder / "request.json", {"case": case, "seed": seed, "condition": condition,
                    "identity_sha256": self.identity_hash, "created_at_utc": utc_now()})

        def emit(event):
            with (folder / "events.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(_safe(event), ensure_ascii=False, allow_nan=False) + "\n")
                stream.flush()

        generation = generate_condition(case, seed, condition, self.backend, ROOT / "data", emit, clock=clock, sleep=sleep)
        meta = {"condition": condition, "model": self.backend.policy.model, "temperature": self.backend.policy.temperature,
                "code_commit": None, "base_commit": BASE_COMMIT, "source_sha256": self.identity["source_sha256"],
                "dataset_sha256": self.identity["dataset_sha256"], "experiment_identity_sha256": self.identity_hash,
                "policy": self.identity["policy"], "generation_policy": POLICY_VERSION,
                "evidence_mode": self.backend.mode, "study_kind": self.identity["study_kind"],
                "seed_support_verified": False, "actual_cost_usd": None, "estimated_cost_usd": None,
                "live_http_requests": generation["http_requests"] if self.backend.mode == "live" else 0,
                "session_http_cap": self.backend.session_cap,
                "code_provenance": "Source snapshot identified by file hashes; base commit is M5, not a claim of an M6 commit"}
        record = build_record(case, seed, generation, self.datasets, meta,
                              experiment_version=self.version, run_id=folder.name)
        save_record(folder / "record.json", record)
        (folder / "record.sha256").write_text(sha256(folder / "record.json") + "\n")
        return record

    def run_batch(self, *, max_new_records, clock=time.perf_counter, sleep=time.sleep):
        if type(max_new_records) is not int or max_new_records < 1:
            raise ValueError("Explicit positive new-record cap required")
        records = []
        for case, seed, condition in self.schedule():
            if self.folder(case, seed, condition).exists():
                self.read_record(case, seed, condition)
                continue
            if len(records) >= max_new_records or self.backend.remaining < self.backend.policy.http_per_record:
                break
            record = self.run_record(case, seed, condition, clock=clock, sleep=sleep)
            records.append(record)
            error = record["generation_result"].get("generation_error") or {}
            # Stop the batch on terminal service/budget/program errors; keep its record.
            if error and error["type"] != "MessageError":
                break
        return records
