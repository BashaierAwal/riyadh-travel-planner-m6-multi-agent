"""Resume unstarted records after bounded cooldowns; never retry a saved attempt."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import time


CONTROLLER_SHA = "a13507ca7b2af66716e53497028e7788b73571a44f490ac1dbcf1a8b4106f5ee"
VERSIONS = {"main": "main-v2", "ablation": "ablation-v1", "second_model": "second-model-v1",
            "strong_coordinator": "coordinator-v1"}
MODELS = {"main": ["gemini-3.5-flash-lite"], "ablation": ["gemini-3.5-flash-lite"],
          "second_model": ["gemini-3.1-flash-lite"],
          "strong_coordinator": ["gemini-3.5-flash-lite", "gemini-3-flash-preview"]}


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


def mirror_metadata(args, paths):
    destination = args.output/VERSIONS[args.stage]/"source_snapshot"/"execution"
    if not destination.parent.exists():
        return
    destination.mkdir(exist_ok=True)
    for path in paths:
        target = destination/path.name
        if target.exists() and sha(target) != sha(path):
            raise ValueError("The saved execution metadata differs")
        if not target.exists():
            shutil.copyfile(path, target)


def check_service(args, *, backend_factory=None):
    """Check the API using synthetic text, never a registered travel request."""
    sys.path.insert(0, str(args.project))
    from revision.provider import Gemini, ServiceError
    from revision.tools import declarations
    factory = backend_factory or Gemini
    traces, ready = [], True
    prompt = 'Return only the JSON {"status":"ok"}. Do not call tools.'
    for model in MODELS[args.stage]:
        backend = factory(os.environ.get("GEMINI_API_KEY"), 2, pacing=12, timeout=60)
        trace = {"model": model, "checks": [], "events": []}
        traces.append(trace)
        for name, padding in (("tools_short", ""), ("tools_larger_context", "\nDiagnostic sample text. "*1000)):
            body = {"contents": [{"role": "user", "parts": [{"text": prompt+padding}]}],
                    "generationConfig": {"temperature": 0, "seed": 11, "maxOutputTokens": 8192},
                    "tools": [{"functionDeclarations": declarations(
                        ["find_activities", "find_hotels", "find_restaurants", "check_plan"])}]}
            try:
                backend.request(model, body, trace["events"].append)
                code = 200
            except ServiceError as error:
                code, ready = error.status, False
            trace["checks"].append({"name": name, "status": code, "input_characters": len(prompt+padding)})
            if not ready:
                break
        if not ready:
            break
    requests = sum(event["kind"] == "http_request" for trace in traces for event in trace["events"])
    receipt = {"scope": "Service readiness with synthetic text only; no study case, scoring or prompt tuning",
               "at_utc": datetime.now(timezone.utc).isoformat(), "source_commit": args.source_commit,
               "supervisor_sha256": sha(__file__), "ready": ready, "request_count": requests, "traces": traces}
    path = args.output/("service_readiness_"+args.stage+"_"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")+".json")
    save(path, receipt)
    mirror_metadata(args, [path])
    return {"ready": ready, "diagnostic_file": path.name, "request_count": requests,
            "statuses": [check["status"] for trace in traces for check in trace["checks"]]}


def supervise(args, *, run=subprocess.run, sleep=time.sleep, active=linux_process_active, readiness=check_service):
    if sha(args.controller) != CONTROLLER_SHA:
        raise ValueError("The registered controller changed")
    if args.cooldown_seconds < 300 or not 0 <= args.max_continuations <= 4:
        raise ValueError("Use a cooldown of at least five minutes and at most four continuations")
    args.output.mkdir(parents=True, exist_ok=True)
    name = "continuation_v2_"+args.stage+"_"+args.target_group
    policy = {"controller_sha256": sha(args.controller), "supervisor_sha256": sha(__file__),
              "stage": args.stage, "target_group": args.target_group,
              "source_commit": args.source_commit, "http_cap": args.http_cap,
              "cooldown_seconds": args.cooldown_seconds, "max_continuations": args.max_continuations,
              "saved_records_not_retried": True, "daily_quota_stops_immediately": True,
              "readiness_models": MODELS[args.stage], "readiness_requests_per_model_at_most": 2,
              "readiness_required_before_controller_launch": True,
              "readiness_failure_starts_no_study_attempt": True,
              "readiness_checks_per_launch_at_most": 4,
              "readiness_requests_separate_from_study_request_cap": True}
    policy_path = args.output/(name+"_policy.json")
    if policy_path.exists() and json.loads(policy_path.read_text()) != policy:
        raise ValueError("The saved continuation policy differs")
    save(policy_path, policy)
    snapshot = args.output/"Continue_Review_Study_v2.py"
    if snapshot.exists() and sha(snapshot) != sha(__file__):
        raise ValueError("The saved supervisor source differs")
    if not snapshot.exists():
        shutil.copyfile(__file__, snapshot)
    mirror_metadata(args, [snapshot, args.controller, policy_path])
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
            expected_version = VERSIONS[args.stage]
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
        for service_check in range(1, 5):
            status("checking_service", service_check=service_check)
            try:
                check = readiness(args)
            except Exception as error:
                status("inspection_required", error_type=type(error).__name__)
                return
            if check["ready"]:
                break
            codes = check.get("statuses", [])
            transient = bool(codes) and all(code in (None, 200, 408, 500, 502, 503, 504) for code in codes)
            if not transient or service_check == 4:
                status("service_unavailable", readiness=check, service_check=service_check)
                return
            status("waiting_for_service", wait_seconds=args.cooldown_seconds,
                   readiness=check, service_check=service_check)
            sleep(args.cooldown_seconds)
        launches += 1
        status("running_controller", readiness=check)
        outcome = run(command, cwd=args.project, check=False)
        mirror_metadata(args, [snapshot, args.controller, policy_path])
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
