"""Exercise the external continuation policy without any generation request."""

import argparse
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT))
from scripts import Continue_Review_Study_v2 as supervisor


def arguments(root, **extra):
    values = dict(controller=PROJECT/"scripts/Run_Review_Study_v5.py", project=PROJECT,
                  priority_worker=PROJECT/"scripts/Run_Review_Priority.py", output=Path(root),
                  source_commit="fixture-only-no-provider-request", http_cap=3600,
                  stage="second_model", target_group="hard", cooldown_seconds=300,
                  max_continuations=2, wait_pid=None)
    values.update(extra)
    return argparse.Namespace(**values)


class ContinuationTests(unittest.TestCase):
    def test_recovered_readiness_starts_one_controller_after_waiting(self):
        with tempfile.TemporaryDirectory() as temporary:
            args = arguments(temporary)
            checks = iter([{"ready": False, "statuses": [503]}, {"ready": True, "statuses": [200, 200]}])
            calls, waits = [], []
            def run(command, **kwargs):
                calls.append(command)
                supervisor.save(args.output/"run_status.json", {"state": "selected_hard_group_complete"})
                return SimpleNamespace(returncode=0)
            supervisor.supervise(args, run=run, sleep=waits.append, readiness=lambda args: next(checks))
            self.assertEqual(len(calls), 1)
            self.assertEqual(waits, [300])
            status = json.loads((args.output/"continuation_v2_second_model_hard_status.json").read_text())
            self.assertEqual(status["controller_state"], "selected_hard_group_complete")

    def test_unavailable_service_waits_without_consuming_case_records(self):
        for code, expected_waits in ((503, [300, 300, 300]), (429, []), (403, [])):
            with tempfile.TemporaryDirectory() as temporary:
                args = arguments(temporary)
                frozen = args.output/"second-model-v1"/"manifest.json"
                frozen.parent.mkdir()
                (frozen.parent/"source_snapshot").mkdir()
                frozen.write_text("FROZEN FIXTURE MANIFEST\n")
                calls, probes, waits = [], [], []
                def readiness(args):
                    probes.append(code)
                    return {"ready": False, "statuses": [code], "diagnostic_file": "synthetic-only"}
                supervisor.supervise(args, run=lambda *a, **kw: calls.append(a), sleep=waits.append, readiness=readiness)
                self.assertEqual(calls, [])
                self.assertEqual(waits, expected_waits)
                self.assertEqual(len(probes), 4 if code == 503 else 1)
                self.assertEqual(frozen.read_text(), "FROZEN FIXTURE MANIFEST\n")
                self.assertEqual(list(frozen.parent.glob("*/record.json")), [])
                status = json.loads((args.output/"continuation_v2_second_model_hard_status.json").read_text())
                self.assertEqual(status["state"], "service_unavailable")

    def test_real_readiness_path_checks_both_models_and_stops_on_error(self):
        from revision.provider import ServiceError
        calls = []
        class Backend:
            def __init__(self, key, cap, **kwargs):
                self.count = 0
                self.asserted_cap = cap
            def request(self, model, body, emit):
                self.count += 1
                calls.append((model, body))
                emit({"kind": "http_request", "model": model, "number": self.count, "body": body})
                if model == "gemini-3-flash-preview":
                    emit({"kind": "http_response", "number": self.count, "status": 503, "body": "fixture"})
                    raise ServiceError(503, "Synthetic test response")
                emit({"kind": "http_response", "number": self.count, "status": 200, "body": {}})
                return {}
        with tempfile.TemporaryDirectory() as temporary:
            args = arguments(temporary, stage="strong_coordinator")
            with patch.dict("os.environ", {"GEMINI_API_KEY": "synthetic-fixture-no-network"}):
                result = supervisor.check_service(args, backend_factory=Backend)
            self.assertFalse(result["ready"])
            self.assertEqual(result["statuses"], [200, 200, 503])
            self.assertEqual(result["request_count"], 3)
            self.assertEqual([model for model, body in calls], ["gemini-3.5-flash-lite"]*2+["gemini-3-flash-preview"])
            self.assertEqual(list(args.output.glob("*/record.json")), [])
            receipt = json.loads((args.output/result["diagnostic_file"]).read_text())
            self.assertIn("synthetic text only", receipt["scope"])
            self.assertEqual(len(receipt["traces"]), 2)
            for model, body in calls:
                self.assertEqual(body["generationConfig"], {"temperature": 0, "seed": 11, "maxOutputTokens": 8192})
                self.assertNotIn("case_id", body["contents"][0]["parts"][0]["text"])

    def run_states(self, args, states):
        commands, sleeps = [], []
        def run(command, **kwargs):
            commands.append(command)
            value = states[len(commands)-1]
            supervisor.save(args.output/"run_status.json", value)
            return SimpleNamespace(returncode=0)
        supervisor.supervise(args, run=run, sleep=sleeps.append, readiness=lambda args: {"ready": True, "statuses": [200, 200]})
        return commands, sleeps, json.loads((args.output/"continuation_v2_second_model_hard_status.json").read_text())

    def service_error(self, status=503):
        return {"state": "stopped_after_service_or_budget_error", "active_version": "second-model-v1",
                "detail": {"type": "ServiceError", "status": status}}

    def test_cooldown_then_next_batch_preserves_saved_attempt(self):
        with tempfile.TemporaryDirectory() as temporary:
            args = arguments(temporary)
            record = args.output/"fixture_saved_record.json"
            record.write_text('UNTOUCHED FAILED ATTEMPT\n')
            before = record.read_bytes()
            commands, sleeps, status = self.run_states(args, [self.service_error(), {"state": "selected_hard_group_complete"}])
            self.assertEqual(len(commands), 2)
            self.assertEqual(sleeps, [300])
            self.assertEqual(record.read_bytes(), before)
            self.assertEqual(status["controller_state"], "selected_hard_group_complete")
            self.assertTrue(all("--target-group" in command and "--http-cap" in command for command in commands))

    def test_quota_authentication_and_internal_inspection_do_not_auto_continue(self):
        for stopped in (self.service_error(429), self.service_error(403),
                        {"state": "request_limit_reached"}, {"state": "stopped_for_inspection"}):
            with tempfile.TemporaryDirectory() as temporary:
                commands, sleeps, status = self.run_states(arguments(temporary), [stopped])
                self.assertEqual(len(commands), 1)
                self.assertEqual(sleeps, [])
                self.assertEqual(status["state"], "stopped")

    def test_continuations_are_bounded_and_wait_does_not_overlap_existing_controller(self):
        with tempfile.TemporaryDirectory() as temporary:
            args = arguments(temporary)
            commands, sleeps, status = self.run_states(args, [self.service_error()]*3)
            self.assertEqual((len(commands), sleeps, status["state"]), (3, [300, 300], "continuation_limit_reached"))
        with tempfile.TemporaryDirectory() as temporary:
            args = arguments(temporary, wait_pid=123)
            supervisor.save(args.output/"run_status.json", {"state": "selected_hard_group_complete"})
            active = iter([True, False])
            calls, sleeps = [], []
            supervisor.supervise(args, run=lambda *a, **kw: calls.append(a), sleep=sleeps.append,
                                 active=lambda pid: next(active), readiness=lambda args: {"ready": True, "statuses": [200, 200]})
            self.assertEqual(calls, [])
            self.assertEqual(sleeps, [15])


if __name__ == "__main__":
    unittest.main()
