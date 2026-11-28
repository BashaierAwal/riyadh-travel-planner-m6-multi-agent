"""Resume unstarted records after bounded cooldowns; never retry a saved attempt."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import shutil
import sys
import time


CONTROLLER_SHA = "a13507ca7b2af66716e53497028e7788b73571a44f490ac1dbcf1a8b4106f5ee"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2)+"\n")
    temporary.replace(path)


def temporary_service_stop(status):
    error = status.get("detail") or {}
    return (status.get("state") == "stopped_after_service_or_budget_error"
            and error.get("type") == "ServiceError" and error.get("status") in (None, 408, 500, 502, 503, 504))


def linux_process_active(pid):
    path = Path("/proc")/str(pid)
    try:
        state = (path/"stat").read_text().rsplit(")", 1)[1].strip().split()[0]
    except FileNotFoundError:
        return False
    return state != "Z"


def supervise(args, *, run=subprocess.run, sleep=time.sleep, active=linux_process_active):
    if sha(args.controller) != CONTROLLER_SHA:
        raise ValueError("The registered controller changed")
    if args.cooldown_seconds < 300 or not 0 <= args.max_continuations <= 4:
        raise ValueError("Use a cooldown of at least five minutes and at most four continuations")
    args.output.mkdir(parents=True, exist_ok=True)
    name = "continuation_"+args.stage+"_"+args.target_group
    policy = {"controller_sha256": sha(args.controller), "supervisor_sha256": sha(__file__),
              "stage": args.stage, "target_group": args.target_group,
              "source_commit": args.source_commit, "http_cap": args.http_cap,
              "cooldown_seconds": args.cooldown_seconds, "max_continuations": args.max_continuations,
              "saved_records_not_retried": True, "daily_quota_stops_immediately": True}
    policy_path = args.output/(name+"_policy.json")
    if policy_path.exists() and json.loads(policy_path.read_text()) != policy:
        raise ValueError("The saved continuation policy differs")
    save(policy_path, policy)
    snapshot = args.output/"Continue_Review_Study.py"
    if snapshot.exists() and sha(snapshot) != sha(__file__):
        raise ValueError("The saved supervisor source differs")
    if not snapshot.exists():
        shutil.copyfile(__file__, snapshot)
    destination = args.output/(name+"_status.json")
    status_path = args.output/"run_status.json"
    launches, continuations = 0, 0

    def status(state, **extra):
        value = {"state": state, "launches": launches, "continuations": continuations,
                 "at_utc": datetime.now(timezone.utc).isoformat(), **extra}
        save(destination, value)
        print("REVIEW_CONTINUATION", json.dumps(value), flush=True)

    command = [sys.executable, str(args.controller), "--project", str(args.project),
               "--output", str(args.output), "--source-commit", args.source_commit,
               "--http-cap", str(args.http_cap), "--stage", args.stage,
               "--target-group", args.target_group, "--priority-worker", str(args.priority_worker)]
    if args.wait_pid:
        status("waiting_for_existing_controller", wait_pid=args.wait_pid)
        while active(args.wait_pid):
            sleep(15)
        if not status_path.exists():
            raise ValueError("The existing controller left no status receipt")
        current = json.loads(status_path.read_text())
    else:
        current = None
    while True:
        if current is not None:
            expected_version = {"main": "main-v2", "ablation": "ablation-v1",
                                "second_model": "second-model-v1", "strong_coordinator": "coordinator-v1"}[args.stage]
            if temporary_service_stop(current) and current.get("active_version") != expected_version:
                raise ValueError("The stopped controller belongs to another study")
            if not temporary_service_stop(current):
                status("stopped", controller_state=current["state"], detail=current.get("detail"))
                return
            if continuations >= args.max_continuations:
                status("continuation_limit_reached", controller_state=current["state"], detail=current.get("detail"))
                return
            continuations += 1
            status("cooling_down", wait_seconds=args.cooldown_seconds, detail=current.get("detail"))
            sleep(args.cooldown_seconds)
        launches += 1
        status("running_controller")
        outcome = run(command, cwd=args.project, check=False)
        if outcome.returncode != 0 or not status_path.exists():
            status("inspection_required", returncode=outcome.returncode)
            return
        current = json.loads(status_path.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--controller", required=True, type=Path)
    parser.add_argument("--priority-worker", required=True, type=Path)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--http-cap", required=True, type=int)
    parser.add_argument("--stage", required=True, choices=("main", "ablation", "second_model", "strong_coordinator"))
    parser.add_argument("--target-group", choices=("hard", "all"), default="hard")
    parser.add_argument("--cooldown-seconds", type=int, default=300)
    parser.add_argument("--max-continuations", type=int, default=4)
    parser.add_argument("--wait-pid", type=int)
    supervise(parser.parse_args())


if __name__ == "__main__":
    main()
