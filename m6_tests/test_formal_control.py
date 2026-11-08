import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

MODULE = Path(__file__).resolve().parents[1] / "scripts/M6_Run_Formal.py"
spec = importlib.util.spec_from_file_location("formal_control", MODULE)
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


class FormalControlTests(unittest.TestCase):
    def write_record(self, project, number, error=None):
        folder = Path(project) / "m6_runs/formal-v1" / f"fixture_{number}"
        folder.mkdir(parents=True)
        (folder / "record.json").write_text(json.dumps({"generation_result": {"generation_error": error}}))
        (folder / "events.jsonl").write_text(json.dumps({"kind": "http_request"}) + "\n")

    def test_no_approval_never_invokes_runner(self):
        with TemporaryDirectory() as p:
            with self.assertRaises(PermissionError):
                control.run_formal(p, batch_runner=lambda args: self.fail("No API action allowed"))

    def test_full_study_has_twenty_bounded_calls_and_no_extra_records(self):
        with TemporaryDirectory() as p:
            calls, checkpoints = [], []
            def runner(args):
                calls.append(args)
                count = int(args[args.index("--max-new-records") + 1])
                self.assertLessEqual(count, 6)
                self.assertEqual(int(args[args.index("--http-cap") + 1]), 30 * count)
                start = control.inspect_saved(Path(p) / "m6_runs/formal-v1")["records"]
                for n in range(start, start + count):
                    self.write_record(p, n)
            result = control.run_formal(p, approved=True, batch_runner=runner,
                                        checkpoint=lambda root, state: checkpoints.append(state.copy()))
            self.assertEqual(result["records"], 120)
            self.assertEqual(len(calls), 20)
            self.assertEqual(len(checkpoints), 20)
            control.run_formal(p, approved=True, batch_runner=lambda args: self.fail("No reruns"))

    def test_terminal_provider_failure_stops_new_batches(self):
        with TemporaryDirectory() as p:
            calls = []
            def runner(args):
                calls.append(args)
                self.write_record(p, 0, {"type": "ProviderFailure", "code": 429})
            result = control.run_formal(p, approved=True, batch_runner=runner)
            self.assertEqual(len(calls), 1)
            self.assertEqual(result["terminal_errors"], 1)
            control.run_formal(p, approved=True, batch_runner=lambda args: self.fail("Must stop on saved service error"))

    def test_incomplete_record_blocks_before_api(self):
        with TemporaryDirectory() as p:
            (Path(p) / "m6_runs/formal-v1/incomplete").mkdir(parents=True)
            with self.assertRaises(ValueError):
                control.run_formal(p, approved=True, batch_runner=lambda args: self.fail("No API action allowed"))

    def test_saved_request_cap_is_a_hard_limit(self):
        with TemporaryDirectory() as p:
            self.write_record(p, 0)
            folder = Path(p) / "m6_runs/formal-v1/fixture_0"
            (folder / "events.jsonl").write_text((json.dumps({"kind": "http_request"}) + "\n") * 3601)
            with self.assertRaises(ValueError):
                control.run_formal(p, approved=True, batch_runner=lambda args: self.fail("No API action allowed"))
