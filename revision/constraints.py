"""Dataset checks for distance, hotel cost and competing interests.

Distances are great-circle distances, not road distances or journey times.
Each daily route is hotel, activity 1, restaurant 1, activity 2, restaurant 2,
hotel. Missing coordinates make a route uncheckable and prevent a pass.
"""

from collections import Counter
from math import asin, cos, isfinite, radians, sin, sqrt

from m5eval.scoring import parse_itinerary, score_itinerary, structural_errors, validate_case


def number(value):
    try:
        n = float(value)
        return n if isfinite(n) else None
    except (TypeError, ValueError):
        return None


def coordinates(row):
    lat = number(row.get("latitude", row.get("lat")))
    lon = number(row.get("longitude", row.get("lng")))
    if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return lat, lon


def distance(a, b):
    """Great-circle kilometres on the IUGG mean-radius sphere."""
    lat1, lon1, lat2, lon2 = map(radians, (*a, *b))
    h = sin((lat2-lat1)/2)**2 + cos(lat1)*cos(lat2)*sin((lon2-lon1)/2)**2
    return 6371.0088 * 2 * asin(sqrt(min(1, max(0, h))))


def validate_constraints(case, datasets):
    validate_case(case, datasets)
    rules = case.get("constraints")
    if rules is None:
        return
    if not isinstance(rules, dict) or set(rules) != {
            "max_km_per_day", "hotel_cap_sar", "nights", "minimum_interest_slots"}:
        raise ValueError("Hard cases need all four registered constraints")
    for name in ("max_km_per_day", "hotel_cap_sar"):
        if type(rules[name]) not in (int, float) or number(rules[name]) is None or rules[name] <= 0:
            raise ValueError("Constraint limits must be positive finite numbers")
    if type(rules["nights"]) is not int or rules["nights"] != max(1, case["trip_duration"]-1):
        raise ValueError("Nights are explicit: max(1, trip duration minus one)")
    quotas = rules["minimum_interest_slots"]
    if (not isinstance(quotas, dict) or set(quotas) != set(case["interests"])
            or len(quotas) != 2 or any(type(q) is not int or q < 1 for q in quotas.values())
            or sum(quotas.values()) > 2*case["trip_duration"]):
        raise ValueError("Two distinct interests need feasible positive slot quotas")


def check_plan(plan, case, datasets):
    """Return individual broken rules; never repair or change a submitted plan."""
    validate_constraints(case, datasets)
    itinerary, parse_errors = parse_itinerary(plan)
    violations = []

    def add(kind, rule, detail):
        violations.append({"kind": kind, "rule": rule, "detail": detail})

    if itinerary is None:
        add("no_output", "readable_plan", "; ".join(parse_errors))
        return {"violations": violations, "violation_count": 1, "passed": False,
                "checkable": False, "routes": [], "hotel_cost_sar": None}
    errors = structural_errors(itinerary, case["trip_duration"], datasets)
    for index, error in enumerate(errors):
        kind = "repeated_place" if "Repeated" in error else (
            "invented_place" if "unknown" in error or "Invalid hotel" in error else "structure")
        add(kind, "structure_"+error, error)
    rules = case.get("constraints")
    if rules is None:
        return {"violations": violations, "violation_count": len(violations),
                "passed": not violations, "checkable": not errors,
                "routes": [], "hotel_cost_sar": None}
    hotel = datasets["hotels"].get(itinerary.get("hotel_id")) if isinstance(itinerary.get("hotel_id"), str) else None
    cost = None
    if hotel:
        nightly = number(hotel.get("median_price"))
        if nightly is None or nightly < 0:
            add("uncheckable", "hotel_cost", "Hotel median price is missing or invalid")
        else:
            cost = nightly * rules["nights"]
            if cost > rules["hotel_cap_sar"] + 1e-9:
                add("budget", "hotel_cost", f"{cost:.3f} SAR exceeds {rules['hotel_cap_sar']} SAR")
        if hotel["budget_level"] != case["budget_level"]:
            add("budget", "hotel_category", "Hotel category does not match the requested budget")
    days = itinerary.get("days")
    days = days if isinstance(days, list) else []
    seen, interest_counts, routes = set(), Counter(), []
    for index, day in enumerate(days[:case["trip_duration"]], 1):
        if not isinstance(day, dict):
            continue
        acts, rests = day.get("activities"), day.get("restaurants")
        if not isinstance(acts, list) or not isinstance(rests, list):
            continue
        for pid in acts[:2]:
            row = datasets["activities"].get(pid) if isinstance(pid, str) else None
            if row and pid not in seen:
                interest_counts[row["interest_group"]] += 1
                seen.add(pid)
        for slot, pid in enumerate(rests[:2], 1):
            row = datasets["restaurants"].get(pid) if isinstance(pid, str) else None
            if row and row["budget_level"] != case["budget_level"]:
                add("budget", f"restaurant_{index}_{slot}", "Restaurant budget category does not match")
        if len(acts) != 2 or len(rests) != 2:
            add("uncheckable", f"route_{index}", "Daily route requires two activities and two restaurants")
            continue
        rows = [hotel]
        for group, pid in (("activities", acts[0]), ("restaurants", rests[0]),
                           ("activities", acts[1]), ("restaurants", rests[1])):
            rows.append(datasets[group].get(pid) if isinstance(pid, str) else None)
        rows.append(hotel)
        points = [coordinates(row) if row else None for row in rows]
        if any(p is None for p in points):
            add("uncheckable", f"route_{index}", "A route place or coordinate is missing")
            routes.append({"day": index, "km": None})
        else:
            km = sum(distance(a, b) for a, b in zip(points, points[1:]))
            routes.append({"day": index, "km": km})
            if km > rules["max_km_per_day"] + 1e-9:
                add("distance", f"route_{index}", f"{km:.3f} km exceeds {rules['max_km_per_day']} km")
    for interest, quota in rules["minimum_interest_slots"].items():
        if interest_counts[interest] < quota:
            add("preference", f"interest_{interest}", f"{interest_counts[interest]} unique slots; {quota} required")
    return {"violations": violations, "violation_count": len(violations), "passed": not violations,
            "checkable": not any(v["kind"] in ("uncheckable", "no_output", "invented_place", "structure") for v in violations),
            "routes": routes, "hotel_cost_sar": cost, "interest_slots": dict(interest_counts)}


def evaluate(plan, case, datasets):
    return {"original_metrics": score_itinerary(plan, case, datasets),
            "constraints": check_plan(plan, case, datasets)}
