import base64
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import inspect

from bson import ObjectId
from fastapi import APIRouter, Body, HTTPException, Request
from pydantic import BaseModel

# Adjust import below to match backend/database.py exports
try:
    from backend.database import get_issues_collection
except ImportError:
    from database import get_issues_collection


def issues_collection():
    """Return the `issues` collection handle (Motor/async)."""
    return get_issues_collection()


# Optional priority recalculation import if severity changes
try:
    from backend.services.priority_engine import calculate_priority
except ImportError:
    try:
        from services.priority_engine import calculate_priority
    except ImportError:
        calculate_priority = None

router = APIRouter(tags=["Admin"])

DEFAULT_CATEGORY_TEAMS: Dict[str, str] = {
    "Pothole": "Roads & Maintenance Dept",
    "Water Leak": "Water Supply Board",
    "Broken Streetlight": "Electrical Grid Team",
    "Overflowing Garbage": "Sanitation & Waste Dept",
}

KNOWN_CATEGORIES: List[str] = [
    "Pothole",
    "Water Leak",
    "Overflowing Garbage",
    "Broken Streetlight",
]

KNOWN_STATUSES: List[str] = [
    "YET_TO_START",
    "WORKING",
    "DONE",
]

# Accept legacy / differently-cased labels the frontend may still send.
STATUS_ALIASES: Dict[str, str] = {
    "OPEN": "YET_TO_START",
    "PENDING": "YET_TO_START",
    "NEW": "YET_TO_START",
    "TODO": "YET_TO_START",
    "TO_DO": "YET_TO_START",
    "NOT_STARTED": "YET_TO_START",
    "YET_TO_START": "YET_TO_START",
    "YET TO START": "YET_TO_START",
    "IN_PROGRESS": "WORKING",
    "INPROGRESS": "WORKING",
    "IN PROGRESS": "WORKING",
    "ONGOING": "WORKING",
    "ASSIGNED": "WORKING",
    "WORKING": "WORKING",
    "RESOLVED": "DONE",
    "CLOSED": "DONE",
    "COMPLETE": "DONE",
    "COMPLETED": "DONE",
    "DONE": "DONE",
}


class AdminIssueUpdatePayload(BaseModel):
    status: Optional[str] = None
    assigned_team: Optional[str] = None
    after_image: Optional[str] = None
    resolution_notes: Optional[str] = None
    severity: Optional[int] = None


class WorkerProofPayload(BaseModel):
    after_image: Optional[str] = None
    photo_url: Optional[str] = None
    image: Optional[str] = None
    resolution_notes: Optional[str] = None
    status: Optional[str] = None


def _normalize_status(value: Any) -> Optional[str]:
    """Map a loosely-typed status string onto a KNOWN_STATUSES value, or None."""
    if value is None:
        return None
    key = str(value).strip().upper().replace("-", "_")
    if key in STATUS_ALIASES:
        return STATUS_ALIASES[key]
    if key in KNOWN_STATUSES:
        return key
    return None


def serialize_issue(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure every MongoDB document returned has string 'id' and '_id'."""
    if not doc:
        return {}
    serialized = dict(doc)
    raw_id = serialized.get("_id") or serialized.get("id")
    str_id = str(raw_id) if raw_id is not None else ""
    serialized["_id"] = str_id
    serialized["id"] = str_id

    for key, value in serialized.items():
        if isinstance(value, ObjectId):
            serialized[key] = str(value)
        elif isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            serialized[key] = value.isoformat()

    # Mirror priority_score <-> priority so either key the frontend reads is present.
    priority_raw = serialized.get("priority_score")
    if priority_raw is None:
        priority_raw = serialized.get("priority")
    try:
        priority_value = float(priority_raw) if priority_raw is not None else 0.0
    except (TypeError, ValueError):
        priority_value = 0.0
    serialized["priority_score"] = priority_value
    serialized["priority"] = priority_value

    # Mirror upvotes <-> report_count.
    try:
        upvotes_value = int(serialized.get("upvotes", 0) or 0)
    except (TypeError, ValueError):
        upvotes_value = 0
    report_count_raw = serialized.get("report_count")
    try:
        report_count_value = (
            int(report_count_raw) if report_count_raw is not None else max(1, upvotes_value + 1)
        )
    except (TypeError, ValueError):
        report_count_value = max(1, upvotes_value + 1)
    serialized["upvotes"] = upvotes_value
    serialized["report_count"] = report_count_value

    # Mirror after_image <-> worker_photo_url so the "After" photo is always found.
    after_value = serialized.get("after_image") or serialized.get("worker_photo_url")
    if after_value:
        serialized["after_image"] = after_value
        serialized["worker_photo_url"] = after_value

    return serialized


def _build_id_query(issue_id: str) -> Dict[str, Any]:
    """Match issue by ObjectId, string _id, or string id."""
    candidates: List[Dict[str, Any]] = [{"_id": issue_id}, {"id": issue_id}]
    if ObjectId.is_valid(issue_id):
        candidates.insert(0, {"_id": ObjectId(issue_id)})
    return {"$or": candidates}


def _resolve_default_team(category: Optional[str]) -> str:
    if not category:
        return "Roads & Maintenance Dept"
    if category in DEFAULT_CATEGORY_TEAMS:
        return DEFAULT_CATEGORY_TEAMS[category]
    cat_lower = category.lower()
    if "pothole" in cat_lower or "road" in cat_lower:
        return "Roads & Maintenance Dept"
    if "water" in cat_lower or "leak" in cat_lower:
        return "Water Supply Board"
    if "light" in cat_lower or "electric" in cat_lower:
        return "Electrical Grid Team"
    if "garbage" in cat_lower or "waste" in cat_lower or "trash" in cat_lower:
        return "Sanitation & Waste Dept"
    return "General Municipal Dept"


def _parse_utc_datetime(val: Any) -> Optional[datetime]:
    """Safely parse ISO string or datetime object into a UTC-aware datetime."""
    if not val:
        return None
    if isinstance(val, datetime):
        return val if val.tzinfo is not None else val.replace(tzinfo=timezone.utc)
    if isinstance(val, str):
        cleaned = val.strip()
        if cleaned.endswith("Z"):
            cleaned = cleaned[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(cleaned)
            return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _age_hours(val: Any) -> float:
    """Hours elapsed since `val`, clamped at 0.0 for far-future/unknown values."""
    dt = _parse_utc_datetime(val)
    if not dt:
        return 0.0
    return max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0)


def _extract_priority(issue: Dict[str, Any]) -> int:
    """Read the urgency score, tolerating both `priority` and `priority_score`."""
    raw = issue.get("priority")
    if raw is None:
        raw = issue.get("priority_score", 0)
    try:
        return int(float(raw or 0))
    except (TypeError, ValueError):
        return 0


async def _db_find_one(query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    res = issues_collection().find_one(query)
    if inspect.isawaitable(res):
        return await res
    return res


async def _db_update_one(query: Dict[str, Any], update: Dict[str, Any]) -> Any:
    res = issues_collection().update_one(query, update)
    if inspect.isawaitable(res):
        return await res
    return res


async def _db_find_all(query: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    cursor = issues_collection().find(query or {})
    if hasattr(cursor, "to_list"):
        res = cursor.to_list(length=None)
        if inspect.isawaitable(res):
            return await res
        return list(res)
    return list(cursor)


def _daily_buckets(issues: List[Dict[str, Any]], field: str, days: int = 14) -> List[Dict[str, Any]]:
    """Zero-filled `{"date": "YYYY-MM-DD", "count": n}` buckets for the last `days`."""
    today = datetime.now(timezone.utc).date()
    window = [today - timedelta(days=offset) for offset in range(days - 1, -1, -1)]
    counts: Counter = Counter()
    for issue in issues:
        dt = _parse_utc_datetime(issue.get(field))
        if dt:
            counts[dt.date()] += 1
    return [{"date": day.isoformat(), "count": counts.get(day, 0)} for day in window]


def _build_analytics_extras(
    issues: List[Dict[str, Any]],
    total_issues: int,
    pending_count: int,
    in_progress_count: int,
    resolved_count: int,
    avg_resolution_hours: float,
) -> Dict[str, Any]:
    """Keys the original `get_analytics` stub promised, alongside our existing ones."""
    total_upvotes = sum(int(i.get("upvotes", 0) or 0) for i in issues)

    stats = {
        "total_issues": total_issues,
        "yet_to_start": pending_count,
        "working": in_progress_count,
        "done": resolved_count,
        # 0.0-1.0 scale, as the AnalyticsResponse contract expects.
        "resolution_rate": round(resolved_count / total_issues, 4) if total_issues else 0.0,
        "avg_resolution_hours": avg_resolution_hours,
        "total_upvotes": total_upvotes,
    }

    breakdown_map: Dict[str, Dict[str, Any]] = {}
    for issue in issues:
        cat = issue.get("category") or "Uncategorized"
        entry = breakdown_map.setdefault(cat, {"category": cat, "total": 0, "done": 0})
        entry["total"] += 1
        if issue.get("status") == "DONE":
            entry["done"] += 1
    category_breakdown = sorted(breakdown_map.values(), key=lambda e: e["total"], reverse=True)

    leaderboard_sorted = sorted(issues, key=_extract_priority, reverse=True)
    priority_leaderboard = [
        {
            "id": i.get("id") or i.get("_id") or "",
            "title": i.get("title", ""),
            "category": i.get("category", ""),
            "priority": _extract_priority(i),
            "upvotes": int(i.get("upvotes", 0) or 0),
            "status": i.get("status", ""),
        }
        for i in leaderboard_sorted[:10]
    ]

    return {
        "stats": stats,
        "category_breakdown": category_breakdown,
        "priority_leaderboard": priority_leaderboard,
        "daily_created": _daily_buckets(issues, "created_at"),
        "daily_resolved": _daily_buckets(issues, "resolved_at"),
    }


async def _handle_issue_update(
    issue_id: str,
    payload: AdminIssueUpdatePayload,
) -> Dict[str, Any]:
    query = _build_id_query(issue_id)
    existing = await _db_find_one(query)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Issue '{issue_id}' not found")

    update_fields: Dict[str, Any] = {}
    data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else payload.dict(exclude_unset=True)

    new_status = data.get("status")
    if new_status is not None:
        normalized_status = _normalize_status(new_status)
        if normalized_status is None:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{new_status}'. Must be one of {KNOWN_STATUSES}",
            )
        new_status = normalized_status
        update_fields["status"] = new_status

    incoming_team = data.get("assigned_team")
    if incoming_team is not None and incoming_team.strip() and incoming_team.strip().lower() != "unassigned":
        update_fields["assigned_team"] = incoming_team.strip()

    effective_status = new_status or existing.get("status")
    current_team = update_fields.get("assigned_team") or existing.get("assigned_team")

    if effective_status == "WORKING":
        if not current_team or str(current_team).strip().lower() in ("", "unassigned", "none"):
            update_fields["assigned_team"] = _resolve_default_team(existing.get("category"))

    if "after_image" in data and data["after_image"] is not None:
        update_fields["after_image"] = data["after_image"]
        update_fields["worker_photo_url"] = data["after_image"]

    if "resolution_notes" in data and data["resolution_notes"] is not None:
        update_fields["resolution_notes"] = data["resolution_notes"]

    if effective_status == "DONE":
        update_fields["resolved_at"] = datetime.now(timezone.utc).isoformat()
        if not update_fields.get("assigned_team") and (
            not current_team or str(current_team).strip().lower() in ("", "unassigned", "none")
        ):
            update_fields["assigned_team"] = _resolve_default_team(existing.get("category"))

    if "severity" in data and data["severity"] is not None:
        update_fields["severity"] = int(data["severity"])
        if callable(calculate_priority):
            try:
                merged = {**existing, **update_fields}
                priority_value = calculate_priority(
                    merged.get("category") or "Other",
                    int(merged.get("upvotes", 0) or 0),
                    _age_hours(merged.get("created_at")),
                    bool(merged.get("worker_photo_url") or merged.get("after_image")),
                    bool(merged.get("duplicate_of")),
                )
                update_fields["priority"] = int(priority_value)
                update_fields["priority_score"] = int(priority_value)
            except Exception:
                pass

    update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()

    if update_fields:
        await _db_update_one({"_id": existing["_id"]}, {"$set": update_fields})

    updated_doc = await _db_find_one({"_id": existing["_id"]})
    return serialize_issue(updated_doc or {**existing, **update_fields})


@router.patch("/api/admin/issues/{issue_id}")
@router.put("/api/admin/issues/{issue_id}")
@router.patch("/api/admin/issues/{issue_id}/status")
@router.put("/api/admin/issues/{issue_id}/status")
@router.patch("/api/issues/{issue_id}/status")
@router.put("/api/issues/{issue_id}/status")
async def update_admin_issue(
    issue_id: str,
    payload: AdminIssueUpdatePayload = Body(...),
) -> Dict[str, Any]:
    """Move an issue between Yet to Start / Working / Done (and patch admin fields).

    Kept as an alias for the original `update_status` stub path
    (`PATCH/PUT /api/admin/issues/{issue_id}/status`).
    """
    return await _handle_issue_update(issue_id, payload)


@router.get("/api/admin/issues")
async def list_all_issues(
    status: Optional[str] = None,
    category: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Every issue, for rendering the Kanban board.

    Optional `status` / `category` filters narrow the result. Sorted by
    `priority_score` descending; the frontend groups by `status` into columns.
    """
    query: Dict[str, Any] = {}
    if status:
        query["status"] = status
    if category:
        query["category"] = category

    docs = await _db_find_all(query)
    issues = [serialize_issue(d) for d in docs]
    issues.sort(key=lambda x: float(x.get("priority_score", 0.0) or 0.0), reverse=True)
    return issues


@router.post("/api/admin/issues/{issue_id}/photo")
@router.patch("/api/admin/issues/{issue_id}/photo")
async def upload_worker_proof(
    issue_id: str,
    request: Request,
) -> Dict[str, Any]:
    """Attach the worker's "after" proof photo and mark the issue resolved.

    Accepts multipart/form-data (a `UploadFile` under `file`/`photo`/`after_image`/
    `image`), application/x-www-form-urlencoded, or application/json. The image is
    stored as a base64 data URL in BOTH `after_image` and `worker_photo_url`.

    Raises:
        404: issue not found.
    """
    query = _build_id_query(issue_id)
    existing = await _db_find_one(query)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Issue '{issue_id}' not found")

    content_type = request.headers.get("content-type", "").lower()

    after_image: Optional[str] = None
    resolution_notes: Optional[str] = None
    incoming_status: Any = None

    if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        try:
            form = await request.form()
        except Exception:
            form = {}

        for key in ("file", "photo", "after_image", "image"):
            candidate = form.get(key)
            if candidate is not None and hasattr(candidate, "read"):
                raw_bytes = await candidate.read()
                file_ct = getattr(candidate, "content_type", None) or "image/jpeg"
                b64_str = base64.b64encode(raw_bytes).decode("ascii")
                after_image = f"data:{file_ct};base64,{b64_str}"
                break

        if after_image is None:
            for item in form.values():
                if hasattr(item, "read"):
                    raw_bytes = await item.read()
                    file_ct = getattr(item, "content_type", None) or "image/jpeg"
                    b64_str = base64.b64encode(raw_bytes).decode("ascii")
                    after_image = f"data:{file_ct};base64,{b64_str}"
                    break

        if after_image is None:
            candidate = form.get("after_image") or form.get("photo_url")
            if candidate is not None and not hasattr(candidate, "read"):
                after_image = candidate

        notes_field = form.get("resolution_notes")
        if notes_field is not None and not hasattr(notes_field, "read"):
            resolution_notes = notes_field
        incoming_status = form.get("status")
    else:
        try:
            body = await request.json()
        except Exception:
            body = {}
        if not isinstance(body, dict):
            body = {}
        after_image = (
            body.get("after_image")
            or body.get("photo_url")
            or body.get("image")
            or body.get("worker_photo_url")
        )
        resolution_notes = body.get("resolution_notes")
        incoming_status = body.get("status")

    update_fields: Dict[str, Any] = {}
    if after_image:
        update_fields["after_image"] = after_image
        update_fields["worker_photo_url"] = after_image

    if resolution_notes is not None:
        update_fields["resolution_notes"] = resolution_notes

    # Default to DONE unless another valid status was explicitly passed.
    new_status = _normalize_status(incoming_status) or "DONE"
    update_fields["status"] = new_status
    if new_status == "DONE":
        update_fields["resolved_at"] = datetime.now(timezone.utc).isoformat()

    if after_image and callable(calculate_priority):
        try:
            merged = {**existing, **update_fields}
            priority_value = calculate_priority(
                merged.get("category") or "Other",
                int(merged.get("upvotes", 0) or 0),
                _age_hours(merged.get("created_at")),
                True,
                bool(merged.get("duplicate_of")),
            )
            update_fields["priority"] = int(priority_value)
            update_fields["priority_score"] = int(priority_value)
        except Exception:
            pass

    update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()

    await _db_update_one({"_id": existing["_id"]}, {"$set": update_fields})
    updated_doc = await _db_find_one({"_id": existing["_id"]})
    return serialize_issue(updated_doc or {**existing, **update_fields})


@router.get("/api/admin/analytics")
@router.get("/api/admin/stats")
async def get_admin_stats() -> Dict[str, Any]:
    docs = await _db_find_all()
    issues = [serialize_issue(d) for d in docs]

    total_issues = len(issues)
    pending_count = sum(1 for i in issues if i.get("status") == "YET_TO_START")
    in_progress_count = sum(1 for i in issues if i.get("status") == "WORKING")
    resolved_count = sum(1 for i in issues if i.get("status") == "DONE")

    resolution_rate = (
        round((resolved_count / total_issues) * 100.0, 1) if total_issues > 0 else 0.0
    )

    resolution_durations_hours: List[float] = []
    for issue in issues:
        if issue.get("status") == "DONE":
            created_dt = _parse_utc_datetime(issue.get("created_at"))
            resolved_dt = _parse_utc_datetime(issue.get("resolved_at"))
            if created_dt and resolved_dt:
                diff_hours = max(0.0, (resolved_dt - created_dt).total_seconds() / 3600.0)
                resolution_durations_hours.append(diff_hours)

    avg_resolution_hours = (
        round(sum(resolution_durations_hours) / len(resolution_durations_hours), 2)
        if resolution_durations_hours
        else 0.0
    )

    by_category: Dict[str, int] = {cat: 0 for cat in KNOWN_CATEGORIES}
    for issue in issues:
        cat = issue.get("category") or "Uncategorized"
        by_category[cat] = by_category.get(cat, 0) + 1

    category_chart_data = [
        {"name": cat, "count": count} for cat, count in by_category.items()
    ]

    by_status: Dict[str, int] = {
        "YET_TO_START": pending_count,
        "WORKING": in_progress_count,
        "DONE": resolved_count,
    }
    status_chart_data = [
        {"name": st, "count": count} for st, count in by_status.items()
    ]

    unresolved_issues = [i for i in issues if i.get("status") != "DONE"]
    unresolved_issues.sort(
        key=lambda x: float(x.get("priority_score", 0.0) or 0.0),
        reverse=True,
    )
    top_priority_issues = unresolved_issues[:5]

    payload: Dict[str, Any] = {
        "total_issues": total_issues,
        "pending_count": pending_count,
        "in_progress_count": in_progress_count,
        "resolved_count": resolved_count,
        "resolution_rate": resolution_rate,
        "avg_resolution_hours": avg_resolution_hours,
        "by_category": by_category,
        "category_chart_data": category_chart_data,
        "by_status": by_status,
        "status_chart_data": status_chart_data,
        "top_priority_issues": top_priority_issues,
    }

    # Extra keys promised by the original `get_analytics` stub / AnalyticsResponse.
    payload.update(
        _build_analytics_extras(
            issues,
            total_issues,
            pending_count,
            in_progress_count,
            resolved_count,
            avg_resolution_hours,
        )
    )
    return payload
