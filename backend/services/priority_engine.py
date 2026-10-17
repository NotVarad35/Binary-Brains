"""Dev 1 — Duplicate check (Haversine) + Priority algorithm.

Contract file: `priority_engine` is imported by BOTH routers, so the
signatures below are fixed. Fill in the TODO bodies; do not rename.

Contract:
    haversine_distance(lat1, lon1, lat2, lon2) -> float   [DONE]
    find_duplicates(collection, lat, lon, radius_m)       [TODO]
    calculate_priority(category, upvotes, ...) -> int     [TODO]
"""

import math
from typing import List

# Upper bound of the priority score. Clamped so the frontend can render a
# stable 0-100 bar without needing to know the weighting internals.
PRIORITY_MAX = 100

# Base severity per category, before upvote / age bonuses. Dev 1 owns these
# numbers — they drive the "priority leaderboard" on AnalyticsPage.
CATEGORY_WEIGHTS = {
    "Pothole": 40,
    "Street Light": 35,
    "Garbage": 25,
    "Graffiti": 15,
    "Water Logging": 45,
    "Broken Road": 50,
    "Sewage": 55,
    "Other": 20,
}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two WGS-84 points, in METRES.

    Implemented so the duplicate check matches what MongoDB's $near returns,
    letting us double-check results in Python rather than trusting the
    geo index alone.

    Args:
        lat1, lon1: first point (degrees).
        lat2, lon2: second point (degrees).

    Returns:
        Distance in metres.
    """
    radius_m = 6_371_000  # mean Earth radius

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return radius_m * c


def find_duplicates(collection, lat: float, lon: float, radius_m: float = 100.0) -> List[dict]:
    """Return issues already reported within `radius_m` of (lat, lon).

    TODO(Dev 1): implement using the 2dsphere index created in
    `database.ensure_indexes()`.

        1. Build GeoJSON point: {"type": "Point", "coordinates": [lon, lat]}
           (note: coordinates are [lon, lat], NOT [lat, lon]).
        2. `collection.find({"location": {"$near": {"$geometry": point,
           "$maxDistance": radius_m}}})`.
        3. Also filter on category if you want cross-category vs same-category
           duplicate behaviour — your call, document it in the README.

    Returns:
        Matching documents, sorted nearest-first. Empty list if none.
    """
    raise NotImplementedError("TODO(Dev 1): implement find_duplicates()")


def calculate_priority(
    category: str,
    upvotes: int = 0,
    age_hours: float = 0.0,
    has_worker_photo: bool = False,
    is_duplicate: bool = False,
) -> int:
    """Score how urgently an issue should be worked, 0..PRIORITY_MAX.

    TODO(Dev 1): implement the scoring formula.

    Intended shape (adapt as you see fit, but keep the signature):

        score  = CATEGORY_WEIGHTS.get(category, 20)          # base severity
               + min(upvotes * 5, 40)                        # community demand
               + min(age_hours * 0.5, 20)                    # time open
               - (20 if is_duplicate else 0)                 # penalise dupes
        return max(0, min(score, PRIORITY_MAX))              # clamp to 0-100

    Constraints the rest of the app depends on:
        - Must return an `int`.
        - Must stay within 0..PRIORITY_MAX inclusive.
        - Must be deterministic for identical inputs (AnalyticsPage sorts on it).

    Args:
        category: one of `models.Category` values.
        upvotes: current upvote count.
        age_hours: hours since `created_at`.
        has_worker_photo: True once a worker uploaded proof (signals progress).
        is_duplicate: True when linked to another report of the same issue.

    Returns:
        Priority score as an int.
    """
    raise NotImplementedError("TODO(Dev 1): implement calculate_priority()")
