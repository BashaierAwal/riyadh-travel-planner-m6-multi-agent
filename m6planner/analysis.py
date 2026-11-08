"""Offline complete-cohort comparison. Missing/failed runs cannot disappear."""

import csv
import io
import json
from pathlib import Path
from statistics import mean, stdev

from m5eval.evaluate import ROOT, sha256
from m5eval.experiment import fingerprint, golden_cases
from m5eval.scoring import load_datasets, score_itinerary, tool_coverage
from m5eval.statistics import METRICS, summarize
from m5eval.generation import requested_tool_names
from .workflow import usage_totals


def describe(values):
    return {"n": len(values), "mean": mean(values) if values else None,
            "sample_sd": stdev(values) if len(values) > 1 else None}


def load_records(directory):
    root = Path(directory).resolve()
    manifest = json.loads((root / "manifest.json").read_text())
    identity = manifest["identity"]
    if fingerprint(identity) != manifest["identity_sha256"]:
        raise ValueError("Manifest checksum mismatch")
    approved = {c["case_id"]: c for c in golden_cases()}
    if any(c != approved.get(c["case_id"]) for c in identity["cases"]):
        raise ValueError("Golden inputs changed")
    for name, digest in identity["dataset_sha256"].items():
        if sha256(ROOT / "data" / f"{name}.csv") != digest:
            raise ValueError("Dataset hash mismatch")
    datasets = load_datasets(ROOT / "data")
    expected = {(k, c["case_id"], s) for k in ("baseline", "treatment") for c in identity["cases"] for s in identity["seeds"]}
    if len(expected) != len(identity["cases"]) * len(identity["seeds"]) * 2:
        raise ValueError("Duplicate expected inputs")
    folders = {p.name for p in root.iterdir() if p.is_dir() and p.name != "analysis"}
    expected_folders = {f"{k}_{c}_seed{s}" for k, c, s in expected}
    if folders != expected_folders:
        raise ValueError("Incomplete or unexpected cohort folders; no partial primary comparison")
    records = []
    for condition, case_id, seed in sorted(expected):
        folder = root / f"{condition}_{case_id}_seed{seed}"
        path = folder / "record.json"
        if not path.is_file() or not (folder / "record.sha256").is_file() or sha256(path) != (folder / "record.sha256").read_text().strip():
            raise ValueError("Missing or altered saved record")
        record = json.loads(path.read_text())
        generation, meta = record["generation_result"], record["metadata"]
        if (record["user_input"] != approved[case_id] or record["seed"] != seed or type(record["seed"]) is not int
                or record["case_id"] != case_id or record["experiment_version"] != identity["version"]
                or meta["condition"] != condition or meta["experiment_identity_sha256"] != manifest["identity_sha256"]
                or meta["evidence_mode"] != identity["evidence_mode"] or generation["condition"] != condition):
            raise ValueError("Record identity mismatch")
        trace = [json.loads(line) for line in (folder / "events.jsonl").read_text().splitlines()]
        if trace != generation["trace"] or [e["event_number"] for e in trace] != list(range(1, len(trace)+1)):
            raise ValueError("Journal linkage mismatch")
        if generation["generation_success"] != (generation["itinerary"] is not None) or record["generation_success"] != generation["generation_success"]:
            raise ValueError("Success/output inconsistency")
        if record["evaluation"] != score_itinerary(generation["itinerary"], record["user_input"], datasets):
            raise ValueError("Score mismatch")
        last_attempt = len(generation["attempts"])
        calls = requested_tool_names(trace, attempt=last_attempt)
        if generation["tool_calls"] != calls or record["RTC"] != tool_coverage(calls):
            raise ValueError("Final-attempt RTC mismatch")
        if generation["usage"] != usage_totals(trace):
            raise ValueError("Usage mismatch")
        if generation["http_requests"] != sum(e["kind"] == "http_request" for e in trace):
            raise ValueError("HTTP count mismatch")
        records.append(record)
    return identity, records


def comparison(directory):
    identity, records = load_records(directory)
    result = {"evidence_mode": identity["evidence_mode"], "study_kind": identity["study_kind"],
              "is_formal_experimental_evidence": identity["evidence_mode"] == "live" and identity["study_kind"] == "formal"
              and identity["cases"] == golden_cases() and identity["seeds"] == [11, 22, 33],
              "generation_policy": identity["generation_policy"], "conditions": {},
              "interpretation": "Mock/pilot results are validation only. Architecture benefit is not assumed. IFR is structural only."}
    flat_rows = []
    for condition in ("baseline", "treatment"):
        group = [r for r in records if r["metadata"]["condition"] == condition]
        rows = [{**r["user_input"], "seed": r["seed"], **{m: r["evaluation"][m] for m in METRICS if m != "RTC"},
                 "tool_calls": r["generation_result"]["tool_calls"]} for r in group]
        metrics = summarize(rows, identity["cases"], identity["seeds"]) if len(identity["cases"]) > 1 and len(identity["seeds"]) > 1 else {
            m: describe([r["RTC"] if m == "RTC" else r["evaluation"][m] for r in group]) for m in METRICS}
        timings = {k: describe([r["generation_result"]["timing"][k] for r in group]) for k in
                   ("system_wall_ms", "processing_ms", "retry_wait_ms", "pacing_wait_ms")}
        failure_counts = {}
        for r in group:
            g = r["generation_result"]
            error = g.get("generation_error")
            if error:
                name = ("final_parse" if error["stage"] in ("baseline", "coordinator_final") else "coordination_message") if error["type"] == "MessageError" else error["type"]
                failure_counts[name] = failure_counts.get(name, 0) + 1
            elif r["evaluation"]["IFR"] != 100:
                failure_counts["structural_output"] = failure_counts.get("structural_output", 0) + 1
            flat_rows.append({"condition": condition, "case_id": r["case_id"], "seed": r["seed"],
                              **{m: r["RTC"] if m == "RTC" else r["evaluation"][m] for m in METRICS},
                              "generation_success": r["generation_success"], "failure_type": name if error else ("structural_output" if r["evaluation"]["IFR"] != 100 else ""),
                              **{k: g["timing"][k] for k in timings}, "http_requests": g["http_requests"],
                              "observed_prompt_tokens": g["usage"]["observed_tokens"]["promptTokenCount"],
                              "observed_candidate_tokens": g["usage"]["observed_tokens"]["candidatesTokenCount"],
                              "actual_cost_usd": None, "estimated_cost_usd": None, "evidence_mode": identity["evidence_mode"]})
        observed = {}
        for name in group[0]["generation_result"]["usage"]["observed_tokens"]:
            values = [r["generation_result"]["usage"]["observed_tokens"][name] for r in group]
            known = [v for v in values if v is not None]
            observed[name] = {"sum_observed": sum(known) if known else None, "records_with_observation": len(known)}
        result["conditions"][condition] = {"records": len(group), "parsed_outputs": sum(r["generation_success"] for r in group),
                                           "structurally_valid": sum(r["evaluation"]["IFR"] == 100 for r in group),
                                           "metrics": metrics, "latency": timings, "observed_usage": observed,
                                           "http_requests": sum(r["generation_result"]["http_requests"] for r in group),
                                           "actual_cost_usd": None, "estimated_cost_usd": None, "failure_counts": failure_counts}
    by_key = {(r["metadata"]["condition"], r["case_id"], r["seed"]): r for r in records}
    result["paired_treatment_minus_baseline"] = {}
    for metric in METRICS:
        diffs = []
        for c in identity["cases"]:
            for s in identity["seeds"]:
                a, b = (by_key[(k, c["case_id"], s)] for k in ("baseline", "treatment"))
                diffs.append(b["RTC"] - a["RTC"] if metric == "RTC" else b["evaluation"][metric] - a["evaluation"][metric])
        result["paired_treatment_minus_baseline"][metric] = describe(diffs)
    return result, flat_rows


def export_comparison(directory):
    result, rows = comparison(directory)
    destination = Path(directory) / "analysis"
    destination.mkdir(exist_ok=True)
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    payloads = {"M6_Results.csv": stream.getvalue(), "M6_Comparison.json": json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"}
    for name, payload in payloads.items():
        path = destination / name
        if path.exists():
            if path.read_text() != payload:
                # CSV universal-newline normalization is harmless; all data must still agree.
                if path.read_text() != payload.replace("\r\n", "\n"):
                    raise ValueError("Existing derived report differs; preserve and inspect it")
        else:
            with path.open("x", newline="", encoding="utf-8") as f:
                f.write(payload)
    return result
