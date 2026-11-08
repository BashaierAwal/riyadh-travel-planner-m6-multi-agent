"""OFFLINE FIXTURE ONLY. Deterministic HTTP replies are never experimental evidence."""

import json
from m5eval.evaluate import ROOT
from m5eval.experiment import golden_cases
from m5eval.generation import build_prompt, make_tools


class FakeClock:
    def __init__(self):
        self.value, self.waits = 100.0, []

    def clock(self):
        return self.value

    def sleep(self, seconds):
        self.waits.append(seconds)
        self.value += seconds


def response_body(value):
    return {"candidates": [{"content": {"role": "model", "parts": [{"text": json.dumps(value)}]}, "finishReason": "STOP"}],
            "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5, "totalTokenCount": 15},
            "modelVersion": "OFFLINE_FIXTURE_NOT_A_REAL_MODEL"}


def tool_response(case, names):
    args = {"find_activities": {"interests": case["interests"]},
            "find_restaurants": {"budget_level": case["budget_level"]},
            "find_hotels": {"budget_level": case["budget_level"]}}
    body = response_body(None)
    body["candidates"][0]["content"]["parts"] = [{"functionCall": {"name": name, "args": args[name]}} for name in names]
    return body


class MockService:
    def __init__(self, clock):
        self.clock, self.calls, self.cache = clock, [], {}

    def itinerary(self, case):
        if case["case_id"] not in self.cache:
            tools = make_tools(ROOT / "data", lambda event: None)
            activities = tools[0](case["interests"])
            restaurants = tools[1](case["budget_level"])
            hotels = tools[2](case["budget_level"])
            # Intentionally preserve short candidate sets as repeated-activity fixtures.
            ids = [row["place_id"] for row in activities]
            self.cache[case["case_id"]] = {"hotel_id": hotels[0]["place_id"], "days": [
                {"day": day + 1, "activities": [ids[(2*day+j) % len(ids)] for j in range(2)],
                 "restaurants": [restaurants[j % len(restaurants)]["place_id"] for j in range(2)]}
                for day in range(case["trip_duration"])]}
        return self.cache[case["case_id"]]

    def __call__(self, request):
        import httpx
        body = json.loads(request.content)
        prompt = body["contents"][0]["parts"][0]["text"]
        self.calls.append(body)
        self.clock.value += 0.05
        if "\nContext:\n" in prompt:
            case = json.loads(prompt.split("\nContext:\n", 1)[1])["user_input"]
            if 'Return ONLY JSON: {"type":"dispatch"' in prompt:
                return httpx.Response(200, json=response_body({"type": "dispatch", "activity_task": "Select activities", "budget_task": "Select hotel/restaurants and check structure"}))
            if "You are the Attraction and Preference specialist." in prompt:
                stage = "activities"
            elif "You are the Budget and Structural Feasibility specialist." in prompt:
                stage = "budget"
            else:
                stage = "final"
        else:
            case = next(c for c in golden_cases() if prompt == build_prompt(c))
            stage = "baseline"
        trip = self.itinerary(case)
        if stage != "final" and len(body["contents"]) == 1:
            names = {"baseline": ["find_activities", "find_restaurants", "find_hotels"],
                     "activities": ["find_activities"], "budget": ["find_restaurants", "find_hotels"]}[stage]
            return httpx.Response(200, json=tool_response(case, names))
        if stage == "activities":
            value = {"type": "activities", "days": [{"day": d["day"], "activities": d["activities"]} for d in trip["days"]], "notes": "Offline fixture"}
        elif stage == "budget":
            value = {"type": "budget", "hotel_id": trip["hotel_id"],
                     "days": [{"day": d["day"], "restaurants": d["restaurants"]} for d in trip["days"]],
                     "checks": ["Offline fixture"], "notes": "Offline fixture"}
        else:
            value = trip
        return httpx.Response(200, json=response_body(value))
