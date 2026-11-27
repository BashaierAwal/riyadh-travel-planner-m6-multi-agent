"""Run the unchanged registered cases with hard-case blocks first."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys


def load_project(project):
    sys.path.insert(0, str(project))
    from revision.run import Experiment, digest, file_hash, write_json
    from revision.provider import Gemini
    from revision.verify import audit
    return Experiment, Gemini, digest, file_hash, write_json, audit


def prioritize(schedule, finish_cases=()):
    finish = set(finish_cases)
    return sorted(schedule, key=lambda item: (0 if item[0]["case_id"] in finish else
                                            1 if item[0]["case_id"].startswith("H") else 2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--study", required=True, choices=("main", "ablation", "second_model", "strong_coordinator"))
    parser.add_argument("--version", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--second-model")
    parser.add_argument("--coordinator-model")
    parser.add_argument("--max-requests", required=True, type=int)
    parser.add_argument("--max-new-records", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    Experiment, Gemini, digest, file_hash, write_json, audit = load_project(args.project)

    class PriorityExperiment(Experiment):
        def schedule(self):
            yield from prioritize(list(super().schedule()), getattr(self, "finish_cases", ()))

    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    backend = Gemini(key, args.max_requests)
    experiment = PriorityExperiment(args.output, args.version, backend, args.model,
                                    study=args.study, second_model=args.second_model,
                                    coordinator_model=args.coordinator_model, root=args.project)
    checked = audit(experiment.root, args.project)
    if checked["interrupted"]:
        raise ValueError("Review an interrupted record before changing execution order")
    receipt_path = experiment.root/"priority_execution_v1.json"
    saved = json.loads(receipt_path.read_text()) if receipt_path.exists() else None
    if saved:
        experiment.finish_cases = saved["policy"]["finish_started_original_cases"]
    else:
        totals = Counter(case["case_id"] for case, _, _, _ in Experiment.schedule(experiment))
        done = Counter(row["case_id"] for row in checked["records"])
        experiment.finish_cases = sorted(cid for cid, count in done.items()
                                         if cid.startswith("G") and 0 < count < totals[cid])
    queue = list(experiment.schedule())
    queue_keys = [{"case_id": case["case_id"], "seed": seed, "condition": condition, "repeat": repeat}
                  for case, seed, condition, repeat in queue]
    worker_copy = experiment.root/"source_snapshot"/"execution"/"Run_Review_Priority.py"
    policy = {"identity_sha256": experiment.fingerprint,
              "priority": "Finish started original cases, then all H blocks before untouched G blocks",
              "finish_started_original_cases": experiment.finish_cases,
              "within_case_order": "Unchanged frozen schedule including alternate condition order",
              "queue_sha256": digest(queue_keys), "worker_sha256": file_hash(Path(__file__)),
              "worker_snapshot": "source_snapshot/execution/Run_Review_Priority.py",
              "all_cases_preserved": True, "completed_records_not_retried": True}
    if saved:
        if saved["policy"] != policy or not worker_copy.exists() or file_hash(worker_copy) != policy["worker_sha256"]:
            raise ValueError("Execution priority changed after registration")
    else:
        if any(row["case_id"].startswith("H") for row in checked["records"]):
            raise ValueError("Register priority before any hard-case model record")
        worker_copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(__file__, worker_copy)
        write_json(receipt_path, {"policy": policy,
                   "registered_at_utc": datetime.now(timezone.utc).isoformat(),
                   "completed_before_registration": sorted(row["case_id"]+"/"+row["condition"]+"/"+str(row["seed"])
                                                            for row in checked["records"]),
                   "hard_model_records_before_registration": 0})
    experiment.run(args.max_new_records)


if __name__ == "__main__":
    main()
