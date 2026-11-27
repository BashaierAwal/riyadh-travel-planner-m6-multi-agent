"""Guard predefined-group reporting with explicitly synthetic audit fixtures."""

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT))

from scripts import Report_Study_Group as reporter
from revision.statistics import summarize


def fixture(study="main"):
    conditions = {"main": ["baseline", "treatment"], "ablation": ["without_feasibility", "without_repair"],
                  "strong_coordinator": ["strong_coordinator"]}[study]
    cases = json.loads((PROJECT/"revision/cases/all.json").read_text())
    identity = {key: "fixture" for key in reporter.SHARED}
    identity.update(cases=cases, seeds=[11, 22, 33], conditions=conditions, evidence_mode="fixture",
                    coordinator_model="different-fixture-model" if study == "strong_coordinator" else None)
    rows, records = [], []
    for case in cases[20:]:
        for seed in identity["seeds"]:
            for condition in conditions:
                name = f"{condition}_{case['case_id']}_seed{seed}_repeat1"
                row = {key: 100 for key in reporter.METRICS}
                row.update(condition=condition, case_id=case["case_id"], seed=seed, repeat=1,
                           record=name, primary_failure_label="no_output", all_failure_labels=["no_output"],
                           constraint_pass=0, system_wall_seconds=10)
                rows.append(row)
                records.append({"condition": condition, "case_id": case["case_id"], "seed": seed,
                    "case": case, "system_wall_seconds": 10, "pacing_wait_seconds": 2,
                    "result": {"itinerary": None, "error": {"type": "FixtureFailure"},
                               "evaluation": {"constraints": {"violations": [{"kind": "no_output"}]}}}})
    return {"study": study, "identity": identity, "rows": rows, "records": records,
            "evidence_mode": "fixture", "status": "incomplete", "completed": len(rows),
            "expected": 40*3*len(conditions), "missing": ["fixture original-group records"],
            "interrupted": [], "numeric_replay": {"evidence_mode": "fixture"}}


class GroupTests(unittest.TestCase):
    def test_requires_the_whole_predefined_matrix_including_failed_attempts(self):
        result = fixture()
        cases, rows, records = reporter.complete_group(result, "hard")
        self.assertEqual((len(cases), len(rows), len(records)), (20, 120, 120))
        for change in (lambda x: x["rows"].pop(),
                       lambda x: x["rows"].append(deepcopy(x["rows"][0])),
                       lambda x: x["records"].pop(),
                       lambda x: x["identity"]["cases"][20].update(budget_level="changed"),
                       lambda x: x["identity"].update(seeds=[11, 22]),
                       lambda x: x["rows"][0].update(repeat=2)):
            broken = deepcopy(result)
            change(broken)
            with self.assertRaises(ValueError):
                reporter.complete_group(broken, "hard")
        with self.assertRaises(ValueError):
            reporter.complete_group(result, "original")

    def test_complete_group_report_retains_failures_and_overall_incomplete_status(self):
        result = fixture()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for row in result["rows"]:
                (root/row["record"]).mkdir()
                (root/row["record"]/"events.jsonl").write_text("")
            fast_summary = lambda *a, **kw: summarize(*a, **kw, draws=20)
            with patch.object(reporter, "audit", return_value=result), patch.object(reporter, "summarize", side_effect=fast_summary):
                report = reporter.report_group(root, "hard")
            self.assertEqual(report["group_status"], "complete")
            self.assertEqual(report["overall_status"], "incomplete")
            self.assertEqual(report["evidence_mode"], "fixture")
            self.assertEqual(report["failure_counts"], {"baseline": {"no_output": 60}, "treatment": {"no_output": 60}})
            self.assertEqual(report["statistics"]["constraint_pass"]["conditions"]["baseline"]["mean"], 0)
            self.assertEqual(report["statistics"]["constraint_pass"]["conditions"]["baseline"]["pass3"], 0)
            self.assertEqual(report["timing"]["elapsed_excluding_pacing_seconds"]["conditions"]["baseline"]["mean"], 8)

    def test_variant_comparison_rejects_partial_or_mismatched_groups(self):
        main, ablation = fixture(), fixture("ablation")
        fast_summary = lambda *a, **kw: summarize(*a, **kw, draws=20)
        with patch.object(reporter, "audit", side_effect=[main, ablation]), patch.object(reporter, "summarize", side_effect=fast_summary):
            report = reporter.compare_group("main", "ablation", "without_feasibility", "hard")
        self.assertEqual(report["statistics"]["constraint_pass"]["paired_second_minus_first"]["n_cases"], 20)
        variants = [deepcopy(ablation) for _ in range(3)]
        variants[0]["rows"].pop()
        variants[1]["identity"]["temperature"] = "changed"
        variants[2]["identity"]["coordinator_model"] = "changed"
        for changed in variants:
            with patch.object(reporter, "audit", side_effect=[main, changed]):
                with self.assertRaises(ValueError):
                    reporter.compare_group("main", "ablation", "without_feasibility", "hard")


if __name__ == "__main__":
    unittest.main()
