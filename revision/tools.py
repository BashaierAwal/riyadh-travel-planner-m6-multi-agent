"""Shared dataset tools for all revised conditions, using only Python's standard library."""

import json

from .constraints import check_plan, coordinates, distance, number


class Tools:
    def __init__(self, datasets, case, emit):
        self.data, self.case, self.emit = datasets, case, emit
        self.returned = {name: set() for name in datasets}

    def search(self, group, filters, limit, center_id=None):
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("limit must be an integer from 1 to 100")
        rows = [r for r in self.data[group].values() if filters(r)
                and (not self.case.get("constraints") or coordinates(r))]
        center = None
        if center_id:
            matches = [d[center_id] for d in self.data.values() if center_id in d]
            if not matches or not coordinates(matches[0]):
                raise ValueError("Unknown center or missing coordinates")
            center = coordinates(matches[0])
        def rank(row):
            rating = number(row.get("rating"))
            count = number(row.get("number_of_ratings", row.get("ratingSignals", row.get("count"))))
            quality = (-(rating if rating is not None else -1), -(count or 0), row["place_id"])
            return (distance(center, coordinates(row)) if coordinates(row) else float("inf"), *quality) if center else quality
        rows.sort(key=rank)
        fields = ("place_id", "name", "hotel_name", "interest_group", "budget_level", "median_price", "rating")
        result = [{**{k: r[k] for k in fields if k in r},
                   "latitude": coordinates(r)[0] if coordinates(r) else None,
                   "longitude": coordinates(r)[1] if coordinates(r) else None} for r in rows[:limit]]
        self.returned[group].update(r["place_id"] for r in result)
        return result

    def call(self, name, args):
        self.emit({"kind": "tool_call", "name": name, "arguments": args})
        try:
            allowed = {"find_activities", "find_restaurants", "find_hotels", "check_plan"}
            if name not in allowed or not isinstance(args, dict):
                raise ValueError("Unknown tool or invalid arguments")
            result = getattr(self, name)(**args)
            self.emit({"kind": "tool_result", "name": name, "result": result, "status": "success"})
            return result
        except (ValueError, TypeError, KeyError) as error:
            result = {"error": str(error)}
            self.emit({"kind": "tool_result", "name": name, "result": result, "status": "error"})
            return result

    def find_activities(self, interests, limit=30, center_id=None):
        known = {r["interest_group"] for r in self.data["activities"].values()}
        if not isinstance(interests, list) or not interests or any(i not in known for i in interests):
            raise ValueError("Use known interest groups")
        return self.search("activities", lambda r: r["interest_group"] in interests, limit, center_id)

    def find_restaurants(self, budget_level, limit=10, center_id=None):
        if budget_level not in ("Low", "Medium", "High"):
            raise ValueError("Unknown budget level")
        return self.search("restaurants", lambda r: r["budget_level"] == budget_level, limit, center_id)

    def find_hotels(self, budget_level, limit=10, center_id=None):
        if budget_level not in ("Low", "Medium", "High"):
            raise ValueError("Unknown budget level")
        return self.search("hotels", lambda r: r["budget_level"] == budget_level, limit, center_id)

    def check_plan(self, plan_json):
        if not isinstance(plan_json, str):
            raise ValueError("Pass the complete plan as a JSON string")
        return check_plan(plan_json, self.case, self.data)

    def grounding_errors(self, plan):
        if not isinstance(plan, dict):
            return []
        missing = []
        hotel = plan.get("hotel_id")
        if isinstance(hotel, str) and hotel not in self.returned["hotels"]:
            missing.append({"group": "hotels", "place_id": hotel})
        for day in plan.get("days", []) if isinstance(plan.get("days"), list) else []:
            if not isinstance(day, dict):
                continue
            for group in ("activities", "restaurants"):
                for pid in day.get(group, []) if isinstance(day.get(group), list) else []:
                    if isinstance(pid, str) and pid not in self.returned[group]:
                        missing.append({"group": group, "place_id": pid})
        return missing


def declarations(names):
    specs = {
        "find_activities": {"interests": {"type": "ARRAY", "items": {"type": "STRING"}}},
        "find_restaurants": {"budget_level": {"type": "STRING", "enum": ["Low", "Medium", "High"]}},
        "find_hotels": {"budget_level": {"type": "STRING", "enum": ["Low", "Medium", "High"]}},
        "check_plan": {"plan_json": {"type": "STRING", "description": "Complete itinerary encoded as JSON"}},
    }
    descriptions = {
        "find_activities": "Find matching activities with coordinates; optionally rank nearest to center_id.",
        "find_restaurants": "Find budget-matching restaurants with coordinates; optionally rank nearest to center_id.",
        "find_hotels": "Find budget-matching hotels with median nightly SAR prices and coordinates.",
        "check_plan": "Check a full plan for structure, distance, hotel cost and interest constraints. Does not change the plan.",
    }
    result = []
    for name in names:
        fields = dict(specs[name])
        required = list(fields)
        if name != "check_plan":
            fields.update(limit={"type": "INTEGER"}, center_id={"type": "STRING"})
        result.append({"name": name, "description": descriptions[name],
                       "parameters": {"type": "OBJECT", "properties": fields, "required": required}})
    return result
