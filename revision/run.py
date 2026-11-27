"""Freeze, journal and resume separate revised experiments. No network on import."""

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import time

from m5eval.scoring import load_datasets
from . import VERSION
from .constraints import evaluate
from .provider import Gemini
from .workflow import run_workflow

ROOT = Path(__file__).resolve().parents[1]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix+".tmp")
    with tmp.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    tmp.replace(path)


def now():
    return datetime.now(timezone.utc).isoformat()


def commit_at(project):
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=project,
                                       stderr=subprocess.DEVNULL, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


class Experiment:
    def __init__(self, destination, version, backend, model, *, study="main", second_model=None,
                 coordinator_model=None, root=ROOT):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", version):
            raise ValueError("Use a short safe experiment version")
        self.project, self.backend = Path(root).resolve(), backend
        self.data = load_datasets(self.project / "data")
        cases = json.loads((self.project / "revision/cases/all.json").read_text())
        seeds = [11, 22, 33]
        if study not in ("main", "ablation", "second_model", "strong_coordinator", "seed_check", "pilot"):
            raise ValueError("Unknown study")
        conditions = ["baseline", "treatment"]
        if study=="ablation":
            conditions = ["without_feasibility", "without_repair"]
        if study=="strong_coordinator":
            if not coordinator_model or coordinator_model==model:
                raise ValueError("A distinct coordinator model is required")
            conditions = ["strong_coordinator"]
        if study=="second_model":
            if not second_model or second_model==model:
                raise ValueError("A distinct second model is required")
            model = second_model
        if study=="seed_check":
            cases = [cases[0]]
            seeds = [11]
            conditions = ["baseline"]
        if study=="pilot":
            cases = [{"case_id": "P00", "trip_duration": 1, "interests": ["Shopping", "Entertainment"],
                      "budget_level": "Low", "constraints": {"max_km_per_day": 60, "hotel_cap_sar": 600,
                      "nights": 1, "minimum_interest_slots": {"Shopping": 1, "Entertainment": 1}}}]
            seeds = [11]
        source_paths = sorted((self.project / "revision").glob("*.py")) + [
            self.project / "m5eval/scoring.py", self.project / "m5eval/__init__.py"]
        self.identity = {"version": version, "policy": VERSION, "study": study, "evidence_mode": backend.mode,
            "code_commit": commit_at(self.project),
            "model": model, "coordinator_model": coordinator_model if study=="strong_coordinator" else None,
            "temperature": 0, "max_output_tokens_per_request": 8192, "max_repairs": 3, "http_per_record": 60,
            "pacing_seconds": backend.pacing, "timeout_seconds": backend.timeout,
            "retries": 0, "cases": cases, "seeds": seeds, "conditions": conditions,
            "dataset_sha256": {name: file_hash(self.project / "data" / f"{name}.csv") for name in self.data},
            "source_sha256": {str(p.relative_to(self.project)): file_hash(p) for p in source_paths},
            "python": platform.python_version(), "seed_effect_verified": False,
            "ordering": "Case-major, seed-minor; reverse condition order on alternate pairs"}
        self.fingerprint = digest(self.identity)
        self.root = (Path(destination) / version).resolve()
        allowed = (self.project / "revision/runs").resolve()
        if self.root==self.project or (self.project in self.root.parents and allowed not in self.root.parents):
            raise ValueError("Within the project, write run evidence only beneath revision/runs")
        self.root.mkdir(parents=True, exist_ok=True)
        manifest = self.root / "manifest.json"
        if manifest.exists():
            saved = json.loads(manifest.read_text())
            if saved["identity"]!=self.identity or saved["sha256"]!=self.fingerprint:
                raise ValueError("Experiment changed; preserve the old version and use a new version")
        else:
            if any(self.root.iterdir()):
                raise ValueError("Nonempty output directory without a manifest")
            write_json(manifest, {"identity": self.identity, "sha256": self.fingerprint, "created": now()})
        snapshot = self.root / "source_snapshot"
        for name, expected in self.identity["source_sha256"].items():
            target = snapshot / name
            if target.exists():
                if file_hash(target)!=expected:
                    raise ValueError("Saved source snapshot hash mismatch")
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(self.project/name, target)

    def schedule(self):
        for index, (case, seed) in enumerate((c,s) for c in self.identity["cases"] for s in self.identity["seeds"]):
            conditions = self.identity["conditions"]
            for condition in conditions if index%2==0 else list(reversed(conditions)):
                for repeat in (1,2) if self.identity["study"]=="seed_check" else (1,):
                    yield deepcopy(case), seed, condition, repeat

    def folder(self, case, seed, condition, repeat):
        return self.root / f"{condition}_{case['case_id']}_seed{seed}_repeat{repeat}"

    def read_record(self, folder, case, seed, condition, repeat):
        if not (folder / "record.json").exists() or not (folder / "record.sha256").exists():
            raise ValueError("Interrupted record preserved; review journal before any recovery")
        if (folder / "record.sha256").read_text().strip()!=file_hash(folder / "record.json"):
            raise ValueError("Record checksum mismatch")
        row = json.loads((folder / "record.json").read_text())
        if (row.get("identity_sha256")!=self.fingerprint or row.get("case")!=case
                or row.get("seed")!=seed or row.get("condition")!=condition or row.get("repeat")!=repeat):
            raise ValueError("Saved record identity mismatch")
        events = [json.loads(line) for line in (folder / "events.jsonl").read_text().splitlines()]
        if digest(events)!=row["events_sha256"]:
            raise ValueError("Journal hash mismatch")
        if evaluate(row["result"]["itinerary"], case, self.data)!=row["result"]["evaluation"]:
            raise ValueError("Saved evaluation does not reproduce")
        return row

    def run(self, max_new_records):
        if type(max_new_records) is not int or max_new_records<1:
            raise ValueError("An explicit positive record limit is required")
        new = []
        for case, seed, condition, repeat in self.schedule():
            folder = self.folder(case, seed, condition, repeat)
            if folder.exists():
                self.read_record(folder, case, seed, condition, repeat)
                continue
            if len(new)>=max_new_records or self.backend.cap-self.backend.count<60:
                break
            folder.mkdir()
            write_json(folder / "request.json", {"case": case, "seed": seed, "condition": condition,
                "repeat": repeat, "identity_sha256": self.fingerprint, "started": now()})
            events = []
            start = time.perf_counter()
            def emit(event):
                event = self.backend.sanitize({**event, "number_in_record": len(events)+1, "time_utc": now()})
                events.append(event)
                with (folder / "events.jsonl").open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(event, ensure_ascii=False, allow_nan=False)+"\n")
                    stream.flush()
                    os.fsync(stream.fileno())
                if event["kind"]=="agent_started":
                    print("PROGRESS", folder.name, event["stage"], flush=True)
            result = run_workflow(case, seed, condition, self.backend, self.data, self.identity["model"], emit,
                                  coordinator_model=self.identity["coordinator_model"])
            responses = [e for e in events if e["kind"]=="http_response" and isinstance(e.get("body"), dict)]
            observations = [e["body"].get("usageMetadata") for e in responses]
            usage = {}
            for name in ("promptTokenCount", "candidatesTokenCount", "thoughtsTokenCount", "totalTokenCount"):
                values = [u[name] for u in observations if isinstance(u, dict) and type(u.get(name)) is int]
                usage[name] = {"observed": sum(values) if values else None, "responses_with_observation": len(values)}
            row = {"case": case, "case_id": case["case_id"], "seed": seed, "condition": condition,
                   "repeat": repeat, "identity_sha256": self.fingerprint, "evidence_mode": self.backend.mode,
                   "result": result, "events_sha256": digest(events), "usage": usage,
                   "system_wall_seconds": time.perf_counter()-start,
                   "pacing_wait_seconds": sum(e["elapsed_seconds"] for e in events if e["kind"]=="pacing_wait"),
                   "actual_cost_usd": None, "estimated_cost_usd": None, "finished": now()}
            write_json(folder / "record.json", row)
            (folder / "record.sha256").write_text(file_hash(folder / "record.json")+"\n")
            new.append(row)
            print(folder.name, "PASS" if result["success"] else "FAIL", flush=True)
            if result["error"] and result["error"]["type"] in ("ServiceError", "BudgetError"):
                break
        return new


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--study", required=True)
    p.add_argument("--version", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--second-model")
    p.add_argument("--coordinator-model")
    p.add_argument("--max-requests", type=int, required=True)
    p.add_argument("--max-new-records", type=int, required=True)
    p.add_argument("--output", default=str(ROOT / "revision/runs"))
    args = p.parse_args()
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    backend = Gemini(key, args.max_requests)
    experiment = Experiment(args.output, args.version, backend, args.model, study=args.study,
                            second_model=args.second_model, coordinator_model=args.coordinator_model)
    experiment.run(args.max_new_records)


if __name__=="__main__":
    main()
