import inspect
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query

# Dual-import support so running from `backend/` or repo root both work across all devices
try:
    from backend.models import IssueCreate
    from backend.services.priority_engine import (
        calculate_priority_score,
        extract_lat_lng,
        find_nearby_duplicate,
        get_default_team,
        haversine_distance_meters,
    )
except ImportError:
    from models import IssueCreate
    from services.priority_engine import (
        calculate_priority_score,
        extract_lat_lng,
        find_nearby_duplicate,
        get_default_team,
        haversine_distance_meters,
    )

router = APIRouter(tags=["Citizen Issues"])

# In-memory fallback store so independent local testing works even if MongoDB is not configured yet
_FALLBACK_ISSUES_STORE: List[Dict[str, Any]] = []


def _resolve_db_collection():
    """
    Dynamically inspects `database.py` to find the MongoDB `issues` collection regardless of how
    Dev 3 names the exported variables (`issues_collection`, `collection`, `db`, `get_database`, etc.).
    Returns None if MongoDB is unavailable, triggering the automatic in-memory fallback.
    """
    db_mod = None
    for mod_name in ("backend.database", "database"):
        try:
            db_mod = __import__(mod_name, fromlist=["*"])
            break
        except Exception:
            continue

    if db_mod is None:
        return None

    for attr in ("issues_collection", "collection", "issues"):
        col = getattr(db_mod, attr, None)
        if col is not None:
            return col

    for db_attr in ("db", "database"):
        db_obj = getattr(db_mod, db_attr, None)
        if db_obj is not None:
            try:
                return db_obj["issues"]
            except Exception:
                pass

    for fn_attr in ("get_database", "get_db"):
        fn = getattr(db_mod, fn_attr, None)
        if callable(fn):
            try:
                db_obj = fn()
                if db_obj is not None and not inspect.iscoroutine(db_obj):
                    return db_obj["issues"]
            except Exception:
                pass

    return None


async def _maybe_await(result: Any) -> Any:
    if inspect.isawaitable(result):
        return await result
    return result


async def _fetch_all_issues_raw() -> List[Dict[str, Any]]:
    col = _resolve_db_collection()
    if col is None:
        return [dict(item) for item in _FALLBACK_ISSUES_STORE]

    try:
        cursor = col.find({})
        if hasattr(cursor, "to_list"):
            docs = await _maybe_await(cursor.to_list(length=1000))
        else:
            docs = list(cursor)
        return docs
    except Exception:
        return [dict(item) for item in _FALLBACK_ISSUES_STORE]


async def _insert_issue_raw(doc: Dict[str, Any]) -> Dict[str, Any]:
    col = _resolve_db_collection()
    if col is None:
        doc["_id"] = str(ObjectId())
        _FALLBACK_ISSUES_STORE.append(dict(doc))
        return doc

    try:
        res = await _maybe_await(col.insert_one(doc))
        doc["_id"] = getattr(res, "inserted_id", doc.get("_id") or str(ObjectId()))
        return doc
    except Exception:
        doc["_id"] = str(ObjectId())
        _FALLBACK_ISSUES_STORE.append(dict(doc))
        return doc


async def _update_issue_raw(issue_id: Any, update_fields: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    col = _resolve_db_collection()
    queries = []
    if isinstance(issue_id, ObjectId):
        queries.append({"_id": issue_id})
    else:
        raw_str = str(issue_id)
        if ObjectId.is_valid(raw_str):
            queries.append({"_id": ObjectId(raw_str)})
        queries.append({"_id": raw_str})
        queries.append({"id": raw_str})

    if col is not None:
        try:
            for q in queries:
                res = await _maybe_await(col.update_one(q, {"$set": update_fields}))
                if getattr(res, "matched_count", 0) > 0:
                    updated = await _maybe_await(col.find_one(q))
                    if updated:
                        return updated
        except Exception:
            pass

    raw_str = str(issue_id)
    for item in _FALLBACK_ISSUES_STORE:
        if str(item.get("_id")) == raw_str or str(item.get("id")) == raw_str:
            item.update(update_fields)
            return dict(item)
    return None


async def _find_issue_by_id_raw(issue_id: str) -> Optional[Dict[str, Any]]:
    col = _resolve_db_collection()
    queries = []
    if ObjectId.is_valid(str(issue_id)):
        queries.append({"_id": ObjectId(str(issue_id))})
    queries.append({"_id": str(issue_id)})
    queries.append({"id": str(issue_id)})

    if col is not None:
        try:
            for q in queries:
                doc = await _maybe_await(col.find_one(q))
                if doc:
                    return doc
        except Exception:
            pass

    for item in _FALLBACK_ISSUES_STORE:
        if str(item.get("_id")) == str(issue_id) or str(item.get("id")) == str(issue_id):
            return dict(item)
    return None


def serialize_issue(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensures MongoDB `_id` is converted to string for both `id` and `_id` so neither
    FastAPI JSON serialization nor the React frontend ever crashes.
    """
    if not doc:
        return {}

    serialized = dict(doc)
    raw_id = serialized.get("_id") or serialized.get("id") or str(ObjectId())
    str_id = str(raw_id)
    serialized["id"] = str_id
    serialized["_id"] = str_id

    coords = extract_lat_lng(serialized)
    lat = coords[0] if coords else 18.5204
    lng = coords[1] if coords else 73.8567
    loc_obj = serialized.get("location") if isinstance(serialized.get("location"), dict) else {}
    address = loc_obj.get("address") or serialized.get("address") or "Pune, Maharashtra"

    serialized["location"] = {
        "lat": lat,
        "lng": lng,
        "address": address,
    }

    category = serialized.get("category") or "Pothole"
    report_count = int(serialized.get("report_count", 1) or 1)
    severity = int(serialized.get("severity", 3) or 3)
    created_at = serialized.get("created_at") or datetime.now(timezone.utc).isoformat()
    status = str(serialized.get("status") or "YET_TO_START").upper()

    serialized["category"] = category
    serialized["report_count"] = report_count
    serialized["severity"] = severity
    serialized["status"] = status
    serialized["created_at"] = str(created_at)
    serialized["assigned_team"] = serialized.get("assigned_team") or get_default_team(category)
    serialized["before_image"] = serialized.get("before_image")
    serialized["after_image"] = serialized.get("after_image")
    serialized["duplicate_of"] = (
        str(serialized["duplicate_of"]) if serialized.get("duplicate_of") else None
    )
    serialized["resolved_at"] = serialized.get("resolved_at")
    serialized["resolution_notes"] = serialized.get("resolution_notes")

    serialized["priority_score"] = calculate_priority_score(
        category=category,
        report_count=report_count,
        severity=severity,
        created_at_iso=created_at,
    )
    return serialized


async def _create_or_merge_issue(payload: IssueCreate) -> Dict[str, Any]:
    norm_loc = payload.get_normalized_location()
    lat = norm_loc["lat"]
    lng = norm_loc["lng"]
    category = (payload.category or "Pothole").strip()

    existing_issues = await _fetch_all_issues_raw()
    duplicate = find_nearby_duplicate(
        existing_issues=existing_issues,
        lat=lat,
        lng=lng,
        category=category,
        radius_meters=50.0,
    )

    if duplicate is not None:
        dup_id = duplicate.get("_id") or duplicate.get("id")
        new_report_count = int(duplicate.get("report_count", 1) or 1) + 1
        merged_severity = max(
            int(duplicate.get("severity", 3) or 3),
            int(payload.severity or 3),
        )
        created_at = duplicate.get("created_at") or datetime.now(timezone.utc).isoformat()
        new_priority = calculate_priority_score(
            category=duplicate.get("category", category),
            report_count=new_report_count,
            severity=merged_severity,
            created_at_iso=created_at,
        )

        update_fields: Dict[str, Any] = {
            "report_count": new_report_count,
            "severity": merged_severity,
            "priority_score": new_priority,
        }
        if not duplicate.get("before_image") and payload.get_before_image():
            update_fields["before_image"] = payload.get_before_image()

        updated_doc = await _update_issue_raw(dup_id, update_fields)
        if updated_doc is None:
            duplicate.update(update_fields)
            updated_doc = duplicate

        serialized_dup = serialize_issue(updated_doc)
        return {
            "is_duplicate": True,
            "message": "This issue was already reported! We boosted its priority score.",
            "issue": serialized_dup,
            "existing_issue": serialized_dup,
        }

    now_iso = datetime.now(timezone.utc).isoformat()
    initial_priority = calculate_priority_score(
        category=category,
        report_count=1,
        severity=payload.severity,
        created_at_iso=now_iso,
    )

    new_doc: Dict[str, Any] = {
        "title": payload.title.strip() if payload.title else f"{category} issue reported",
        "description": (payload.description or "").strip(),
        "category": category,
        "severity": int(payload.severity or 3),
        "location": norm_loc,
        "before_image": payload.get_before_image(),
        "after_image": None,
        "status": "YET_TO_START",
        "assigned_team": payload.assigned_team or get_default_team(category),
        "report_count": 1,
        "duplicate_of": None,
        "priority_score": initial_priority,
        "created_at": now_iso,
        "resolved_at": None,
        "resolution_notes": None,
    }

    inserted_doc = await _insert_issue_raw(new_doc)
    serialized_new = serialize_issue(inserted_doc)
    return {
        "is_duplicate": False,
        "message": "Civic issue reported successfully.",
        "issue": serialized_new,
        "existing_issue": None,
    }


async def _list_issues(
    category: Optional[str] = None,
    status: Optional[str] = None,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    radius_km: Optional[float] = None,
) -> List[Dict[str, Any]]:
    raw_issues = await _fetch_all_issues_raw()
    results: List[Dict[str, Any]] = []

    for doc in raw_issues:
        item = serialize_issue(doc)

        if category and category.strip().lower() not in ("all", ""):
            if item["category"].strip().lower() != category.strip().lower():
                continue

        if status and status.strip().upper() not in ("ALL", ""):
            if item["status"].strip().upper() != status.strip().upper():
                continue

        if lat is not None and lng is not None:
            loc = item["location"]
            dist_m = haversine_distance_meters(lat, lng, loc["lat"], loc["lng"])
            item["distance_meters"] = dist_m
            if radius_km is not None and dist_m > float(radius_km) * 1000.0:
                continue

        results.append(item)

    results.sort(key=lambda x: x.get("priority_score", 0.0), reverse=True)
    return results


async def _upvote_issue_by_id(issue_id: str) -> Dict[str, Any]:
    existing = await _find_issue_by_id_raw(issue_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Issue '{issue_id}' not found")

    new_count = int(existing.get("report_count", 1) or 1) + 1
    new_score = calculate_priority_score(
        category=existing.get("category", "Pothole"),
        report_count=new_count,
        severity=int(existing.get("severity", 3) or 3),
        created_at_iso=existing.get("created_at"),
    )

    update_fields = {
        "report_count": new_count,
        "priority_score": new_score,
    }
    updated = await _update_issue_raw(existing.get("_id") or issue_id, update_fields)
    if updated is None:
        existing.update(update_fields)
        updated = existing

    serialized = serialize_issue(updated)
    return {
        **serialized,
        "message": "Issue upvoted and priority score recalculated.",
        "issue": serialized,
    }


# Primary routes (/api/issues...) + prefix-safe aliases (/issues...) so it works regardless of main.py prefix setup
@router.post("/api/issues")
@router.post("/issues", include_in_schema=False)
async def create_issue(payload: IssueCreate):
    return await _create_or_merge_issue(payload)


@router.get("/api/issues")
@router.get("/issues", include_in_schema=False)
async def get_issues(
    category: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    lat: Optional[float] = Query(default=None),
    lng: Optional[float] = Query(default=None),
    radius_km: Optional[float] = Query(default=None),
):
    return await _list_issues(
        category=category,
        status=status,
        lat=lat,
        lng=lng,
        radius_km=radius_km,
    )


@router.get("/api/issues/nearby")
@router.get("/issues/nearby", include_in_schema=False)
async def get_nearby_issues(
    lat: float = Query(default=18.5204),
    lng: float = Query(default=73.8567),
    radius_km: float = Query(default=5.0),
    category: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
):
    return await _list_issues(
        category=category,
        status=status,
        lat=lat,
        lng=lng,
        radius_km=radius_km,
    )


@router.post("/api/issues/{issue_id}/upvote")
@router.post("/issues/{issue_id}/upvote", include_in_schema=False)
async def upvote_issue(issue_id: str):
    return await _upvote_issue_by_id(issue_id)