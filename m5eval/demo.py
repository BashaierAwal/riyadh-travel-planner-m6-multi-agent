"""Run an explicitly labelled offline fixture through the complete storage/scoring path."""

import argparse
import json
from pathlib import Path
import uuid

from .evaluate import ROOT
from .experiment import Experiment, RunSettings, golden_cases


class FixtureBackend:
    mode = "fixture"

    def __init__(self, case, *, text_override=None):
        self.case, self.text_override = case, text_override
        self.calls = 0

    def send(self, *, prompt, tools, seed, model, temperature, maximum_remote_calls, emit):
        self.calls += 1
        by_name = {tool.__name__: tool for tool in tools}
        activities = by_name["find_activities"](self.case["interests"])
        restaurants = by_name["find_restaurants"](self.case["budget_level"])
        hotels = by_name["find_hotels"](self.case["budget_level"])
        activity_ids = [r["place_id"] for r in activities]
        restaurant_ids = [r["place_id"] for r in restaurants]
        itinerary = {"hotel_id": hotels[0]["place_id"] if hotels else None, "days": []}
        for day in range(self.case["trip_duration"]):
            itinerary["days"].append({"day": day+1,
                "activities": [activity_ids[(2*day+i) % len(activity_ids)] for i in range(2)] if activity_ids else [],
                "restaurants": [restaurant_ids[(2*day+i) % len(restaurant_ids)] for i in range(2)] if restaurant_ids else []})
        return {"text": self.text_override if self.text_override is not None else json.dumps(itinerary),
                "response": {"fixture_only": True}, "history": None}

    def close(self):
        pass


def run_demo(destination):
    case = golden_cases()[0]
    backend = FixtureBackend(case)
    experiment = Experiment(destination, "fixture-" + uuid.uuid4().hex[:12], [case], [11], backend,
                            settings=RunSettings(max_attempts=1))
    record = experiment.run_case(case["case_id"], 11)
    return {"evidence_mode": "fixture", "live_model_calls": 0, "record_directory": str(experiment.root),
            "scores": record["evaluation"], "status": "Local fixture completed; Gemini availability is untested."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "runs")
    args = parser.parse_args()
    print(json.dumps(run_demo(args.output), indent=2))


if __name__ == "__main__":
    main()
