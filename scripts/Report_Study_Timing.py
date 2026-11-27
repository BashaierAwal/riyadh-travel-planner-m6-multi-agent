"""Report elapsed time and scheduled pacing from a verified complete cohort."""

import argparse
import csv
import json
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from revision.statistics import summarize
from revision.verify import audit


def timing_rows(records):
    rows = []
    for record in records:
        wall = record["system_wall_seconds"]
        pacing = record["pacing_wait_seconds"]
        if not (0 <= pacing <= wall):
            raise ValueError("Recorded pacing must fall within elapsed time")
        rows.append({"condition": record["condition"], "case_id": record["case_id"],
                     "seed": record["seed"], "elapsed_seconds": wall,
                     "scheduled_pacing_seconds": pacing,
                     "elapsed_excluding_pacing_seconds": wall-pacing})
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    result = audit(args.directory, PROJECT)
    if result["status"] != "complete" or result["study"] == "seed_check":
        raise ValueError("Timing comparisons require a complete registered cohort")
    rows = timing_rows(result["records"])
    identity = result["identity"]
    report = {"note": "All registered runs, including failures. Excluding pacing still includes network, tool and local processing time; it is not pure model inference time.",
              "identity_sha256": result["records"][0]["identity_sha256"], "subsets": {}}
    for subset, prefix in (("original", "G"), ("hard", "H"), ("combined", "")):
        selected = [row for row in rows if row["case_id"].startswith(prefix)]
        if not selected:
            continue
        cases = sorted({row["case_id"] for row in selected})
        values = {metric: summarize(selected, metric, seeds=identity["seeds"],
                  conditions=identity["conditions"], expected_cases=cases)
                  for metric in ("elapsed_seconds", "scheduled_pacing_seconds", "elapsed_excluding_pacing_seconds")}
        if result["study"] == "ablation":
            for value in values.values():
                value.pop("paired_second_minus_first", None)
        report["subsets"][subset] = values
    destination = args.directory / "analysis"
    destination.mkdir(exist_ok=True)
    (destination / "TIMING.json").write_text(json.dumps(report, indent=2)+"\n")
    with (destination / "TIMING.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print("Timing report saved for", len(rows), "verified records")


if __name__ == "__main__":
    main()
