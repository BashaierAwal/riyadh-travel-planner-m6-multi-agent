"""Check controller targets and resource stops with temporary fixture records."""

import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT))

from scripts import Run_Review_Study_v5 as controller
from scripts.Run_Review_Priority import prioritize
from revision.run import Experiment


class ControllerTests(unittest.TestCase):
    def run_fixture(self, cap):
        cases = json.loads((PROJECT/"revision/cases/all.json").read_text())
        experiment = object.__new__(Experiment)
        experiment.identity = {"cases": cases, "seeds": [11, 22, 33], "conditions": ["baseline", "treatment"], "study": "main"}
        units = [item for item in prioritize(list(experiment.schedule())) if item[0]["case_id"].startswith("H")]
        calls = []
        with tempfile.TemporaryDirectory() as temporary:
            project, output = Path(temporary)/"project", Path(temporary)/"output"
            project.mkdir()

            def command(arguments, **kwargs):
                calls.append(arguments)
                if str(arguments[1]).endswith("Run_Review_Priority.py"):
                    root = output/"main-v2"
                    root.mkdir(exist_ok=True)
                    start = len(list(root.glob("*/record.json")))
                    count = int(arguments[arguments.index("--max-new-records")+1])
                    for index in range(start, start+count):
                        case, seed, condition, repeat = units[index]
                        folder = root/f"{condition}_{case['case_id']}_seed{seed}_repeat{repeat}"
                        folder.mkdir()
                        error = {"type": "BudgetError", "status": None, "message": "Model stage request limit reached"} if index == 0 else None
                        record = {"case_id": case["case_id"], "evidence_mode": "fixture",
                                  "result": {"http_requests": 1, "error": error}}
                        path = folder/"record.json"
                        path.write_text(json.dumps(record))
                        (folder/"record.sha256").write_text(controller.sha(path))
                return SimpleNamespace(returncode=0)

            arguments = ["controller", "--project", str(project), "--output", str(output),
                         "--source-commit", "fixture", "--http-cap", str(cap), "--stage", "main",
                         "--target-group", "hard", "--priority-worker", str(PROJECT/"scripts/Run_Review_Priority.py")]
            with redirect_stdout(StringIO()), patch.object(sys, "argv", arguments), patch.object(controller.subprocess, "check_output", return_value="fixture\n"), patch.object(controller.subprocess, "run", side_effect=command):
                controller.main()
            state = json.loads((output/"run_status.json").read_text())
            rows = [json.loads(p.read_text()) for p in (output/"main-v2").glob("*/record.json")]
            return state, rows, calls

    def test_hard_target_is_complete_without_claiming_full_grid(self):
        state, rows, calls = self.run_fixture(300)
        self.assertEqual(state["state"], "selected_hard_group_complete")
        self.assertEqual(len(rows), 120)
        self.assertEqual(state["stages"]["main-v2"]["completed"], 120)
        self.assertEqual(state["stages"]["main-v2"]["expected"], 240)
        self.assertEqual(sum(row["result"]["error"] is not None for row in rows), 1)
        verification = [args for args in calls if "revision.verify" in args]
        self.assertEqual(len(verification), 1)
        self.assertIn("--allow-partial", verification[0])

    def test_resource_guard_does_not_claim_completion(self):
        state, rows, _ = self.run_fixture(60)
        self.assertEqual(state["state"], "request_limit_reached")
        self.assertLess(len(rows), 120)
        self.assertLessEqual(state["http_requests_used_or_reserved"], 60)


if __name__ == "__main__":
    unittest.main()
