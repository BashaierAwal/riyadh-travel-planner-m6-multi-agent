"""Pair a full team with a component-removal or coordinator-only variant."""

import argparse
from pathlib import Path

from .run import ROOT, write_json
from .statistics import summarize
from .verify import audit


def compare(main_directory, variant_directory, variant, *, project=ROOT):
    main,changed=audit(main_directory,project),audit(variant_directory,project)
    if any(x["status"]!="complete" for x in (main,changed)):
        raise ValueError("Both comparison grids must be complete")
    if variant not in ("without_feasibility","without_repair","strong_coordinator"):
        raise ValueError("Use a registered team variant")
    if main["study"]!="main" or changed["study"] not in ("ablation","strong_coordinator"):
        raise ValueError("Wrong experiment kind for this comparison")
    shared=("policy","evidence_mode","model","temperature","max_repairs","http_per_record","max_output_tokens_per_request",
            "pacing_seconds","timeout_seconds","retries","cases","seeds","dataset_sha256","source_sha256")
    if any(main["identity"][k]!=changed["identity"][k] for k in shared):
        raise ValueError("Shared conditions differ between experiments")
    rows=[r for r in main["rows"] if r["condition"]=="treatment"]
    rows += [r for r in changed["rows"] if r["condition"]==variant]
    result={"comparison":f"{variant} minus treatment","evidence_mode":main["evidence_mode"],
            "scope":"Separate cohorts with matching settings; execution times can still differ",
            "statistics":{}}
    for subset,prefix in (("original","G"),("hard","H"),("combined",None)):
        selected=[r for r in rows if prefix is None or r["case_id"].startswith(prefix)]
        if not selected:continue
        cases=sorted({r["case_id"] for r in selected})
        result["statistics"][subset]={metric:summarize(selected,metric,
            conditions=("treatment",variant),seeds=main["identity"]["seeds"],expected_cases=cases)
            for metric in ("constraint_pass","violation_count","IFR","repair_rounds","tool_calls","system_wall_seconds")}
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("main_directory",type=Path)
    p.add_argument("variant_directory",type=Path)
    p.add_argument("variant")
    args=p.parse_args()
    result=compare(args.main_directory,args.variant_directory,args.variant)
    destination=args.variant_directory/"analysis"
    destination.mkdir(exist_ok=True)
    write_json(destination/f"{args.variant}_VERSUS_FULL_TEAM.json",result)
    print(result["comparison"])


if __name__=="__main__":main()
