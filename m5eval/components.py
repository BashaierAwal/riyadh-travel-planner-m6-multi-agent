"""Offline contract checks on the preserved baseline's actual search tools."""

import pandas as pd

from . import baseline_tools as tools


def evaluate_components(data_dir, cases, datasets):
    for name in ("activities", "restaurants", "hotels"):
        setattr(tools, name, pd.read_csv(data_dir / f"{name}.csv", float_precision="round_trip"))
    results = []
    for case in cases:
        checks = {}
        specs = [
            ("activities", tools.find_activities, {"interests": case["interests"]}, 30),
            ("restaurants", tools.find_restaurants, {"budget_level": case["budget_level"]}, 10),
            ("hotels", tools.find_hotels, {"budget_level": case["budget_level"]}, 5),
        ]
        for name, function, arguments, limit in specs:
            eligible = {pid for pid, row in datasets[name].items()
                        if (row["interest_group"] in case["interests"] if name == "activities"
                            else row["budget_level"] == case["budget_level"])}
            rows = function(**arguments)
            ids = [row["place_id"] for row in rows]
            contract = {
                "all_returned_ids_eligible": set(ids) <= eligible,
                "no_duplicate_candidates": len(ids) == len(set(ids)),
                "expected_candidate_count": len(ids) == min(limit, len(eligible)),
                "repeat_call_same_ids": ids == [r["place_id"] for r in function(**arguments)],
            }
            if not all(contract.values()):
                raise AssertionError(f"Component contract failed: {case['case_id']} {name} {contract}")
            checks[name] = {"eligible_count": len(eligible), "returned_count": len(ids),
                            "checks": contract, "passed": True}
        results.append({"case_id": case["case_id"], "components": checks})
    return {"evaluation_type": "offline search-tool contract evaluation",
            "scope": "Dataset membership, category/budget eligibility, default limits, uniqueness and repeatability; not model tool-selection quality.",
            "case_count": len(cases), "tool_invocations": len(cases) * 3 * 2,
            "case_tool_contracts": len(cases) * 3, "results": results}
