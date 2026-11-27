"""Replay frozen evidence with a narrow tolerance for calculated route kilometres."""

import argparse
from contextlib import contextmanager
import json
import math
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from revision import verify
from revision.run import digest, file_hash


class RouteComparison:
    tolerance_km = 1e-12

    def __init__(self):
        self.rounding_comparisons = 0
        self.maximum_difference_km = 0.0

    def equal(self, left, right, path=()):
        if isinstance(left, dict) and isinstance(right, dict):
            return left.keys() == right.keys() and all(
                self.equal(left[key], right[key], path+(key,)) for key in left)
        if isinstance(left, list) and isinstance(right, list):
            return len(left) == len(right) and all(
                self.equal(a, b, path+(index,)) for index, (a, b) in enumerate(zip(left, right)))
        route_km = (len(path) >= 3 and path[-3] == "routes"
                    and type(path[-2]) is int and path[-1] == "km")
        if route_km and type(left) is float and type(right) is float:
            if not (math.isfinite(left) and math.isfinite(right)):
                return False
            delta = abs(left-right)
            if delta > self.tolerance_km:
                return False
            if delta:
                self.rounding_comparisons += 1
                self.maximum_difference_km = max(self.maximum_difference_km, delta)
            return True
        return type(left) is type(right) and left == right


@contextmanager
def route_replay():
    comparison = RouteComparison()
    original_evaluate, original_tools = verify.evaluate, verify.Tools

    class ComparedDict(dict):
        def __eq__(self, other):
            return comparison.equal(self, other)

        def __ne__(self, other):
            return not self.__eq__(other)

    def replay_evaluation(*args, **kwargs):
        return ComparedDict(original_evaluate(*args, **kwargs))

    class ReplayTools(original_tools):
        def call(self, *args, **kwargs):
            value = super().call(*args, **kwargs)
            return ComparedDict(value) if isinstance(value, dict) else value

    # Apply the comparison only inside this independent audit process. The
    # frozen generation files and the raw saved records are never rewritten.
    verify.evaluate, verify.Tools = replay_evaluation, ReplayTools
    try:
        yield comparison
    finally:
        verify.evaluate, verify.Tools = original_evaluate, original_tools


def execution_priority(directory, identity):
    path = Path(directory)/"priority_execution_v1.json"
    if not path.exists():
        return None
    receipt = json.loads(path.read_text())
    policy = receipt["policy"]
    expected_cases = json.loads((PROJECT/"revision/cases/all.json").read_text())
    if identity["cases"] != expected_cases or policy["identity_sha256"] != digest(identity):
        raise ValueError("Priority registration differs from the registered case inputs")
    if identity["study"] not in ("main", "ablation", "second_model", "strong_coordinator"):
        raise ValueError("Unsupported priority study")
    finish = policy["finish_started_original_cases"]
    known = {case["case_id"] for case in identity["cases"]}
    if len(set(finish)) != len(finish) or any(cid not in known or not cid.startswith("G") for cid in finish):
        raise ValueError("Invalid case-priority registration")
    queue = []
    for index, (case, seed) in enumerate((c, s) for c in identity["cases"] for s in identity["seeds"]):
        conditions = identity["conditions"] if index%2 == 0 else list(reversed(identity["conditions"]))
        queue.extend({"case_id": case["case_id"], "seed": seed, "condition": condition, "repeat": 1}
                     for condition in conditions)
    queue.sort(key=lambda item: 0 if item["case_id"] in finish else 1 if item["case_id"].startswith("H") else 2)
    if digest(queue) != policy["queue_sha256"]:
        raise ValueError("Registered priority queue differs")
    snapshot = "source_snapshot/execution/Run_Review_Priority.py"
    if policy["worker_snapshot"] != snapshot or file_hash(Path(directory)/snapshot) != policy["worker_sha256"]:
        raise ValueError("Priority worker snapshot hash differs")
    if (policy.get("all_cases_preserved") is not True or policy.get("completed_records_not_retried") is not True
            or receipt.get("hard_model_records_before_registration") != 0):
        raise ValueError("Invalid execution-priority safeguards")
    return {"registered_at_utc": receipt["registered_at_utc"], "worker_sha256": policy["worker_sha256"],
            "queue_sha256": policy["queue_sha256"], "finish_started_original_cases": finish}


def receipt_for(result, comparison, priority=None):
    return {"status": result["status"], "evidence_mode": result["evidence_mode"], "completed": result["completed"],
               "expected": result["expected"], "route_tolerance_km": comparison.tolerance_km,
               "rounding_comparisons": comparison.rounding_comparisons,
               "maximum_difference_km": comparison.maximum_difference_km,
               "execution_priority": priority,
               "raw_integrity_checks": "Exact manifest, source, dataset, record and journal hashes",
               "other_replay_checks": "Exact IDs, tool-result ordering, scores, rule decisions and non-route values",
               "scope": "Only derived routes[index].km numbers allow the stated absolute tolerance. Generation rules and scores are unchanged.",
               "verifier_sha256": file_hash(Path(__file__))}


def audit(directory, project=PROJECT):
    with route_replay() as comparison:
        result = verify.audit(directory, project)
    priority = execution_priority(directory, result["identity"])
    result["numeric_replay"] = receipt_for(result, comparison, priority)
    return result


def export(directory, *, allow_partial=False):
    identity = json.loads((Path(directory)/"manifest.json").read_text())["identity"]
    priority = execution_priority(directory, identity)
    with route_replay() as comparison:
        result = verify.export(directory, project=PROJECT, allow_partial=allow_partial)
    receipt = receipt_for(result, comparison, priority)
    destination = Path(directory)/"analysis"/"REPLAY_MODE.json"
    destination.write_text(json.dumps(receipt, indent=2)+"\n")
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args()
    print(json.dumps(export(args.directory, allow_partial=args.allow_partial)))


if __name__ == "__main__":
    main()
