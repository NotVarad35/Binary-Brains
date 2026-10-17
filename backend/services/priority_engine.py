import math
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional

CATEGORY_WEIGHTS: Dict[str, int] = {
    "water leak": 5,
    "pothole": 4,
    "broken streetlight": 3,
    "overflowing garbage": 2,
}

DEFAULT_TEAMS: Dict[str, str] = {
    "water leak": "Water Supply Board",
    "pothole": "Roads & Maintenance Dept",
    "broken streetlight": "Electrical Grid Team",
    "overflowing garbage": "Sanitation & Waste Dept",
}


def get_category_weight(category: Optional[str]) -> int:
    if not category:
        return 3
    normalized = category.strip().lower()
    if normalized in CATEGORY_WEIGHTS:
        return CATEGORY_WEIGHTS[normalized]
    for key, weight in CATEGORY_WEIGHTS.items():
        if key in normalized or normalized in key:
            return weight
    return 3


def get_default_team(category: Optional[str]) -> str:
    if not category:
        return "Roads & Maintenance Dept"
    normalized = category.strip().lower()
    return DEFAULT_TEAMS.get(normalized, "Roads & Maintenance Dept")


def haversine_distance_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate the great-circle distance in meters between two GPS coordinates.
    """
    earth_radius_meters = 6371000.0
    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    delta_phi = math.radians(float(lat2) - float(lat1))
    delta_lambda = math.radians(float(lng2) - float(lng1))

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return round(earth_radius_meters * c, 2)


def _compute_hours_unresolved(created_at_iso: Optional[Any]) -> float:
    if not created_at_iso:
        return 0.0
    try:
        if isinstance(created_at_iso, datetime):
            created_dt = created_at_iso
        else:
            raw = str(created_at_iso).strip()
            if raw.endswith("Z"):
                raw = raw[:-1] + "+00:00"
            created_dt = datetime.fromisoformat(raw)

        if created_dt.tzinfo is None:
            created_dt = created_dt.replace(tzinfo=timezone.utc)

        now_utc = datetime.now(timezone.utc)
        diff_hours = (now_utc - created_dt).total_seconds() / 3600.0
        return max(0.0, diff_hours)
    except Exception:
        return 0.0


def calculate_priority_score(
    category: str,
    report_count: int = 1,
    severity: int = 3,
    created_at_iso: Optional[Any] = None,
) -> float:
    """
    Dynamic Priority Formula:
    Priority Score = (W_category * 10) + (report_count * 15) + (severity * 5) + (hours_unresolved * 2)
    """
    w_category = get_category_weight(category)
    safe_reports = max(1, int(report_count or 1))
    safe_severity = max(1, min(5, int(severity or 3)))
    hours_unresolved = _compute_hours_unresolved(created_at_iso)

    score = (
        (w_category * 10.0)
        + (safe_reports * 15.0)
        + (safe_severity * 5.0)
        + (hours_unresolved * 2.0)
    )
    return round(score, 1)


def extract_lat_lng(issue_doc: Dict[str, Any]) -> Optional[tuple]:
    loc = issue_doc.get("location")
    if isinstance(loc, dict) and loc.get("lat") is not None and loc.get("lng") is not None:
        try:
            return float(loc["lat"]), float(loc["lng"])
        except (TypeError, ValueError):
            pass
    if issue_doc.get("lat") is not None and issue_doc.get("lng") is not None:
        try:
            return float(issue_doc["lat"]), float(issue_doc["lng"])
        except (TypeError, ValueError):
            pass
    return None


def find_nearby_duplicate(
    existing_issues: Iterable[Dict[str, Any]],
    lat: float,
    lng: float,
    category: str,
    radius_meters: float = 50.0,
) -> Optional[Dict[str, Any]]:
    """
    Returns the closest unresolved issue of the same category within `radius_meters` (default 50m).
    """
    target_category = (category or "").strip().lower()
    closest_issue: Optional[Dict[str, Any]] = None
    closest_distance = float("inf")

    for issue in existing_issues:
        status = str(issue.get("status", "YET_TO_START")).upper()
        if status == "DONE":
            continue

        issue_cat = str(issue.get("category", "")).strip().lower()
        if issue_cat != target_category:
            continue

        coords = extract_lat_lng(issue)
        if not coords:
            continue

        dist = haversine_distance_meters(lat, lng, coords[0], coords[1])
        if dist <= radius_meters and dist < closest_distance:
            closest_distance = dist
            closest_issue = issue

    return closest_issue