"""Write every event/record directly to mounted Drive, with a separate checkpoint ZIP."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# Prior run:463 observed requests + at most6 remaining records*30; pilot:9.
# This reserves the unobserved tail instead of assuming zero usage after disconnect.
RECOVERY_HTTP_CAP = 3600 - (463 + 6 * 30 + 9)


def run_persistent_batch(destination, *, approved=False, version="formal-v2", backend=None, api_key=None):
    if approved is not True:
        raise PermissionError("A separately approved recovery cohort is required before model calls")
    if version != "formal-v2":
        raise ValueError("Recovery uses a separate formal-v2; never overwrite formal-v1")
    destination = Path(destination).resolve()
    if backend is None or backend.mode == "live":
        drive = Path("/content/drive/MyDrive").resolve()
        if not os.path.ismount("/content/drive") or not drive.is_dir() or drive not in destination.parents:
            raise ValueError("Live evidence must be inside an authorized mounted MyDrive folder")
    from scripts.M6_Run_Formal import inspect_saved
    from m6planner.experiment import PairedExperiment
    from m6planner.workflow import ControlledBackend
    from m5eval.generation import GeminiBackend
    folder = destination / version
    before = inspect_saved(folder)
    if before["http_requests"] > RECOVERY_HTTP_CAP:
        raise ValueError("Recovery request budget exceeded in saved evidence")
    if before["terminal_errors"] or before["complete"]:
        return before
    count = min(6, 120 - before["records"], (RECOVERY_HTTP_CAP - before["http_requests"]) // 30)
    if count < 1:
        return before
    if backend is None:
        backend = ControlledBackend(GeminiBackend(api_key, allow_live=True, max_http_requests=30 * count))
        backend.pacer.last_start = backend.pacer.clock()
    elif backend.mode != "sdk_mock":
        raise ValueError("Tests may inject only a mocked HTTP backend")
    try:
        exp = PairedExperiment(destination, version, backend, study_kind="formal")
        policy_file = folder / "storage_policy.json"
        storage = {"storage": "All journals and records written directly to persistent destination",
                   "destination": str(destination), "checkpoint": "Separate ZIP after each batch",
                   "formal_v1": "Preserved separately as an incomplete run with unavailable later raw evidence",
                   "recovery_http_cap": RECOVERY_HTTP_CAP,
                   "reserved_prior_request_upper_bound_including_pilot": 652,
                   "combined_request_cap": 3600,
                   "version": version, "evidence_mode": backend.mode}
        if policy_file.exists():
            if json.loads(policy_file.read_text()) != storage:
                raise ValueError("Storage identity changed")
        else:
            with policy_file.open("x") as stream:
                json.dump(storage, stream, indent=2)
        exp.run_batch(max_new_records=count, clock=backend.pacer.clock, sleep=backend.pacer.sleep)
        for case, seed, condition in exp.schedule():
            if exp.folder(case, seed, condition).exists():
                exp.read_record(case, seed, condition)  # checksum and journal readback
        state = inspect_saved(folder)
        checkpoints = destination.parent / "checkpoints"
        checkpoints.mkdir(parents=True, exist_ok=True)
        name = checkpoints / f"M6_{version}_checkpoint_{state['records']:03d}"
        if name.with_suffix(".zip").exists():
            raise ValueError("Checkpoint already exists; preserve it and inspect")
        archive = shutil.make_archive(str(name), "zip", root_dir=destination, base_dir=version)
        with zipfile.ZipFile(archive) as saved:
            if saved.testzip() is not None:
                raise ValueError("Persistent checkpoint integrity check failed")
        state["checkpoint"] = archive
        return state
    except BaseException:
        if folder.exists():
            checkpoints = destination.parent / "checkpoints"
            checkpoints.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            shutil.make_archive(str(checkpoints / f"M6_{version}_interrupted_{stamp}"), "zip",
                                root_dir=destination, base_dir=version)
        raise
    finally:
        backend.close()
