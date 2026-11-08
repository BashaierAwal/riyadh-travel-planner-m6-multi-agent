"""Explicit offline validation or separately approved, capped live execution."""

import argparse
import json
import os
from pathlib import Path
from unittest.mock import patch

from m5eval.evaluate import ROOT
from m5eval.experiment import golden_cases
from m5eval.generation import GeminiBackend
from .analysis import export_comparison
from .experiment import PairedExperiment
from .mock_service import FakeClock, MockService
from .policy import Pacer
from .workflow import ControlledBackend


def main(argv=None):
    parser = argparse.ArgumentParser(description="M6: mock validation is separate from experimental evidence")
    commands = parser.add_subparsers(dest="command", required=True)
    smoke = commands.add_parser("mock-smoke", help="120 offline fixture records using real SDK with simulated HTTP")
    smoke.add_argument("--version", default="validation-v1")
    analyze = commands.add_parser("analyze", help="Verify a complete saved cohort and export comparison; no model calls")
    analyze.add_argument("directory", type=Path)
    live = commands.add_parser("live", help="Requires separate approval and explicit record/request caps")
    live.add_argument("--approve-live", action="store_true", help="Set only after the project lead approves this specific run")
    live.add_argument("--kind", choices=("pilot", "formal"), default="pilot")
    live.add_argument("--version", required=True)
    live.add_argument("--max-new-records", type=int, required=True)
    live.add_argument("--http-cap", type=int, required=True)
    args = parser.parse_args(argv)
    if args.command == "analyze":
        result = export_comparison(args.directory)
        print(json.dumps({"evidence_mode": result["evidence_mode"], "formal": result["is_formal_experimental_evidence"],
                          "records": {k: v["records"] for k, v in result["conditions"].items()}}, indent=2))
        return
    if args.command == "live":
        # Gate before reading a credential or creating any provider client/output directory.
        if not args.approve_live:
            parser.error("Live execution is disabled. Obtain approval for this run before using --approve-live.")
        if (args.max_new_records < 1 or args.http_cap < 30
                or args.http_cap > args.max_new_records * 30):
            parser.error("Use positive record cap and HTTP cap between30 and30 times the record cap")
        if not args.version.startswith(args.kind + "-"):
            parser.error("Use a pilot- or formal- version prefix matching the study kind")
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            parser.error("GEMINI_API_KEY must be supplied privately, e.g. from Colab Secrets")
        raw = GeminiBackend(key, allow_live=True, max_http_requests=args.http_cap)
        backend = ControlledBackend(raw)
        # Conservative startup pause also protects rapid process resumes.
        backend.pacer.last_start = backend.pacer.clock()
        try:
            exp = PairedExperiment(ROOT / "m6_runs", args.version, backend,
                                  cases=golden_cases()[:1] if args.kind == "pilot" else None,
                                  seeds=[11] if args.kind == "pilot" else [11, 22, 33], study_kind=args.kind)
            records = exp.run_batch(max_new_records=args.max_new_records)
            print(json.dumps({"saved_new_records": len(records), "http_requests": backend.request_count,
                              "directory": str(exp.root), "note": "Failed records remain saved. Download evidence after every chunk."}))
        finally:
            backend.close()
        return
    if not args.version.startswith("validation-"):
        parser.error("Mock smoke version must start validation-")
    import httpx
    fake = FakeClock()
    service = MockService(fake)
    with patch("socket.create_connection", side_effect=AssertionError("Mock smoke must never use real network")):
        raw = GeminiBackend("offline-test-key", allow_live=True, max_http_requests=3600,
                            mock_transport=httpx.MockTransport(service))
        backend = ControlledBackend(raw, pacer=Pacer(clock=fake.clock, sleep=fake.sleep))
        try:
            exp = PairedExperiment(ROOT / "m6_runs", args.version, backend, study_kind="validation")
            records = exp.run_batch(max_new_records=120, clock=fake.clock, sleep=fake.sleep)
            result = export_comparison(exp.root)
            print(json.dumps({"evidence_mode": "sdk_mock", "new_fixture_records": len(records),
                              "conditions": {k: v["records"] for k, v in result["conditions"].items()},
                              "directory": str(exp.root), "live_http_requests": 0,
                              "warning": "OFFLINE FIXTURES ONLY. Not M6 experimental results."}, indent=2))
        finally:
            backend.close()


if __name__ == "__main__":
    main()
