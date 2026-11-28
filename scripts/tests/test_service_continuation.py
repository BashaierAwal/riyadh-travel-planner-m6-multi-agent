"""Exercise the external continuation policy without any generation request."""

import argparse
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT))
from scripts import Continue_Review_Study as supervisor


def arguments(root, **extra):
    values = dict(controller=PROJECT/"scripts/Run_Review_Study_v5.py", project=PROJECT,
                  priority_worker=PROJECT/"scripts/Run_Review_Priority.py", output=Path(root),
                  source_commit="fixture-only-no-provider-request", http_cap=3600,
                  stage="second_model", target_group="hard", cooldown_seconds=300,
                  max_continuations=2, wait_pid=None)
    values.update(extra)
    return argparse.Namespace(**values)


class ContinuationTests(unittest.TestCase):
    def run_states(self, args, states):
        commands, sleeps = [], []
        def run(command, **kwargs):
            commands.append(command)
            value = states[len(commands)-1]
            supervisor.save(args.output/"run_status.json", value)
            return SimpleNamespace(returncode=0)
        supervisor.supervise(args, run=run, sleep=sleeps.append)
        return commands, sleeps, json.loads((args.output/"continuation_second_model_hard_status.json").read_text())

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
                                 active=lambda pid: next(active))
            self.assertEqual(calls, [])
            self.assertEqual(sleeps, [15])


if __name__ == "__main__":
    unittest.main()
