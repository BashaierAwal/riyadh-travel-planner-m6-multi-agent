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
from revision.run import file_hash


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


def receipt_for(result, comparison):
    return {"status": result["status"], "evidence_mode": result["evidence_mode"], "completed": result["completed"],
               "expected": result["expected"], "route_tolerance_km": comparison.tolerance_km,
               "rounding_comparisons": comparison.rounding_comparisons,
               "maximum_difference_km": comparison.maximum_difference_km,
               "raw_integrity_checks": "Exact manifest, source, dataset, record and journal hashes",
               "other_replay_checks": "Exact IDs, tool-result ordering, scores, rule decisions and non-route values",
               "scope": "Only derived routes[index].km numbers allow the stated absolute tolerance. Generation rules and scores are unchanged.",
               "verifier_sha256": file_hash(Path(__file__))}


def audit(directory, project=PROJECT):
    with route_replay() as comparison:
        result = verify.audit(directory, project)
    result["numeric_replay"] = receipt_for(result, comparison)
    return result


def export(directory, *, allow_partial=False):
    with route_replay() as comparison:
        result = verify.export(directory, project=PROJECT, allow_partial=allow_partial)
    receipt = receipt_for(result, comparison)
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
