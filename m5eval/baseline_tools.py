"""Search functions extracted unchanged from the preserved baseline notebook.

Only these six reviewed definitions are included. Notebook cells are never executed.
Dataset globals are bound by the offline component evaluator.
"""

import pandas as pd

INTEREST_OPTIONS = ["Shopping", "Entertainment", "Culture & History", "Nature & Outdoors",
                    "Religious", "Sports", "Landmarks & Sightseeing"]
BUDGET_OPTIONS = ["Low", "Medium", "High"]

def search_activities(interests, limit=20, exclude_ids=None):
    """
    Search activities matching user interests.
    Returns dataset-backed activity candidates.
    """

    if isinstance(interests, str):
        interests = [interests]

    if not interests or not set(interests).issubset(INTEREST_OPTIONS):
        raise ValueError("Invalid interests")

    if not isinstance(limit, int) or limit < 1:
        raise ValueError("limit must be a positive integer")

    exclude_ids = set(exclude_ids or [])

    # Filter by selected interests
    results = activities[
        activities["interest_group"].isin(interests)
    ].copy()

    # Exclude previously selected activities
    results = results[
        ~results["place_id"].isin(exclude_ids)
    ]

    # Prefer activities with more rating evidence
    results["_rating"] = pd.to_numeric(
        results["rating"], errors="coerce"
    ).fillna(-1)

    results["_rating_count"] = pd.to_numeric(
        results["number_of_ratings"], errors="coerce"
    ).fillna(0)

    results = results.sort_values(
        by=["_rating", "_rating_count", "place_id"],
        ascending=[False, False, True]
    )

    columns = [
        "place_id",
        "name",
        "interest_group",
        "rating",
        "number_of_ratings"
    ]

    return results[columns].head(limit).to_dict(
        orient="records"
    )

def search_restaurants(budget_level, limit=20, exclude_ids=None):
    """
    Search restaurants by the user's budget level.
    """

    if budget_level not in BUDGET_OPTIONS:
        raise ValueError("Invalid budget level")

    if not isinstance(limit, int) or limit < 1:
        raise ValueError("limit must be a positive integer")

    exclude_ids = set(exclude_ids or [])

    results = restaurants[
        restaurants["budget_level"] == budget_level
    ].copy()

    results = results[
        ~results["place_id"].isin(exclude_ids)
    ]

    results["_rating"] = pd.to_numeric(
        results["rating"], errors="coerce"
    ).fillna(-1)

    results["_rating_signals"] = pd.to_numeric(
        results["ratingSignals"], errors="coerce"
    ).fillna(0)

    results = results.sort_values(
        by=["_rating", "_rating_signals", "place_id"],
        ascending=[False, False, True]
    )

    columns = [
        "place_id",
        "name",
        "budget_level",
        "rating",
        "ratingSignals"
    ]

    return results[columns].head(limit).to_dict(
        orient="records"
    )

def search_hotels(budget_level, limit=10):
    """
    Search hotels matching the user's budget level.
    """

    if budget_level not in BUDGET_OPTIONS:
        raise ValueError("Invalid budget level")

    if not isinstance(limit, int) or limit < 1:
        raise ValueError("limit must be a positive integer")

    results = hotels[
        hotels["budget_level"] == budget_level
    ].copy()

    results["_rating"] = pd.to_numeric(
        results["rating"], errors="coerce"
    ).fillna(-1)

    results["_count"] = pd.to_numeric(
        results["count"], errors="coerce"
    ).fillna(0)

    results = results.sort_values(
        by=["_rating", "_count", "place_id"],
        ascending=[False, False, True]
    )

    columns = [
        "place_id",
        "hotel_name",
        "budget_level",
        "median_price",
        "rating",
        "count"
    ]

    return results[columns].head(limit).to_dict(
        orient="records"
    )

def find_activities(interests: list[str], limit: int = 30) -> list[dict]:
    """
    Search Riyadh activities matching the user's interests.

    Args:
        interests: Selected interest groups.
        limit: Maximum number of activities to return.

    Returns:
        A list of matching activities from the dataset.
    """
    return search_activities(
        interests=interests,
        limit=limit
    )

def find_restaurants(
    budget_level: str,
    limit: int = 10
) -> list[dict]:
    """
    Search Riyadh restaurants by budget level.

    Args:
        budget_level: Low, Medium, or High.
        limit: Maximum number of restaurants.

    Returns:
        Matching restaurants from the dataset.
    """
    return search_restaurants(
        budget_level=budget_level,
        limit=limit
    )

def find_hotels(
    budget_level: str,
    limit: int = 5
) -> list[dict]:
    """
    Search Riyadh hotels matching the user's budget.

    Args:
        budget_level: Low, Medium, or High.
        limit: Maximum number of hotels to return.

    Returns:
        Matching hotels from the dataset.
    """
    return search_hotels(
        budget_level=budget_level,
        limit=limit
    )
