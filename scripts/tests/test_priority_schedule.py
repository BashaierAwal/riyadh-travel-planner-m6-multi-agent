"""Check priority scheduling without changing cases or making model requests."""

from collections import Counter
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT))

from scripts import Run_Review_Priority as worker
from revision.run import Experiment, digest, file_hash, write_json
from revision.verify import audit
from scripts.Verify_Study_Replay import audit as priority_audit


class PriorityTests(unittest.TestCase):
    def test_all_units_and_within_case_order_are_preserved(self):
        cases = json.loads((PROJECT/"revision/cases/all.json").read_text())
        for conditions in (["baseline", "treatment"], ["without_feasibility", "without_repair"], ["strong_coordinator"]):
            experiment = object.__new__(Experiment)
            experiment.identity = {"cases": cases, "seeds": [11, 22, 33], "conditions": conditions, "study": "main"}
            original = list(experiment.schedule())
            for finish in ([], ["G02"]):
                queue = worker.prioritize(original, finish)
                encode = lambda item: json.dumps(item, sort_keys=True)
                self.assertEqual(Counter(map(encode, original)), Counter(map(encode, queue)))
                for case in cases:
                    cid = case["case_id"]
                    self.assertEqual([x for x in original if x[0]["case_id"] == cid],
                                     [x for x in queue if x[0]["case_id"] == cid])
                self.assertEqual(queue[0][0]["case_id"], "G02" if finish else "H01")

    def test_fixture_finishes_started_case_and_keeps_existing_record(self):
        case = json.loads((PROJECT/"revision/cases/hard.json").read_text())[0]
        plan = json.loads((PROJECT/"revision/cases/feasibility_witnesses.json").read_text())[0]["witness"]

        class Fixture:
            mode, pacing, timeout = "fixture", 12, 60
            total_calls = 0

            def __init__(self, key, cap):
                self.count, self.cap = 0, cap

            def sanitize(self, value):
                return value

            def complete(self, prompt, tools, seed, model, emit, **kwargs):
                self.count += 1
                Fixture.total_calls += 1
                emit({"kind": "http_request", "model": model, "body": {"fixture": True}})
                emit({"kind": "http_response", "model": model, "status": 200,
                      "body": {"usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 1, "totalTokenCount": 2}}})
                if "Role: coordinator_dispatch" in prompt:
                    return {"activity_task": "fixture", "feasibility_task": "fixture"}
                allowed = kwargs.get("allowed", [])
                if "find_hotels" in allowed:
                    tools.call("find_hotels", {"budget_level": "Low", "limit": 100})
                for day in plan["days"]:
                    if "find_activities" in allowed:
                        for pid in day["activities"]:
                            tools.call("find_activities", {"interests": case["interests"], "center_id": pid, "limit": 1})
                    if "find_restaurants" in allowed:
                        for pid in day["restaurants"]:
                            tools.call("find_restaurants", {"budget_level": "Low", "center_id": pid, "limit": 1})
                if "check_plan" in allowed:
                    tools.call("check_plan", {"plan_json": json.dumps(plan)})
                return json.loads(json.dumps(plan))

        with tempfile.TemporaryDirectory() as temporary:
            experiment = Experiment(temporary, "priority-fixture", Fixture(None, 240), "test-model")
            experiment.run(1)
            saved = next(experiment.root.glob("*/record.json"))
            original_hash = file_hash(saved)
            original_identity = (experiment.root/"manifest.json").read_bytes()
            arguments = ["priority", "--project", str(PROJECT), "--study", "main", "--version", "priority-fixture",
                         "--model", "test-model", "--max-requests", "240", "--max-new-records", "5", "--output", temporary]
            loaded = (Experiment, Fixture, digest, file_hash, write_json, audit)
            with patch.object(worker, "load_project", return_value=loaded), patch.object(sys, "argv", arguments):
                worker.main()
            receipt = json.loads((experiment.root/"priority_execution_v1.json").read_text())
            self.assertEqual(receipt["policy"]["finish_started_original_cases"], ["G01"])
            self.assertEqual(len(list(experiment.root.glob("*G01*/record.json"))), 6)
            self.assertFalse(list(experiment.root.glob("*H*/record.json")))
            self.assertEqual(file_hash(saved), original_hash)
            self.assertEqual((experiment.root/"manifest.json").read_bytes(), original_identity)
            arguments[arguments.index("--max-new-records")+1] = "1"
            with patch.object(worker, "load_project", return_value=loaded), patch.object(sys, "argv", arguments):
                worker.main()
            self.assertEqual(len(list(experiment.root.glob("*H01*/record.json"))), 1)
            self.assertEqual(audit(experiment.root)["evidence_mode"], "fixture")
            self.assertIsNotNone(priority_audit(experiment.root)["numeric_replay"]["execution_priority"])
            snapshot = experiment.root/receipt["policy"]["worker_snapshot"]
            snapshot.write_text(snapshot.read_text()+"\n# changed\n")
            calls_before = Fixture.total_calls
            with patch.object(worker, "load_project", return_value=loaded), patch.object(sys, "argv", arguments):
                with self.assertRaisesRegex(ValueError, "priority changed"):
                    worker.main()
            self.assertEqual(Fixture.total_calls, calls_before)
            with self.assertRaisesRegex(ValueError, "snapshot hash"):
                priority_audit(experiment.root)


if __name__ == "__main__":
    unittest.main()
