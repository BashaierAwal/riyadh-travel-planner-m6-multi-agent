"""Recheck original evidence and add case-level statistics without new model calls."""

import argparse
from collections import Counter
import json
from pathlib import Path
import zipfile

from m5eval.scoring import load_datasets, score_itinerary
from .run import ROOT, file_hash, write_json
from .statistics import summarize
from .cost import estimate_events


def rows_from_records(records, data):
    rows, failures = [], []
    for record in records:
        case = record["user_input"]
        generation = record["generation_result"]
        actual = score_itinerary(generation.get("itinerary"),case,data)
        if actual!=record["evaluation"]:
            raise ValueError("Saved original score does not reproduce")
        condition = record.get("metadata",{}).get("condition","baseline")
        rows.append({"condition":condition,"case_id":case["case_id"],"seed":record["seed"],
                     **{k:actual[k] for k in ("APM","RBM","HBM","IFR")},"RTC":record["RTC"]})
        if not actual["feasible"]:
            errors = actual["validation_errors"]
            error = generation.get("generation_error") or {}
            if generation.get("itinerary") is None:
                label = "no_output"
                subtype = "provider" if error.get("code") else error.get("type","unreadable_output")
            elif any("unknown" in e or "Invalid hotel" in e for e in errors):
                label,subtype="invented_place","unknown_dataset_id"
            elif any("Repeated" in e for e in errors):
                label,subtype="repeated_place","activity_repeated"
            else:
                label,subtype="structure","output_contract"
            failures.append({"condition":condition,"case_id":case["case_id"],"seed":record["seed"],
                             "label":label,"subtype":subtype,"details":errors,"generation_error":error,
                             "itinerary":generation.get("itinerary")})
    return rows,failures


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--m6-records",type=Path)
    p.add_argument("--output",type=Path,default=ROOT/"revision/reports")
    args=p.parse_args()
    data=load_datasets(ROOT/"data")
    archive=ROOT/"evidence/cohorts/baseline-v3-20261107.zip"
    with zipfile.ZipFile(archive) as z:
        names=[n for n in z.namelist() if n.startswith("baseline-v3-20261107/") and n.endswith("/record.json")]
        if len(names)!=60:raise ValueError("Expected exactly 60 original V3 records, excluding pilots")
        records=[json.loads(z.read(n)) for n in names]
    cases=[c["case_id"] for c in json.loads((ROOT/"revision/cases/original.json").read_text())]
    rows,failures=rows_from_records(records,data)
    result={"scope":"Original M5 V3 records; no new model calls; no hard-case results",
            "archive_sha256":file_hash(archive),"records":60,"statistics":{},"failures":failures,
            "failure_counts":dict(Counter(f["label"] for f in failures))}
    prices=json.loads((ROOT/"revision/PRICING.json").read_text())
    costs={}
    for record in records:
        transformed=[]
        for event in record["generation_result"].get("trace",[]):
            if event["kind"]=="http_request":
                transformed.append({"kind":"http_request","number":event["request_number"],
                                    "model":record["metadata"]["model"]})
            elif event["kind"]=="http_response":
                transformed.append({"kind":"http_response","number":event["request_number"],
                                    "status":event["status_code"],"body":event["body"]})
        costs[f"{record['case_id']}_seed{record['seed']}"]=estimate_events(transformed,prices)
    for metric in ("APM","RBM","HBM","IFR","RTC"):
        result["statistics"][metric]=summarize(rows,metric,conditions=("baseline",),expected_cases=cases)
    args.output.mkdir(parents=True,exist_ok=True)
    write_json(args.output/"M5_V3_RECHECK.json",result)
    write_json(args.output/"M5_V3_COST_ESTIMATES.json",{
        "scope":"Historical V3 usage at standard uncached list prices checked on 27 November 2026; not actual billing",
        "records":costs})
    report=["# Review of the original M5 baseline", "",
        "The baseline is V3: 60 saved runs from 20 fixed cases and three requested seeds. "
        "All scores below were recalculated from the saved plans and unchanged CSVs. V2 is historical only. "
        "This review does not contain results for the new hard cases.","",
        "| Metric | Mean (%) | SD of three seed means |", "|---|---:|---:|"]
    for metric in result["statistics"]:
        s=result["statistics"][metric]["conditions"]["baseline"]
        report.append(f"| {metric} | {s['mean']:.2f} | {s['sd_across_seed_means']:.2f} |")
    pass3=result["statistics"]["IFR"]["conditions"]["baseline"]["pass3"]
    report += ["",f"**Success on all three runs (pass³): {100*pass3:.1f}% of cases.** "
        "A case counts only when all three saved outputs pass structural IFR. This does not verify that the provider honors seeds.","",
        "The eleven structural failures comprise nine plans with repeated activities and two missing or unreadable outputs. "
        "The repeated activities occur in G05, G08 and G15 at all three seeds. G07/11 ends with a provider quota error; "
        "G07/22 has an unexpected text prefix before JSON. Full examples and their saved plans are in M5_V3_RECHECK.json.","",
        "The current tests leave little room for improvement: all readable plans match the hotel and restaurant budget labels. "
        "RTC also reaches 100% for the two failed generations. It therefore measures tool coverage, not successful planning. "
        "The new distance, SAR hotel cap and competing-interest cases address this limit.","",
        "The original design can reuse a highly ranked activity when too few matching unique activities exist. "
        "That observation motivates checking and repairing complete plans, but the new component-removal experiments are "
        "still required to test whether repairs or the feasibility specialist explain any improvement."]
    report += ["","Per-case list-price estimates are in M5_V3_COST_ESTIMATES.json. They use the exact recorded model and "
        "official prices checked on 27 November 2026. Failed requests or missing usage leave a partial observed subtotal "
        "rather than an invented complete cost. These estimates do not establish what the account was charged."]
    (args.output/"M5_V3_RECHECK.md").write_text("\n".join(report)+"\n")
    if args.m6_records:
        paths=sorted(args.m6_records.glob("*/record.json"))
        if len(paths)!=120:raise ValueError("Expected exactly 120 old M6 records")
        old=[json.loads(path.read_text()) for path in paths]
        rows,failures=rows_from_records(old,data)
        summary={"scope":"Earlier M6 experiment, original 20 cases; separate from the revised comparison",
                 "record_sha256":{str(p.relative_to(args.m6_records)):file_hash(p) for p in paths},
                 "statistics":{},"failures":failures}
        for metric in ("APM","RBM","HBM","IFR","RTC"):
            summary["statistics"][metric]=summarize(rows,metric,expected_cases=cases)
        write_json(args.output/"M6_EARLIER_RECHECK.json",summary)
    print("Recalculated original baseline scores and pass3; earlier M6 comparison analysed" if args.m6_records else "Recalculated baseline scores and pass3")


if __name__=="__main__":main()
