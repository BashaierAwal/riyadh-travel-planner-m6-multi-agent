"""Dated per-record list-price estimates from saved HTTP response usage."""

import argparse
import json
from pathlib import Path

from .run import ROOT, file_hash, write_json


def estimate_events(events, prices):
    requests={e["number"]:e for e in events if e["kind"]=="http_request"}
    details=[]
    for e in events:
        if e["kind"]!="http_response":continue
        request=requests.get(e["number"],{})
        model=request.get("model")
        rate=prices["models"].get(model)
        body=e.get("body")
        usage=body.get("usageMetadata",{}) if isinstance(body,dict) else {}
        inp,cand,thought,total=(usage.get(k) for k in ("promptTokenCount","candidatesTokenCount","thoughtsTokenCount","totalTokenCount"))
        usable=rate is not None and all(type(v) is int and v>=0 for v in (inp,cand,total))
        inferred=False
        if thought is None and usable and total==inp+cand:
            thought=0
            inferred=True
        usable=usable and type(thought) is int and thought>=0 and total==inp+cand+thought
        cost=(inp*rate["input_per_million"]+(cand+thought)*rate["output_per_million_including_thinking"])/1e6 if usable else None
        details.append({"request":e["number"],"model":model,"status":e["status"],"prompt_tokens":inp,
                        "candidate_tokens":cand,"thinking_tokens":thought,"total_tokens":total,
                        "zero_thinking_inferred_from_total":inferred,"estimated_usd":cost})
    known=[d["estimated_usd"] for d in details if d["estimated_usd"] is not None]
    complete=len(details)==len(requests) and len(known)==len(requests)
    return {"estimated_cost_usd":sum(known) if complete else None,
            "observed_usage_subtotal_usd":sum(known) if known else None,
            "complete_usage_and_price_coverage":complete,"http_requests":len(requests),
            "requests_with_estimate":len(known),"details":details,"actual_cost_usd":None,
            "basis":prices["basis"],"price_checked_date":prices["checked_date"],"price_source":prices["source"]}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("directory",type=Path)
    args=p.parse_args()
    prices=json.loads((ROOT/"revision/PRICING.json").read_text())
    records={}
    for folder in sorted(args.directory.iterdir()):
        if not folder.is_dir() or not (folder/"record.json").exists():continue
        path=folder/"record.json"
        if not (folder/"record.sha256").exists() or (folder/"record.sha256").read_text().strip()!=file_hash(path):
            raise ValueError("Run record checksum mismatch")
        events=[json.loads(line) for line in (folder/"events.jsonl").read_text().splitlines()]
        records[folder.name]=estimate_events(events,prices)
    dest=args.directory/"analysis"
    dest.mkdir(exist_ok=True)
    write_json(dest/"COST_ESTIMATES.json",{"scope":"Per-case list-price equivalents, separate from billing", "records":records})
    print(f"Estimated usage for {len(records)} saved records")


if __name__=="__main__":main()
