"""Create a fixed, independently checkable extension without calling any model."""

import itertools
import json
from pathlib import Path

from m5eval.scoring import load_datasets
from .constraints import check_plan, coordinates, distance, number

ROOT = Path(__file__).resolve().parents[1]


def witness(case, data):
    """Construct a feasible route to rule out impossible benchmark requests.

    This is case-design evidence only. It is never sent to the planning models.
    """
    rules = case["constraints"]
    hotels = [r for r in data["hotels"].values() if r["budget_level"] == case["budget_level"]
              and coordinates(r) and number(r["median_price"]) is not None
              and 0 <= float(r["median_price"])*rules["nights"] <= rules["hotel_cap_sar"]]
    hotels.sort(key=lambda r: r["place_id"])
    rests = [r for r in data["restaurants"].values() if r["budget_level"] == case["budget_level"] and coordinates(r)]
    groups = [[r for r in data["activities"].values() if r["interest_group"] == interest and coordinates(r)]
              for interest in case["interests"]]
    for hotel in hotels:
        hp = coordinates(hotel)
        nearby_rests = sorted(rests, key=lambda r: (distance(hp, coordinates(r)), r["place_id"]))[:60]
        ranked = [sorted(group, key=lambda r: (distance(hp, coordinates(r)), r["place_id"])) for group in groups]
        used, days = set(), []
        for day in range(1, case["trip_duration"]+1):
            choices = [[r for r in group if r["place_id"] not in used][:12] for group in ranked]
            best = None
            for a, b in itertools.product(*choices):
                r1 = min(nearby_rests, key=lambda r: (distance(coordinates(a), coordinates(r))+distance(coordinates(r), coordinates(b)), r["place_id"]))
                r2 = min(nearby_rests, key=lambda r: (distance(coordinates(b), coordinates(r))+distance(coordinates(r), hp), r["place_id"]))
                points = [hp, coordinates(a), coordinates(r1), coordinates(b), coordinates(r2), hp]
                km = sum(distance(x, y) for x, y in zip(points, points[1:]))
                key = (km, a["place_id"], b["place_id"], r1["place_id"], r2["place_id"])
                if best is None or key < best[0]:
                    best = key, a, b, r1, r2
            if best is None or best[0][0] > rules["max_km_per_day"]:
                break
            _, a, b, r1, r2 = best
            used.update((a["place_id"], b["place_id"]))
            days.append({"day": day, "activities": [a["place_id"], b["place_id"]],
                         "restaurants": [r1["place_id"], r2["place_id"]]})
        if len(days) == case["trip_duration"]:
            plan = {"hotel_id": hotel["place_id"], "days": days}
            if check_plan(plan, case, data)["passed"]:
                return plan
    return None


def main():
    data = load_datasets(ROOT / "data")
    original = json.loads((ROOT / "revision/cases/original.json").read_text())
    # Scenario definitions fixed before generating any model response. Each interest
    # must occupy at least one activity slot per day, competing for the same two slots.
    groups = [("Shopping", "Entertainment"), ("Culture & History", "Shopping"),
              ("Nature & Outdoors", "Entertainment"), ("Religious", "Shopping"),
              ("Landmarks & Sightseeing", "Entertainment")]
    scenarios = [(1, "Low", 25, 350), (2, "Medium", 40, 750),
                 (2, "High", 50, 1400), (3, "Low", 40, 900)]
    cases, proofs = [], []
    for interests, (days, budget, km, cap) in itertools.product(groups, scenarios):
        case = {"case_id": f"H{len(cases)+1:02d}", "trip_duration": days,
                "interests": list(interests), "budget_level": budget,
                "constraints": {"max_km_per_day": km, "hotel_cap_sar": cap,
                                "nights": max(1, days-1),
                                "minimum_interest_slots": {interest: days for interest in interests}}}
        plan = witness(case, data)
        if plan is None:
            raise ValueError(f"No feasible witness found for {case}; do not freeze an unsupported case")
        cases.append(case)
        proofs.append({"case_id": case["case_id"], "witness": plan, "check": check_plan(plan, case, data)})
    for name, value in (("hard.json", cases), ("all.json", original+cases), ("feasibility_witnesses.json", proofs)):
        (ROOT / "revision/cases" / name).write_text(json.dumps(value, indent=2, ensure_ascii=False)+"\n")
    print(f"Preserved {len(original)} original cases; added {len(cases)} feasible hard cases")


if __name__ == "__main__":
    main()
