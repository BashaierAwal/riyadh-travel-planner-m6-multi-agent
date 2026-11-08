"""Price-equivalent of OBSERVED usage; never an actual billing claim or API call."""

import json
from pathlib import Path
from statistics import mean, stdev
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def observed_equivalent(trace, pricing):
    amount, usable, fallbacks, response_count = 0.0, 0, 0, 0
    for event in trace:
        if event["kind"] != "http_response":
            continue
        response_count += 1
        body = event.get("body")
        usage = body.get("usageMetadata") if isinstance(body, dict) else None
        if not isinstance(usage, dict):
            continue
        prompt = usage.get("promptTokenCount")
        if type(prompt) is not int or prompt < 0:
            continue
        total = usage.get("totalTokenCount")
        if type(total) is int and total >= prompt:
            # Official definition: total = prompt + thoughts + response candidates.
            output = total - prompt
        else:
            candidate, thought = usage.get("candidatesTokenCount"), usage.get("thoughtsTokenCount", 0)
            if type(candidate) is not int or candidate < 0 or type(thought) is not int or thought < 0:
                continue
            output = candidate + thought
            fallbacks += 1
        amount += (prompt * pricing["standard_input_USD_per_1M_tokens"]
                   + output * pricing["standard_output_USD_per_1M_tokens_including_thinking"]) / 1_000_000
        usable += 1
    return {"observed_uncached_list_price_equivalent_usd": amount if usable else None,
            "http_responses": response_count, "responses_with_priced_usage": usable,
            "responses_without_priced_usage": response_count - usable,
            "fallback_candidate_thought_sums": fallbacks, "actual_cost_usd": None}


def summarize(directory):
    from m6planner.analysis import load_records
    identity, records = load_records(directory)  # refuses partial cohorts
    pricing = json.loads((ROOT / "reports/M6_Pricing_Reference.json").read_text())
    if identity["policy"]["model"] != pricing["model"]:
        raise ValueError("Price reference is for a different model")
    result = {"price_reference": pricing, "actual_billing_established": False,
              "scope": "Standard uncached list-price equivalent of observable tokens across all attempts; not a bill, not an upper bound, and not a zero-cost claim. Cached discounts/free tier are not applied.",
              "conditions": {}, "per_record": []}
    for condition in ("baseline", "treatment"):
        group = []
        for record in records:
            if record["metadata"]["condition"] != condition:
                continue
            row = {"condition": condition, "case_id": record["case_id"], "seed": record["seed"],
                   **observed_equivalent(record["generation_result"]["trace"], pricing)}
            result["per_record"].append(row)
            group.append(row)
        values = [r["observed_uncached_list_price_equivalent_usd"] for r in group
                  if r["observed_uncached_list_price_equivalent_usd"] is not None]
        result["conditions"][condition] = {"records": len(group), "records_with_observed_estimate": len(values),
            "sum_observed_uncached_list_price_equivalent_usd": sum(values) if values else None,
            "mean_observed_equivalent_per_record_usd": mean(values) if values else None,
            "sample_sd_observed_equivalent_per_record_usd": stdev(values) if len(values) > 1 else None,
            "responses_with_priced_usage": sum(r["responses_with_priced_usage"] for r in group),
            "responses_without_priced_usage": sum(r["responses_without_priced_usage"] for r in group),
            "actual_cost_usd": None}
    return result


if __name__ == "__main__":
    directory = Path(sys.argv[1])
    output = directory / "analysis/M6_Cost_Estimates.json"
    payload = json.dumps(summarize(directory), ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    with output.open("x", encoding="utf-8") as stream:
        stream.write(payload)
    print(output)
