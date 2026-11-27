"""Report a complete predefined group without claiming the whole study is complete."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from revision.cost import estimate_events
from revision.run import digest, file_hash
from revision.statistics import summarize
from scripts.Report_Study_Timing import timing_rows
from scripts.Verify_Study_Replay import audit


METRICS = ("APM", "RBM", "HBM", "IFR", "RTC", "constraint_pass",
           "violation_count", "repair_rounds", "tool_calls", "http_requests",
           "system_wall_seconds")
SHARED = ("policy", "evidence_mode", "model", "temperature", "max_repairs",
          "http_per_record", "max_output_tokens_per_request", "pacing_seconds",
          "timeout_seconds", "retries", "cases", "seeds", "dataset_sha256", "source_sha256")


def complete_group(result, group, project=PROJECT):
    if group not in ("hard", "original"):
        raise ValueError("Use a predefined original or hard group")
    if result["study"] not in ("main", "second_model", "ablation", "strong_coordinator"):
        raise ValueError("This report requires a registered formal study")
    identity = result["identity"]
    cases = json.loads((Path(project)/"revision/cases"/(group+".json")).read_text())
    registered = [case for case in identity["cases"] if case["case_id"].startswith("H" if group == "hard" else "G")]
    if registered != cases or len(cases) != 20 or identity["seeds"] != [11, 22, 33]:
        raise ValueError("The full predefined 20 cases and three seeds must be registered unchanged")
    ids = [case["case_id"] for case in cases]
    conditions = {"main": ["baseline", "treatment"], "second_model": ["baseline", "treatment"],
                  "ablation": ["without_feasibility", "without_repair"],
                  "strong_coordinator": ["strong_coordinator"]}[result["study"]]
    if identity["conditions"] != conditions:
        raise ValueError("Registered study conditions differ")
    expected = {(condition, cid, seed) for condition in conditions for cid in ids for seed in identity["seeds"]}
    rows = [row for row in result["rows"] if row["case_id"] in ids]
    keys = [(row["condition"], row["case_id"], row["seed"]) for row in rows]
    if len(keys) != len(set(keys)) or set(keys) != expected or any(row["repeat"] != 1 for row in rows):
        raise ValueError("Incomplete or duplicate predefined group: report progress only")
    records = [record for record in result["records"] if record["case_id"] in ids]
    record_keys = [(record["condition"], record["case_id"], record["seed"]) for record in records]
    if len(record_keys) != len(set(record_keys)) or set(record_keys) != expected:
        raise ValueError("Group records do not match its complete score matrix")
    return ids, rows, records


def report_group(directory, group, project=PROJECT):
    directory, project = Path(directory), Path(project)
    result = audit(directory, project)
    cases, rows, records = complete_group(result, group, project)
    identity = result["identity"]
    statistics = {metric: summarize(rows, metric, seeds=identity["seeds"],
                  conditions=identity["conditions"], expected_cases=cases) for metric in METRICS}
    timing = {metric: summarize(timing_rows(records), metric, seeds=identity["seeds"],
              conditions=identity["conditions"], expected_cases=cases)
              for metric in ("elapsed_seconds", "scheduled_pacing_seconds", "elapsed_excluding_pacing_seconds")}
    if result["study"] == "ablation":
        for value in [*statistics.values(), *timing.values()]:
            value.pop("paired_second_minus_first", None)
    prices = json.loads((project/"revision/PRICING.json").read_text())
    costs = {}
    examples = {}
    indexed_records = {(record["condition"], record["case_id"], record["seed"]): record for record in records}
    execution_errors = Counter()
    for row in rows:
        record = indexed_records[row["condition"], row["case_id"], row["seed"]]
        events = [json.loads(line) for line in (directory/row["record"]/"events.jsonl").read_text().splitlines()]
        costs[row["record"]] = estimate_events(events, prices)
        error = record["result"]["error"]
        if error:
            execution_errors[(row["condition"], error["type"], error.get("status"), error.get("stage"))] += 1
        label = row["primary_failure_label"]
        if label:
            examples.setdefault(row["condition"]+"/"+label, {"record": row["record"],
                "case": record["case"], "plan": record["result"]["itinerary"],
                "error": record["result"]["error"],
                "violations": record["result"]["evaluation"]["constraints"]["violations"]})
    return {"group": group, "group_status": "complete", "case_ids": cases,
            "records": len(rows), "study": result["study"], "evidence_mode": result["evidence_mode"],
            "overall_status": result["status"], "overall_completed": result["completed"],
            "overall_expected": result["expected"], "overall_missing": result["missing"],
            "overall_interrupted": result["interrupted"], "identity_sha256": digest(identity),
            "numeric_replay": result["numeric_replay"], "reporter_sha256": file_hash(__file__),
            "statistics": statistics, "timing": timing, "cost_estimates": costs,
            "execution_errors": [{"condition": key[0], "type": key[1], "status": key[2],
                "stage": key[3], "count": count} for key, count in execution_errors.items()],
            "failure_counts": {condition: dict(Counter(row["primary_failure_label"] for row in rows
                if row["condition"] == condition and row["primary_failure_label"])) for condition in identity["conditions"]},
            "failure_examples": examples,
            "scope": "Only the complete predefined group is compared. All requested seeds and failed attempts remain included. This does not establish completion of the full 40-case study.",
            "timing_note": "Excluding scheduled pacing still includes network, tool and local processing time; it is not pure inference time.",
            "cost_note": "Dated standard list-price equivalents, not actual charges. Missing usage stays unknown.",
            "interpretation": "Paired tests use case means across three seeds. Secondary outcomes and multiple comparisons are exploratory. Failure labels describe outcomes, not established causes. Fixture evidence is software testing only."}


def compare_group(main_directory, variant_directory, variant, group, project=PROJECT):
    if variant not in ("without_feasibility", "without_repair", "strong_coordinator"):
        raise ValueError("Use a registered team variant")
    main, changed = audit(main_directory, project), audit(variant_directory, project)
    if main["study"] != "main" or changed["study"] != ("strong_coordinator" if variant == "strong_coordinator" else "ablation"):
        raise ValueError("Wrong study kind for the requested variant")
    cases, main_rows, _ = complete_group(main, group, project)
    other_cases, changed_rows, _ = complete_group(changed, group, project)
    if cases != other_cases or any(main["identity"][key] != changed["identity"][key] for key in SHARED):
        raise ValueError("The groups have different settings, cases, data or source")
    if main["identity"]["coordinator_model"] is not None:
        raise ValueError("The reference must use the original team coordinator")
    if variant != "strong_coordinator" and changed["identity"]["coordinator_model"] is not None:
        raise ValueError("Component removal must preserve the coordinator model")
    if variant == "strong_coordinator" and (not changed["identity"]["coordinator_model"]
            or changed["identity"]["coordinator_model"] == main["identity"]["model"]):
        raise ValueError("The coordinator condition must use a different model")
    rows = [row for row in main_rows if row["condition"] == "treatment"]
    rows += [row for row in changed_rows if row["condition"] == variant]
    return {"group": group, "group_status": "complete", "comparison": variant+" minus treatment",
            "evidence_mode": main["evidence_mode"], "overall_status": [main["status"], changed["status"]],
            "identity_sha256": [digest(main["identity"]), digest(changed["identity"])],
            "numeric_replay": [main["numeric_replay"], changed["numeric_replay"]],
            "scope": "All 20 predefined cases and three seeds in both groups; full grids may remain incomplete. Settings match, but execution times can still differ. Secondary comparisons are exploratory.",
            "statistics": {metric: summarize(rows, metric, seeds=main["identity"]["seeds"],
                conditions=["treatment", variant], expected_cases=cases) for metric in METRICS}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--group", required=True, choices=("hard", "original"))
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--variant", choices=("without_feasibility", "without_repair", "strong_coordinator"))
    args = parser.parse_args()
    if bool(args.reference) != bool(args.variant):
        parser.error("Reference and variant are required together")
    report = (compare_group(args.reference, args.directory, args.variant, args.group) if args.reference
              else report_group(args.directory, args.group))
    destination = args.directory/"analysis"
    destination.mkdir(exist_ok=True)
    name = args.group.upper()+("_"+args.variant+"_VERSUS_FULL_TEAM" if args.reference else "_GROUP")
    (destination/(name+".json")).write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({key: report[key] for key in ("group", "group_status", "evidence_mode", "overall_status")}))


if __name__ == "__main__":
    main()
