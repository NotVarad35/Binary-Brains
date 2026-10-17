"""Dev 1 — Citizen-facing routes: submit issue, get nearby issues, upvote.

The paths, methods and payloads below are the agreed API contract with
Dev 3 (frontend citizen pages). Do not rename endpoints or change response
models.

Mounted by main.py under the router's own prefix (`/api/citizen`).

Duplicate strategy (documented in the README): a report that matches an
existing same-category issue within `DUPLICATE_RADIUS_M` is still stored, but
gets `duplicate_of` pointing at the original. The original is boosted (its
upvotes are incremented and its priority recalculated) so the community's
demand lands on a single card instead of two.
"""

import base64
from datetime import datetime, timezone
from typing import List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from pydantic import ValidationError

# Works whether the app is run as `uvicorn main:app` from backend/ or imported
# as the `backend` package (same pattern as admin_routes.py).
try:
    from backend.database import get_issues_collection
    from backend.models import (
        IssueCreate,
        IssueOut,
        NearbyIssuesResponse,
        UpvoteRequest,
    )
    from backend.services import priority_engine
except ImportError:
    from database import get_issues_collection
    from models import (
        IssueCreate,
        IssueOut,
        NearbyIssuesResponse,
        UpvoteRequest,
    )
    from services import priority_engine


router = APIRouter(prefix="/api/citizen", tags=["citizen"])

# Two same-category reports inside this radius are the same problem.
DUPLICATE_RADIUS_M = 40.0

# Photos are stored inline as Base64 data URLs (see the README): the app has no
# S3 bucket, and main.py is locked so there is no static /uploads mount.
MAX_PHOTO_BYTES = 3 * 1024 * 1024


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------
# Dev 2's admin routes emit "YET_TO_START" / "WORKING" / "DONE" while
# models.py (and the frontend) use "Yet to Start" / "Working" / "Done".
# Normalise on the way out so an admin-updated issue can never 500 the citizen
# endpoints. Same idea for the handful of legacy category labels.

_STATUS_ALIASES = {
    "yet_to_start": "Yet to Start",
    "yet to start": "Yet to Start",
    "pending": "Yet to Start",
    "open": "Yet to Start",
    "new": "Yet to Start",
    "todo": "Yet to Start",
    "to_do": "Yet to Start",
    "not_started": "Yet to Start",
    "working": "Working",
    "in_progress": "Working",
    "inprogress": "Working",
    "in progress": "Working",
    "ongoing": "Working",
    "assigned": "Working",
    "done": "Done",
    "resolved": "Done",
    "closed": "Done",
    "complete": "Done",
    "completed": "Done",
}

_CATEGORY_ALIASES = {
    "pothole": "Pothole",
    "potholes": "Pothole",
    "street light": "Street Light",
    "streetlight": "Street Light",
    "broken streetlight": "Street Light",
    "street light broken": "Street Light",
    "garbage": "Garbage",
    "overflowing garbage": "Garbage",
    "trash": "Garbage",
    "graffiti": "Graffiti",
    "water logging": "Water Logging",
    "water leak": "Water Logging",
    "waterlogging": "Water Logging",
    "broken road": "Broken Road",
    "road": "Broken Road",
    "sewage": "Sewage",
    "sewer": "Sewage",
    "other": "Other",
}


def _normalize_status(value) -> str:
    """Map any status label the DB may hold onto a `models.Status` value."""
    raw = getattr(value, "value", value)
    key = str(raw or "").strip().lower()
    return _STATUS_ALIASES.get(key, _STATUS_ALIASES.get(key.replace(" ", "_"), "Yet to Start"))


def _normalize_category(value) -> str:
    """Map a category label onto a `models.Category` value."""
    raw = getattr(value, "value", value)
    key = str(raw or "").strip().lower()
    return _CATEGORY_ALIASES.get(key, "Other")


def _age_hours(doc: dict, now: datetime) -> float:
    """Hours between an issue's `created_at` and `now` (0 if unknown)."""
    created = doc.get("created_at")
    if not isinstance(created, datetime):
        return 0.0
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return max(0.0, (now - created).total_seconds() / 3600.0)


def _coords_of(doc: dict) -> tuple:
    """Return (lat, lon) for a stored issue, whatever shape it was stored in."""
    lat, lon = doc.get("latitude"), doc.get("longitude")
    location = doc.get("location") or {}
    coords = location.get("coordinates") or []
    if lat is None and len(coords) == 2:
        lon, lat = coords[0], coords[1]
    return float(lat or 0.0), float(lon or 0.0)


def _serialize(doc: dict) -> IssueOut:
    """Convert a Mongo document into the `IssueOut` response model."""
    lat, lon = _coords_of(doc)
    duplicate_of = doc.get("duplicate_of")
    return IssueOut(
        id=str(doc.get("_id") or doc.get("id") or ""),
        title=doc.get("title", ""),
        description=doc.get("description") or "",
        category=_normalize_category(doc.get("category")),
        status=_normalize_status(doc.get("status")),
        priority=int(doc.get("priority") or doc.get("priority_score") or 0),
        upvotes=int(doc.get("upvotes") or doc.get("report_count") or 0),
        latitude=lat,
        longitude=lon,
        photo_url=doc.get("photo_url"),
        worker_photo_url=doc.get("worker_photo_url") or doc.get("after_image"),
        reporter_id=str(doc.get("reporter_id") or ""),
        duplicate_of=str(duplicate_of) if duplicate_of else None,
        created_at=doc.get("created_at") or datetime.now(timezone.utc),
        updated_at=doc.get("updated_at") or doc.get("created_at") or datetime.now(timezone.utc),
        resolved_at=doc.get("resolved_at"),
    )


async def _photo_to_data_url(photo: Optional[UploadFile]) -> Optional[str]:
    """Inline a multipart upload as a Base64 data URL (no bucket, no mount)."""
    if photo is None:
        return None
    raw = await photo.read()
    if not raw:
        return None
    if len(raw) > MAX_PHOTO_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Photo is too large — it is compressed in the browser, so this should not happen.",
        )
    content_type = photo.content_type or "image/jpeg"
    return f"data:{content_type};base64,{base64.b64encode(raw).decode('ascii')}"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/issues", response_model=IssueOut, status_code=201)
async def submit_issue(
    # NOTE: the frontend sends multipart/form-data so the photo uploads alongside
    # the fields. Field parts are the IssueCreate attributes as plain strings.
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    reporter_id: str = Form(...),
    photo: UploadFile | None = File(None),
):
    """Citizen submits a new issue.

    Validates the form fields through `IssueCreate`, inlines any photo, runs the
    duplicate check, computes the priority and inserts the document. A match
    within `DUPLICATE_RADIUS_M` is stored with `duplicate_of` set and the
    original issue is boosted instead of losing the report.

    Raises:
        422: the form fields do not satisfy the shared schema.
    """
    try:
        payload = IssueCreate(
            title=title,
            description=description,
            category=category,
            latitude=latitude,
            longitude=longitude,
            reporter_id=reporter_id,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors())

    collection = get_issues_collection()
    now = datetime.now(timezone.utc)
    category_value = getattr(payload.category, "value", str(payload.category))

    photo_url = await _photo_to_data_url(photo)

    matches = await priority_engine.find_duplicates(
        collection,
        payload.latitude,
        payload.longitude,
        radius_m=DUPLICATE_RADIUS_M,
        category=category_value,
    )
    original = matches[0] if matches else None
    priority = priority_engine.calculate_priority(
        category_value,
        upvotes=0,
        age_hours=0.0,
        has_worker_photo=False,
        is_duplicate=original is not None,
    )

    document = {
        "title": payload.title,
        "description": payload.description,
        "category": category_value,
        "status": "Yet to Start",
        "priority": priority,
        "upvotes": 0,
        "location": {"type": "Point", "coordinates": [payload.longitude, payload.latitude]},
        "latitude": payload.latitude,
        "longitude": payload.longitude,
        "photo_url": photo_url,
        "worker_photo_url": None,
        "reporter_id": payload.reporter_id,
        "duplicate_of": original["_id"] if original else None,
        "voters": [],
        "created_at": now,
        "updated_at": now,
        "resolved_at": None,
    }

    inserted = await collection.insert_one(document)

    if original is not None:
        boosted_upvotes = int(original.get("upvotes") or 0) + 1
        boosted_priority = priority_engine.calculate_priority(
            original.get("category"),
            upvotes=boosted_upvotes,
            age_hours=_age_hours(original, now),
            has_worker_photo=bool(original.get("worker_photo_url")),
        )
        await collection.update_one(
            {"_id": original["_id"]},
            {
                "$set": {
                    "upvotes": boosted_upvotes,
                    "priority": boosted_priority,
                    "updated_at": now,
                }
            },
        )

    return _serialize({**document, "_id": inserted.inserted_id})


@router.get("/issues/nearby", response_model=NearbyIssuesResponse)
async def get_nearby_issues(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    radius_m: float = Query(100.0, gt=0, le=10_000, description="Search radius in metres"),
):
    """Issues near a point, plus flagged duplicates for the report form.

    `issues` is everything inside `radius_m` (nearest first). `duplicates` is the
    subset within `DUPLICATE_RADIUS_M`, i.e. what the submit endpoint would treat
    as the same problem.

    Powers the MapPicker "view nearby" layer and the ReportIssue duplicate alert.
    """
    collection = get_issues_collection()
    found = await priority_engine.find_duplicates(collection, lat, lon, radius_m=radius_m)

    issues = [_serialize(doc) for doc in found]

    # Same problem = close enough to be the very same pothole/leak.
    duplicates = []
    for doc in found:
        doc_lat, doc_lon = _coords_of(doc)
        distance = priority_engine.haversine_distance(lat, lon, doc_lat, doc_lon)
        if distance <= DUPLICATE_RADIUS_M:
            duplicates.append((distance, doc))
    duplicates.sort(key=lambda pair: pair[0])
    duplicate_issues = [_serialize(doc) for _, doc in duplicates]

    return NearbyIssuesResponse(
        issues=issues,
        duplicates=duplicate_issues,
        duplicate_radius_m=DUPLICATE_RADIUS_M,
    )


@router.get("/issues/mine", response_model=List[IssueOut])
async def get_my_issues(
    reporter_id: str = Query(..., min_length=1, description="Citizen's stable ID"),
):
    """All issues one citizen has reported, newest first.

    Powers the "Track reports" list on CitizenDashboard.
    """
    collection = get_issues_collection()
    cursor = collection.find({"reporter_id": reporter_id}).sort("created_at", -1)
    documents = await cursor.to_list(length=None)
    return [_serialize(doc) for doc in documents]


@router.post("/issues/{issue_id}/upvote", response_model=IssueOut)
async def upvote_issue(issue_id: str, payload: UpvoteRequest):
    """Increment an issue's upvote count.

    One upvote per `reporter_id`: the id is added to a `voters` array with
    `$addToSet`, and a repeat vote is rejected so the leaderboard stays honest.
    The priority is recalculated because it depends on the upvote count.

    Raises:
        404: issue not found.
        400: reporter already upvoted.
    """
    try:
        object_id = ObjectId(issue_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=404, detail="Issue not found.")

    collection = get_issues_collection()
    document = await collection.find_one({"_id": object_id})
    if document is None:
        raise HTTPException(status_code=404, detail="Issue not found.")

    if payload.reporter_id in (document.get("voters") or []):
        raise HTTPException(status_code=400, detail="You have already upvoted this issue.")

    now = datetime.now(timezone.utc)
    upvotes = int(document.get("upvotes") or 0) + 1
    priority = priority_engine.calculate_priority(
        document.get("category"),
        upvotes=upvotes,
        age_hours=_age_hours(document, now),
        has_worker_photo=bool(document.get("worker_photo_url")),
        is_duplicate=bool(document.get("duplicate_of")),
    )

    await collection.update_one(
        {"_id": object_id},
        {
            "$addToSet": {"voters": payload.reporter_id},
            "$set": {"upvotes": upvotes, "priority": priority, "updated_at": now},
        },
    )

    return _serialize({**document, "upvotes": upvotes, "priority": priority, "updated_at": now})
