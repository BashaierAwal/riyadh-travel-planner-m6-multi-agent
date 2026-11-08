"""Bounded orchestration of the existing frozen M6 runner; no calls on import."""

import json
import hashlib
from pathlib import Path
import platform
from datetime import datetime, timezone


def inspect_saved(root):
    root = Path(root)
    records, requests = [], 0
    if root.exists():
        for folder in sorted(root.iterdir()):
            if not folder.is_dir() or folder.name == "analysis":
                continue
            if not (folder / "record.json").is_file():
                raise ValueError("Interrupted record: preserve evidence and inspect before resuming")
            records.append(json.loads((folder / "record.json").read_text()))
            for line in (folder / "events.jsonl").read_text().splitlines():
                requests += json.loads(line)["kind"] == "http_request"
    if len(records) > 120 or requests > 3600:
        raise ValueError("Approved formal-study limit exceeded in saved evidence")
    errors = [r["generation_result"].get("generation_error") for r in records]
    terminal = [e for e in errors if e and e.get("type") != "MessageError"]
    return {"records": len(records), "http_requests": requests,
            "terminal_errors": len(terminal), "complete": len(records) == 120}


def run_formal(project, *, approved=False, batch_runner=None, checkpoint=None):
    """At most120 records/3600HTTP,6 records/180HTTP per call; saved failures stay saved."""
    if approved is not True:
        raise PermissionError("Explicit approval for120 formal records and3600 total requests required")
    project = Path(project).resolve()
    root = project / "m6_runs" / "formal-v1"
    if batch_runner is None:
        from m6planner.__main__ import main
        from m5eval.evaluate import ROOT
        if project != ROOT.resolve():
            raise ValueError("Controller project must equal the frozen runner project root")
        batch_runner = main
    # Credentials are supplied privately by the caller, never persisted here.
    state = inspect_saved(root)
    if state["terminal_errors"] or state["complete"]:
        if checkpoint and root.exists():
            checkpoint(root, state)
        return state
    if checkpoint and root.exists():
        checkpoint(root, state)
    try:
        for _ in range(20):
            state = inspect_saved(root)
            if state["complete"] or state["terminal_errors"]:
                break
            count = min(6, 120 - state["records"], (3600 - state["http_requests"]) // 30)
            if count < 1:
                break
            before = state["records"]
            batch_runner(["live", "--approve-live", "--kind", "formal", "--version", "formal-v1",
                          "--max-new-records", str(count), "--http-cap", str(30 * count)])
            state = inspect_saved(root)
            control = {**state, "at_utc": datetime.now(timezone.utc).isoformat(),
                       "python": platform.python_version(), "new_records": state["records"] - before,
                       "driver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                       "approved_records": 120, "approved_http_cap": 3600,
                       "chunk_record_cap": count, "chunk_http_cap": 30 * count}
            with (root / "execution_control.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(control) + "\n")
            print(json.dumps(control), flush=True)
            if checkpoint:
                checkpoint(root, state)
            if state["terminal_errors"] or state["records"] - before != count:
                break
    except BaseException:
        if checkpoint and root.exists():
            checkpoint(root, {"records": None, "status": "interrupted; inspect saved journals"})
        raise
    return state
