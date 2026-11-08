"""Aggregation of complete saved score records; no model execution."""

from math import isfinite
from statistics import mean, stdev

from .scoring import tool_coverage

METRICS = ("APM", "RBM", "HBM", "IFR", "RTC")


def summarize(records, cases, seeds=(11, 22, 33)):
    expected = {(c["case_id"], seed) for c in cases for seed in seeds}
    if len(expected) != len(cases) * len(seeds):
        raise ValueError("Case IDs and seeds must be unique")
    pairs = [(r["case_id"], r["seed"]) for r in records]
    if len(pairs) != len(set(pairs)) or set(pairs) != expected:
        raise ValueError("Missing, unexpected or duplicate case/seed records")
    by_case = {c["case_id"]: c for c in cases}
    values = []
    for record in records:
        case = by_case[record["case_id"]]
        if type(record["seed"]) is not int:
            raise ValueError("Seed labels must be integers")
        for key in ("trip_duration", "interests", "budget_level"):
            if type(record[key]) is not type(case[key]) or record[key] != case[key]:
                raise ValueError(f"Input mismatch: {record['case_id']} {key}")
        row = {k: record[k] for k in METRICS if k != "RTC"}
        if any(type(v) not in (int, float) or not isfinite(v) or not 0 <= v <= 100 for v in row.values()):
            raise ValueError("Scores must be finite percentages")
        row.update(case_id=record["case_id"], seed=record["seed"], RTC=tool_coverage(record.get("tool_calls")))
        values.append(row)
    result = {}
    for metric in METRICS:
        run_values = [r[metric] for r in values]
        seed_means = {str(seed): mean(r[metric] for r in values if r["seed"] == seed) for seed in seeds}
        case_means = {c["case_id"]: mean(r[metric] for r in values if r["case_id"] == c["case_id"]) for c in cases}
        result[metric] = {
            "mean": mean(run_values), "across_runs": {"n": len(run_values), "sample_sd": stdev(run_values)},
            "between_seed_means": {"n": len(seeds), "sample_sd": stdev(seed_means.values()), "means": seed_means},
            "between_case_means": {"n": len(cases), "sample_sd": stdev(case_means.values())},
            "per_case": {c["case_id"]: {"mean": case_means[c["case_id"]], "n": len(seeds),
                         "sample_sd": stdev(r[metric] for r in values if r["case_id"] == c["case_id"])} for c in cases},
        }
    return result
