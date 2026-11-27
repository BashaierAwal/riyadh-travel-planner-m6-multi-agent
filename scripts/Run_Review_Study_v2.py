"""Continue frozen experiments in bounded batches; never replace a saved run."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


STAGES = (
    ("main", "main-v2", [], 240),
    ("ablation", "ablation-v1", [], 240),
    ("second_model", "second-model-v1", ["--second-model", "gemini-3.1-flash-lite"], 240),
    ("strong_coordinator", "coordinator-v1", ["--coordinator-model", "gemini-3-flash-preview"], 120),
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def saved(root):
    result = {}
    if not root.exists():
        return result
    for folder in root.iterdir():
        if not folder.is_dir() or folder.name in ("analysis", "source_snapshot"):
            continue
        path = folder / "record.json"
        checksum = folder / "record.sha256"
        if not path.exists() or not checksum.exists():
            raise ValueError("An interrupted record requires inspection; it will not be rerun")
        if checksum.read_text().strip() != sha(path):
            raise ValueError("A saved record checksum differs")
        result[folder.name] = json.loads(path.read_text())
    return result


def write(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--http-cap", required=True, type=int)
    args = parser.parse_args()
    if args.http_cap < 60:
        raise ValueError("Reserve at least one full record")
    args.output.mkdir(parents=True, exist_ok=True)
    controller_path = args.output / "Review_Controller_v2.py"
    if controller_path.exists() and sha(controller_path) != sha(__file__):
        raise ValueError("Preserve the previous controller; use a new controller version")
    if not controller_path.exists():
        shutil.copyfile(__file__, controller_path)
    policy = {"source_commit": args.source_commit, "controller_sha256": sha(__file__),
              "http_cap_including_saved_records": args.http_cap, "new_records_per_batch": 6,
              "main_model": "gemini-3.5-flash-lite", "stages": STAGES,
              "prior_versions_counted": ["pilot-v1", "pilot-v2", "seed-check-v1", "main-v1"],
              "interrupted_prior_record_reservation": 60}
    path = args.output / "controller_policy_v2.json"
    policy = json.loads(json.dumps(policy))
    if path.exists() and json.loads(path.read_text()) != policy:
        raise ValueError("Controller policy differs from its saved version")
    write(path, policy)

    def count_requests():
        total = sum(r["result"]["http_requests"] for _, v, _, _ in STAGES for r in saved(args.output / v).values())
        for version in policy["prior_versions_counted"]:
            root = args.output / version
            if not root.exists():
                continue
            for folder in root.iterdir():
                if not folder.is_dir() or folder.name in ("analysis", "source_snapshot"):
                    continue
                record, checksum = folder / "record.json", folder / "record.sha256"
                if record.exists() and checksum.exists():
                    if checksum.read_text().strip() != sha(record):
                        raise ValueError("A prior saved record checksum differs")
                    total += json.loads(record.read_text())["result"]["http_requests"]
                else:
                    # Reserve the full old per-record cap; this is a resource
                    # reservation, never a claim that 60 requests were observed.
                    total += policy["interrupted_prior_record_reservation"]
        return total

    def status(state, version=None, detail=None):
        receipt = {"state": state, "active_version": version, "detail": detail,
                   "http_requests_used_or_reserved": count_requests(),
                   "at_utc": datetime.now(timezone.utc).isoformat(),
                   "stages": {v: {"completed": len(saved(args.output / v)), "expected": n}
                              for _, v, _, n in STAGES}}
        write(args.output / "run_status.json", receipt)
        print("REVIEW_PROGRESS", json.dumps(receipt), flush=True)

    def command(arguments):
        subprocess.run([sys.executable, *arguments], cwd=args.project, check=True)

    try:
        for study, version, options, expected in STAGES:
            root = args.output / version
            while len(saved(root)) < expected:
                commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=args.project, text=True).strip()
                if commit != args.source_commit:
                    raise ValueError("The frozen generation source changed")
                remaining = args.http_cap - count_requests()
                if remaining < 60:
                    status("request_limit_reached", version)
                    return
                before = saved(root)
                status("running", version)
                command(["-m", "revision.run", "--study", study, "--version", version,
                         "--model", "gemini-3.5-flash-lite", "--max-requests", str(min(360, remaining)),
                         "--max-new-records", "6", "--output", str(args.output), *options])
                after = saved(root)
                new = [r for key, r in after.items() if key not in before]
                if not new:
                    status("no_new_records", version)
                    return
                errors = [r["result"]["error"] for r in new if r["result"]["error"]
                          and r["result"]["error"]["type"] in ("ServiceError", "BudgetError")]
                if errors:
                    command(["-m", "revision.verify", str(root), "--allow-partial"])
                    status("stopped_after_service_or_budget_error", version, errors[-1])
                    return
                status("batch_saved", version)
            command(["-m", "revision.verify", str(root)])
            command(["-m", "revision.cost", str(root)])
            if study == "ablation":
                for variant in ("without_feasibility", "without_repair"):
                    command(["-m", "revision.compare", str(args.output / "main-v2"), str(root), variant])
            elif study == "strong_coordinator":
                command(["-m", "revision.compare", str(args.output / "main-v2"), str(root), "strong_coordinator"])
            status("stage_complete", version)
        status("all_stages_complete")
    except Exception as error:
        status("stopped_for_inspection", detail={"type": type(error).__name__})
        raise


if __name__ == "__main__":
    main()
