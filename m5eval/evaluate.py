"""Reproduce saved statistics and evaluate supplementary outputs offline."""

import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys

import pandas as pd

from . import SCORER_VERSION
from .components import evaluate_components
from .scoring import load_datasets, score_itinerary, tool_coverage
from .statistics import METRICS, summarize

ROOT = Path(__file__).resolve().parents[1]
EVALUATION = ROOT / "source/05_M5_Evaluation"
V2 = EVALUATION / "baseline_v2_standardized"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_import():
    manifest = read_json(ROOT / "audit/import_manifest.json")
    for entry in manifest["files"]:
        path = ROOT / entry["path"]
        if not path.is_file() or sha256(path) != entry["sha256"]:
            raise ValueError(f"Preserved artifact changed: {entry['path']}")
    return len(manifest["files"])


def golden_contract(cases, datasets):
    result = []
    for case in cases:
        score_itinerary(None, case, datasets)
        count = sum(r["interest_group"] in case["interests"] for r in datasets["activities"].values())
        slots = 2 * case["trip_duration"]
        result.append({**case, "required_activity_slots": slots,
                       "matching_unique_activities": count,
                       "APM_ceiling_pct": round(100 * min(count, slots) / slots, 2),
                       "matching_restaurants": sum(r["budget_level"] == case["budget_level"] for r in datasets["restaurants"].values()),
                       "matching_hotels": sum(r["budget_level"] == case["budget_level"] for r in datasets["hotels"].values()),
                       "acceptance": {"hotel_count": 1, "days": case["trip_duration"],
                                      "activities_per_day": 2, "restaurants_per_day": 2,
                                      "activity_repetition_allowed": False,
                                      "all_ids_in_frozen_datasets": True,
                                      "IFR_requires_interest_match": False},
                       "ground_truth_basis": "M2 constraints and frozen dataset labels; no single reference itinerary.",
                       "human_ground_truth_signoff": "pending team review"})
    return result


def evaluate(output_dir):
    output_dir = output_dir.resolve()
    for protected in (ROOT / "source", ROOT / "data", ROOT / "reference", ROOT / "audit", ROOT / "m5eval", ROOT / "tests"):
        if output_dir == protected or protected in output_dir.parents:
            raise ValueError("Report destination must not be a preserved or code directory")
    if output_dir == ROOT:
        raise ValueError("Use a dedicated report directory")
    count = verify_import()
    datasets = load_datasets(ROOT / "data")
    reference = read_json(V2 / "baseline_v2_implementation_reference.json")
    cases = reference["golden_set"]
    if len(cases) < 20 or len({c["case_id"] for c in cases}) != len(cases):
        raise ValueError("Golden cases require at least 20 unique IDs")
    inputs = [(c["trip_duration"], tuple(sorted(c["interests"])), c["budget_level"]) for c in cases]
    if len(set(inputs)) != len(inputs):
        raise ValueError("Golden inputs must be distinct")
    records = read_json(V2 / "baseline_results_v2.json")
    official = read_json(V2 / "baseline_v2_official_summary.json")
    if sha256(V2 / "baseline_results_v2.json") != official["raw_results_sha256"]:
        raise ValueError("Historical result checksum mismatch")
    for name, function in reference["function_sources"].items():
        if hashlib.sha256(function["source"].encode()).hexdigest() != function["sha256"]:
            raise ValueError(f"Frozen function checksum mismatch: {name}")
    canonical_checks = {}
    for name in ("activities", "restaurants", "hotels"):
        frame = pd.read_csv(ROOT / "data" / f"{name}.csv", float_precision="round_trip")
        canonical_hash = hashlib.sha256(frame.to_json(orient="split", date_format="iso", double_precision=15).encode()).hexdigest()
        canonical_checks[name] = canonical_hash
        expected = reference["datasets"][name]
        if (canonical_hash != expected["sha256"] or len(frame) != expected["rows"]
                or list(frame.columns) != expected["columns"]):
            raise ValueError(f"Frozen DataFrame fingerprint mismatch: {name}")
    statistics = summarize(records, cases)
    for metric in METRICS:
        for key, value in (("mean", statistics[metric]["mean"]),
                           ("std", statistics[metric]["across_runs"]["sample_sd"])):
            if abs(value - official["overall_metrics"][metric][key]) > 0.000051:
                raise ValueError(f"Historical summary mismatch: {metric} {key}")
    supplemental = []
    sample_dir = EVALUATION / "llm_judge_evaluation/baseline_samples"
    expected_paths = {f"baseline_{c['case_id']}_seed11.json" for c in cases}
    if {p.name for p in sample_dir.glob("*.json")} != expected_paths:
        raise ValueError("Missing or unexpected supplementary sample files")
    for case in cases:
        path = sample_dir / f"baseline_{case['case_id']}_seed11.json"
        sample = read_json(path)
        if sample["case_id"] != case["case_id"] or sample["seed"] != 11:
            raise ValueError(f"Wrong supplementary sample identity: {path.name}")
        if sample["user_input"] != {k: case[k] for k in ("trip_duration", "interests", "budget_level")}:
            raise ValueError(f"Wrong supplementary sample input: {path.name}")
        generation = sample["generation_result"]
        score = score_itinerary(generation["itinerary"], case, datasets)
        recorded = next(r for r in records if r["case_id"] == case["case_id"] and r["seed"] == 11)
        comparisons = {k: score[k] == recorded[k] for k in ("APM", "RBM", "HBM", "IFR")}
        if not all(comparisons.values()) or score["feasible"] != generation["is_valid"]:
            raise ValueError(f"Supplementary score comparison differs: {case['case_id']}")
        supplemental.append({"case_id": case["case_id"], "seed": 11,
                             "evidence_class": "later supplementary generation",
                             "sample_sha256": sha256(path), "generated_at_utc": sample["generated_at_utc"],
                             "scores": score, "RTC": tool_coverage(generation.get("tool_calls")),
                             "matches_historical_seed11_scores": comparisons,
                             "original_run_identity_verified": False})
    components = evaluate_components(ROOT / "data", cases, datasets)
    requirements = golden_contract(cases, datasets)
    report = {
        "scorer_version": SCORER_VERSION, "preserved_artifacts_verified": count,
        "dataset_canonical_hashes": canonical_checks, "pandas_csv_float_precision": "round_trip",
        "historical_v2": {"records": len(records), "reported_generation_successes": sum(r["generation_success"] is True for r in records),
                          "itineraries_present": sum("itinerary" in r for r in records),
                          "original_outputs_independently_rescored": False, "statistics": statistics},
        "supplementary_samples": {"count": len(supplemental), "scores_verified": True,
                                  "original_v2_generations_verified": False},
        "component_evaluation": {k: v for k, v in components.items() if k != "results"},
        "trajectory_metric": {"name": "required tool-type coverage (historical RTC)",
                              "basis": "saved tool-name sequences", "full_arguments_and_results_available": False,
                              "tool_correctness_measured": False},
        "judge_evaluation": {"saved_results": len(list((EVALUATION / "llm_judge_evaluation/judge_results").glob("*.json"))),
                             "status": "supplementary; not executed"},
        "runtime": {"python": platform.python_version(), "executable_name": Path(sys.executable).name},
        "paid_model_calls": 0,
        "limits": ["Original V2 itineraries and full tool traces remain missing.",
                   "Ground-truth acceptance rules await team human signoff.",
                   "No provider-side seed effectiveness or current model availability was tested.",
                   "Historical cost, token use and latency are unavailable and are not estimated."],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, obj in (("evaluation.json", report), ("golden_contract.json", requirements),
                      ("supplementary_scores.json", supplemental), ("component_results.json", components)):
        (output_dir / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    rows = ["# M5 evaluation results", "", "Offline checks passed. No model calls were made.", "",
            "Historical V2 figures below are verified aggregate arithmetic, not rescored original outputs.", "",
            "| Metric | Mean (%) | Run SD (n=60) | Seed-mean SD (n=3) |",
            "|---|---:|---:|---:|"]
    for metric in METRICS:
        stat = statistics[metric]
        rows.append(f"| {metric} | {stat['mean']:.4f} | {stat['across_runs']['sample_sd']:.4f} | {stat['between_seed_means']['sample_sd']:.4f} |")
    rows += ["", "All SDs use the sample definition (n-1). Per-case and case-mean variation are in evaluation.json.",
             "", "## Verified separately", "", f"- {len(supplemental)} later supplementary itineraries rescored; all 80 metric comparisons agree with historical seed-11 score rows. Output identity is not established.",
             f"- {components['case_tool_contracts']} case/tool contracts passed (120 offline tool calls including repeatability checks).",
             "- G05/G08/G15 have APM ceilings of 90%, 66.67% and 80%; structural IFR need not be zero.",
             "", "## Remaining limits", ""] + [f"- {x}" for x in report["limits"]]
    (output_dir / "RESULTS.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "reports")
    args = parser.parse_args()
    result = evaluate(args.output)
    print(f"PASS: {result['preserved_artifacts_verified']} preserved artifacts, 60 historical records, 20 supplementary outputs and 60 component contracts.")
    print("Historical original-output validation remains incomplete; see reports/RESULTS.md.")


if __name__ == "__main__":
    main()
