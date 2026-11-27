"""Adversarial checks for route-only numerical replay; no live requests."""

import copy
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT))

from scripts.Verify_Study_Replay import RouteComparison, export
from revision import verify
from revision.provider import Gemini
from revision.run import Experiment, digest, file_hash


def shift_routes(value, path=()):
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = path+(key,)
            if (len(child_path) >= 3 and child_path[-3] == "routes"
                    and type(child_path[-2]) is int and key == "km" and type(child) is float):
                value[key] = math.nextafter(child, math.inf)
            else:
                shift_routes(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            shift_routes(child, path+(index,))


class ReplayTests(unittest.TestCase):
    def test_only_small_route_numbers_may_differ(self):
        a = {"routes": [{"day": 1, "km": 1.5}], "passed": True, "hotel_cost_sar": 266.25}
        b = copy.deepcopy(a)
        b["routes"][0]["km"] = math.nextafter(1.5, math.inf)
        comparison = RouteComparison()
        self.assertTrue(comparison.equal(a, b))
        self.assertEqual(comparison.rounding_comparisons, 1)
        for key, value in (("passed", False), ("hotel_cost_sar", math.nextafter(266.25, math.inf))):
            bad = copy.deepcopy(b)
            bad[key] = value
            self.assertFalse(comparison.equal(a, bad))
        b["routes"][0]["km"] = 1.500001
        self.assertFalse(comparison.equal(a, b))
        self.assertFalse(comparison.equal({"score": 1.5}, {"score": math.nextafter(1.5, math.inf)}))
        self.assertFalse(comparison.equal({"km": 1.5}, {"km": math.nextafter(1.5, math.inf)}))
        self.assertFalse(comparison.equal({"ids": ["ACT_1", "ACT_2"]}, {"ids": ["ACT_2", "ACT_1"]}))

    def test_fixture_replay_accepts_rounding_but_rejects_changed_score(self):
        case = json.loads((PROJECT/"revision/cases/hard.json").read_text())[0]
        plan = json.loads((PROJECT/"revision/cases/feasibility_witnesses.json").read_text())[0]["witness"]

        def response(parts):
            return {"candidates": [{"content": {"role": "model", "parts": parts}}],
                    "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5, "totalTokenCount": 15}}

        def transport(model, body):
            prompt = body["contents"][0]["parts"][0]["text"]
            if "Role: coordinator_dispatch" in prompt:
                return response([{"text": json.dumps({"activity_task": "choose", "feasibility_task": "check"})}])
            if len(body["contents"]) == 1:
                allowed = {d["name"] for tool in body.get("tools", []) for d in tool["functionDeclarations"]}
                calls = []
                if "find_hotels" in allowed:
                    calls.append({"name": "find_hotels", "args": {"budget_level": "Low", "limit": 100}})
                for day in plan["days"]:
                    if "find_activities" in allowed:
                        calls.extend({"name": "find_activities", "args": {"interests": case["interests"], "center_id": p, "limit": 1}}
                                     for p in day["activities"])
                    if "find_restaurants" in allowed:
                        calls.extend({"name": "find_restaurants", "args": {"budget_level": "Low", "center_id": p, "limit": 1}}
                                     for p in day["restaurants"])
                if "check_plan" in allowed:
                    calls.append({"name": "check_plan", "args": {"plan_json": json.dumps(plan)}})
                return response([{"functionCall": c} for c in calls])
            return response([{"text": json.dumps(plan)}])

        backend = Gemini("fixture-only", 200, transport=transport, sleep=lambda _: None)
        with tempfile.TemporaryDirectory() as temporary:
            experiment = Experiment(temporary, "numeric-fixture", backend, "test-model", study="pilot")
            experiment.run(2)
            self.assertEqual(verify.audit(experiment.root)["status"], "complete")
            for folder in experiment.root.iterdir():
                if not (folder/"record.json").exists():
                    continue
                events = [json.loads(s) for s in (folder/"events.jsonl").read_text().splitlines()]
                record = json.loads((folder/"record.json").read_text())
                shift_routes(events)
                shift_routes(record)
                record["events_sha256"] = digest(events)
                (folder/"events.jsonl").write_text("\n".join(json.dumps(e) for e in events)+"\n")
                (folder/"record.json").write_text(json.dumps(record))
                (folder/"record.sha256").write_text(file_hash(folder/"record.json"))
            with self.assertRaisesRegex(ValueError, "scores"):
                verify.audit(experiment.root)
            receipt = export(experiment.root)
            self.assertEqual(receipt["status"], "complete")
            self.assertEqual(receipt["evidence_mode"], "fixture")
            self.assertGreater(receipt["rounding_comparisons"], 0)
            saved = next(experiment.root.glob("*/record.json"))
            record = json.loads(saved.read_text())
            record["result"]["evaluation"]["original_metrics"]["APM"] = math.nextafter(
                record["result"]["evaluation"]["original_metrics"]["APM"], -math.inf)
            saved.write_text(json.dumps(record))
            (saved.parent/"record.sha256").write_text(file_hash(saved))
            original = verify.evaluate
            with self.assertRaisesRegex(ValueError, "scores"):
                export(experiment.root)
            self.assertIs(verify.evaluate, original)


if __name__ == "__main__":
    unittest.main()
