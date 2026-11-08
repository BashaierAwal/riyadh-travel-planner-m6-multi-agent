"""Fixed-denominator scoring against the frozen datasets."""

import csv
import json
from pathlib import Path

from . import SCORER_VERSION

REQUIRED_TOOLS = frozenset({"find_activities", "find_restaurants", "find_hotels"})


def load_datasets(directory):
    result = {}
    for name in ("activities", "restaurants", "hotels"):
        with (Path(directory) / f"{name}.csv").open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        ids = [row["place_id"] for row in rows]
        if any(not pid for pid in ids) or len(ids) != len(set(ids)):
            raise ValueError(f"Missing or duplicate {name} identifiers")
        result[name] = dict(zip(ids, rows))
    return result


def validate_case(case, datasets):
    duration = case.get("trip_duration")
    if type(duration) is not int or duration < 1:
        raise ValueError("trip_duration must be a positive integer")
    interests = case.get("interests")
    allowed = {r["interest_group"] for r in datasets["activities"].values()}
    if (not isinstance(interests, list) or not interests
            or any(not isinstance(i, str) or i not in allowed for i in interests)):
        raise ValueError("interests must contain known interest groups")
    if case.get("budget_level") not in ("Low", "Medium", "High"):
        raise ValueError("Unknown budget level")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_itinerary(value):
    if isinstance(value, str):
        try:
            value = json.loads(value, object_pairs_hook=_unique_object,
                               parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))
        except (ValueError, TypeError, RecursionError) as error:
            return None, [f"Invalid JSON: {type(error).__name__}"]
    if not isinstance(value, dict):
        return None, ["Itinerary must be an object"]
    return value, []


def structural_errors(itinerary, duration, datasets):
    errors = []
    hotel = itinerary.get("hotel_id")
    if not isinstance(hotel, str) or hotel not in datasets["hotels"]:
        errors.append("Invalid hotel ID")
    days = itinerary.get("days")
    if not isinstance(days, list):
        return errors + ["Days must be a list"]
    if len(days) != duration:
        errors.append("Incorrect number of days")
    seen = set()
    for index, day in enumerate(days, 1):
        if not isinstance(day, dict):
            errors.append(f"Day {index}: invalid structure")
            continue
        if type(day.get("day")) is not int or day["day"] != index:
            errors.append(f"Day {index}: incorrect day number")
        for field, dataset in (("activities", "activities"), ("restaurants", "restaurants")):
            entries = day.get(field)
            if not isinstance(entries, list):
                errors.append(f"Day {index}: {field} must be a list")
                continue
            if len(entries) != 2:
                errors.append(f"Day {index}: must have 2 {field}")
            for pid in entries:
                if not isinstance(pid, str):
                    errors.append(f"Day {index}: invalid {field} ID type")
                    continue
                if pid not in datasets[dataset]:
                    errors.append(f"Day {index}: unknown {field} ID")
                if field == "activities":
                    if pid in seen:
                        errors.append("Repeated activities found")
                    seen.add(pid)
    return errors


def tool_coverage(tool_calls):
    """Coverage of required tool names; does not establish call correctness."""
    if not isinstance(tool_calls, list):
        return 0.0
    names = {name for name in tool_calls if isinstance(name, str)}
    return round(100 * len(names & REQUIRED_TOOLS) / len(REQUIRED_TOOLS), 2)


def score_itinerary(value, case, datasets):
    validate_case(case, datasets)
    itinerary, parse_errors = parse_itinerary(value)
    result = {"scorer_version": SCORER_VERSION, "APM": 0.0, "RBM": 0.0,
              "HBM": 0.0, "IFR": 0.0, "feasible": False,
              "validation_errors": parse_errors}
    if itinerary is None:
        return result
    errors = structural_errors(itinerary, case["trip_duration"], datasets)
    days = itinerary.get("days")
    days = days if isinstance(days, list) else []
    matching = {"activities": 0, "restaurants": 0}
    seen = set()
    for day in days[:case["trip_duration"]]:
        if not isinstance(day, dict):
            continue
        for field in matching:
            values = day.get(field)
            if not isinstance(values, list):
                continue
            for pid in values[:2]:
                if not isinstance(pid, str):
                    continue
                if field == "activities":
                    if pid in seen:
                        continue
                    seen.add(pid)
                row = datasets[field].get(pid)
                if row is None:
                    continue
                match = (row["interest_group"] in case["interests"] if field == "activities"
                         else row["budget_level"] == case["budget_level"])
                matching[field] += bool(match)
    hotel = itinerary.get("hotel_id")
    hotel_row = datasets["hotels"].get(hotel) if isinstance(hotel, str) else None
    slots = 2 * case["trip_duration"]
    result.update(APM=round(100 * matching["activities"] / slots, 2),
                  RBM=round(100 * matching["restaurants"] / slots, 2),
                  HBM=100.0 if hotel_row and hotel_row["budget_level"] == case["budget_level"] else 0.0,
                  IFR=0.0 if errors else 100.0, feasible=not errors, validation_errors=errors)
    return result
