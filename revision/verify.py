"""Audit revised records, recompute scores and export complete-cohort comparisons."""

import argparse
from collections import Counter
import csv
import json
from pathlib import Path

from m5eval.scoring import load_datasets
from .constraints import evaluate
from .run import ROOT, digest, file_hash, write_json
from .statistics import summarize
from .tools import Tools
from .workflow import SEARCH


def audit(directory, project=ROOT):
    directory, project = Path(directory), Path(project)
    manifest = json.loads((directory/"manifest.json").read_text())
    identity = manifest["identity"]
    if digest(identity)!=manifest["sha256"]:
        raise ValueError("Manifest hash mismatch")
    for name, expected in identity["dataset_sha256"].items():
        if file_hash(project/"data"/(name+".csv"))!=expected:
            raise ValueError("Dataset changed")
    for name, expected in identity["source_sha256"].items():
        if file_hash(project/name)!=expected:
            raise ValueError("Source changed; use the saved source snapshot to verify this experiment")
    data=load_datasets(project/"data")
    expected={}
    for c in identity["cases"]:
        for s in identity["seeds"]:
            for k in identity["conditions"]:
                for repeat in (1,2) if identity["study"]=="seed_check" else (1,):
                    expected[f"{k}_{c['case_id']}_seed{s}_repeat{repeat}"]=(c,s,k,repeat)
    folders={p.name:p for p in directory.iterdir() if p.is_dir() and p.name!="analysis" and p.name!="source_snapshot"}
    if set(folders)-set(expected):
        raise ValueError("Unexpected run folders")
    rows, records, interrupted = [], [], []
    for name, folder in sorted(folders.items()):
        case,seed,condition,repeat=expected[name]
        if not (folder/"record.json").exists() or not (folder/"record.sha256").exists():
            interrupted.append(name)
            continue
        if (folder/"record.sha256").read_text().strip()!=file_hash(folder/"record.json"):
            raise ValueError("Record hash mismatch")
        row=json.loads((folder/"record.json").read_text())
        if (row["identity_sha256"]!=manifest["sha256"] or row["case"]!=case or row["seed"]!=seed
                or row["condition"]!=condition or row["repeat"]!=repeat or row["evidence_mode"]!=identity["evidence_mode"]):
            raise ValueError("Record does not match its registered case")
        events=[json.loads(line) for line in (folder/"events.jsonl").read_text().splitlines()]
        if digest(events)!=row["events_sha256"]:
            raise ValueError("Journal hash mismatch")
        result=row["result"]
        if evaluate(result["itinerary"],case,data)!=result["evaluation"]:
            raise ValueError("Final scores do not reproduce")
        tools=Tools(data,case,lambda e:None)
        calls=[]
        pending=None
        for event in events:
            if event["kind"]=="tool_call":
                if pending is not None:raise ValueError("Missing tool result")
                calls.append(event["name"])
                pending=event
            if event["kind"]=="tool_result":
                if pending is None or pending["name"]!=event["name"]:
                    raise ValueError("Unmatched tool result")
                replay_events=[]
                tools.emit=replay_events.append
                replay=tools.call(pending["name"],pending["arguments"])
                if replay!=event["result"] or replay_events[-1]["status"]!=event.get("status"):
                    raise ValueError("Tool result differs from frozen dataset replay")
                pending=None
        if pending is not None:raise ValueError("Unfinished tool call")
        grounding=tools.grounding_errors(result["itinerary"])
        if result["grounding_errors"]!=grounding:
            raise ValueError("Final grounding does not reproduce")
        success=result["evaluation"]["constraints"]["passed"] and not grounding
        if result["success"]!=success or result["tool_calls"]!=len(calls):
            raise ValueError("Final outcome or tool count does not reproduce")
        if abs(result["RTC"]-100*len(set(calls)&set(SEARCH))/3)>1e-9:
            raise ValueError("Tool coverage does not reproduce")
        requests=[e for e in events if e["kind"]=="http_request"]
        if result["http_requests"]!=len(requests) or len(requests)>identity["http_per_record"]:
            raise ValueError("HTTP count or cap mismatch")
        evaluated=[e for e in events if e["kind"]=="round_evaluated"]
        if len(evaluated)!=len(result["rounds"]):
            raise ValueError("Repair journal and record disagree")
        for i, measured in enumerate(result["rounds"]):
            if measured["round"]!=i or evaluate(measured["plan"],case,data)!=measured["evaluation"]:
                raise ValueError("Round evaluation does not reproduce")
            if any(measured[k]!=evaluated[i][k] for k in measured):
                raise ValueError("Saved repair round differs from journal")
        attempts=sum(e["kind"]=="agent_started" and e["stage"] in ("generalist_repair","coordinator_repair") for e in events)
        if attempts!=result["repair_rounds"] or attempts>identity["max_repairs"]:
            raise ValueError("Repair round count or cap mismatch")
        if condition=="without_repair" and attempts:
            raise ValueError("Repair ablation contains a repair")
        failure_labels={v["kind"] for v in result["evaluation"]["constraints"]["violations"]}
        if grounding:failure_labels.add("grounding")
        priority=("no_output","invented_place","repeated_place","budget","distance","preference","structure","uncheckable","grounding")
        primary=next((k for k in priority if k in failure_labels),None)
        flat={"condition":condition,"case_id":case["case_id"],"seed":seed,"repeat":repeat,
              **{k:result["evaluation"]["original_metrics"][k] for k in ("APM","RBM","HBM","IFR")},
              "RTC":result["RTC"],"constraint_pass":100 if success else 0,
              "violation_count":result["evaluation"]["constraints"]["violation_count"],
              "repair_rounds":result["repair_rounds"],"tool_calls":result["tool_calls"],
              "http_requests":result["http_requests"],"system_wall_seconds":row["system_wall_seconds"],
              "primary_failure_label":primary,"all_failure_labels":sorted(failure_labels),"record":name}
        rows.append(flat)
        records.append(row)
    status="complete" if len(rows)==len(expected) and not interrupted else "incomplete"
    return {"status":status,"evidence_mode":identity["evidence_mode"],"study":identity["study"],
            "expected":len(expected),"completed":len(rows),"interrupted":interrupted,
            "missing":sorted(set(expected)-set(folders)),"identity":identity,"rows":rows,"records":records}


def export(directory, *, project=ROOT, allow_partial=False):
    directory=Path(directory)
    result=audit(directory,project)
    if result["status"]!="complete" and not allow_partial:
        raise ValueError("Partial cohort: report progress only, not comparative conclusions")
    dest=directory/"analysis"
    dest.mkdir(exist_ok=True)
    rows=result.pop("rows")
    records=result.pop("records")
    result["statistics"]={}
    if result["status"]=="complete" and result["study"]!="seed_check":
        for subset,prefix in (("original","G"),("hard","H"),("combined",None)):
            selected=[r for r in rows if prefix is None or r["case_id"].startswith(prefix)]
            if not selected:continue
            cases=sorted({r["case_id"] for r in selected})
            result["statistics"][subset]={metric:summarize(selected,metric,
                seeds=result["identity"]["seeds"],conditions=result["identity"]["conditions"],expected_cases=cases)
                for metric in ("APM","RBM","HBM","IFR","RTC","constraint_pass","violation_count","repair_rounds","tool_calls","system_wall_seconds")}
            if result["study"]=="ablation":
                for value in result["statistics"][subset].values():
                    value.pop("paired_second_minus_first",None)
    if result["study"]=="seed_check" and result["status"]=="complete":
        a,b=sorted(records,key=lambda r:r["repeat"])
        readable=all(r["result"]["itinerary"] is not None for r in (a,b))
        result["seed_check"]={"same_plan":a["result"]["itinerary"]==b["result"]["itinerary"] if readable else None,
            "both_readable":readable,
            "scope":"One case repeated twice with seed 11; matching outputs do not establish determinism for all cases."}
    result["failure_counts"]={condition:dict(Counter(r["primary_failure_label"] for r in rows
        if r["condition"]==condition and r["primary_failure_label"])) for condition in result["identity"]["conditions"]}
    result["failure_examples"]={}
    for record,flat in zip(records,rows):
        label=flat["primary_failure_label"]
        if label:
            key=flat["condition"]+"/"+label
            result["failure_examples"].setdefault(key,{"record":flat["record"],"case":record["case"],
                "plan":record["result"]["itinerary"],"error":record["result"]["error"],
                "violations":record["result"]["evaluation"]["constraints"]["violations"]})
    result["failure_note"]="Exclusive labels use the registered priority order; all labels are retained in the CSV. Labels describe outcomes, not proven causes."
    write_json(dest/"SUMMARY.json",result)
    with (dest/"RESULTS.csv").open("w",newline="") as stream:
        fields=list(rows[0]) if rows else ["condition","case_id","seed"]
        writer=csv.DictWriter(stream,fieldnames=fields)
        writer.writeheader()
        writer.writerows({**row,"all_failure_labels":";".join(row["all_failure_labels"])} for row in rows)
    report=["# Revised experiment results","",f"Status: **{result['status']}**. Records: {result['completed']}/{result['expected']}. Evidence: {result['evidence_mode']}.",""]
    if result["evidence_mode"]!="live":
        report.append("These records test the software only. They are not model-performance results.\n")
    if result["status"]=="complete" and result["statistics"]:
        for subset,stats in result["statistics"].items():
            report += [f"## {subset.capitalize()} cases","","| Metric | Condition | Mean | SD of seed means | Pass on all three runs |","|---|---|---:|---:|---:|"]
            for metric,s in stats.items():
                for condition,c in s["conditions"].items():
                    pass3=f"{100*c['pass3']:.1f}%" if c.get("pass3") is not None else "—"
                    report.append(f"| {metric} | {condition} | {c['mean']:.3f} | {c['sd_across_seed_means']:.3f} | {pass3} |")
            report += ["","Paired differences use one average per case, keeping its three seeds together. "
                       "The JSON report includes 95% bootstrap intervals and paired sign-flip tests. "
                       "Secondary comparisons are exploratory; a small numerical lead is not automatically evidence of improvement.",""]
    report += ["## Failure analysis","","Labels: no output; unknown dataset place; repeated activity; budget; distance; interest quota; structure; missing information; selection not found in searched candidates. "
               "All failed records remain in the denominator. A missing plan receives a recorded no-output violation; it is not treated as a plan with zero travel violations.","",
               "See SUMMARY.json for counts and real examples. Component-removal results are needed before linking a common failure to a particular design choice."]
    (dest/"REPORT.md").write_text("\n".join(report)+"\n")
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("directory",type=Path)
    p.add_argument("--allow-partial",action="store_true")
    args=p.parse_args()
    r=export(args.directory,allow_partial=args.allow_partial)
    print(json.dumps({k:r[k] for k in ("status","completed","expected","evidence_mode")}))


if __name__=="__main__":main()
