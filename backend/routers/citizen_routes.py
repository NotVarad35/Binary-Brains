"""Dev 1 — Citizen-facing routes: submit issue, get nearby issues, upvote.

The paths, methods and payloads below are the agreed API contract with
Dev 3 (frontend citizen pages). Implement the TODO bodies; do not rename
endpoints or change response models.

Mounted by main.py under the router's own prefix (`/api/citizen`).
"""

from typing import List

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from models import (
    IssueCreate,
    IssueOut,
    NearbyIssuesResponse,
    UpvoteRequest,
)

router = APIRouter(prefix="/api/citizen", tags=["citizen"])


@router.post("/issues", response_model=IssueOut, status_code=201)
async def submit_issue(
    # NOTE: the frontend sends multipart/form-data so the photo uploads alongside
    # the fields. Field parts are the IssueCreate attributes as plain strings.
    title: str,
    description: str,
    category: str,
    latitude: float,
    longitude: float,
    reporter_id: str,
    photo: UploadFile | None = File(None),
):
    """Citizen submits a new issue.

    TODO(Dev 1):
        1. Validate/convert the form fields (optionally re-parse into
           `IssueCreate` for full schema validation).
        2. Save `photo` to `backend/uploads/` and build `photo_url`.
        3. Run `priority_engine.find_duplicates()` — if a match is found,
           either (a) reject with a 409 and return the existing issue, or
           (b) store `duplicate_of` pointing at the original. Pick one and
           document it in the README.
        4. Compute `priority` via `priority_engine.calculate_priority()`.
        5. Insert into `database.get_issues_collection()` with
           `location: {"type": "Point", "coordinates": [lon, lat]}`,
           `status: Status.YET_TO_START`, `upvotes: 0`,
           `created_at`/`updated_at` = now.
        6. Return the created issue.

    Raises:
        409: duplicate found (if you choose the reject strategy).
    """
    raise NotImplementedError("TODO(Dev 1): implement submit_issue()")


@router.get("/issues/nearby", response_model=NearbyIssuesResponse)
async def get_nearby_issues(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    radius_m: float = Query(100.0, gt=0, le=10_000, description="Search radius in metres"),
):
    """Issues near a point, plus flagged duplicates for the report form.

    TODO(Dev 1):
        1. Query `get_issues_collection()` with `$near` (or `$geoWithin`
           + `$centerSphere`) around `[lon, lat]`.
        2. Build `issues` (all matches in radius) and `duplicates` (the
           subset close enough to count as the same problem — typically
           within ~20-40m AND same category).
        3. Return `NearbyIssuesResponse` with the radius you used.

    Powers the MapPicker "view nearby" layer and the ReportIssue duplicate
    alert.
    """
    raise NotImplementedError("TODO(Dev 1): implement get_nearby_issues()")


@router.get("/issues/mine", response_model=List[IssueOut])
async def get_my_issues(
    reporter_id: str = Query(..., min_length=1, description="Citizen's stable ID"),
):
    """All issues one citizen has reported, newest first.

    TODO(Dev 1): sort by `created_at` descending and return a plain list.

    Powers the "Track reports" list on CitizenDashboard.
    """
    raise NotImplementedError("TODO(Dev 1): implement get_my_issues()")


@router.post("/issues/{issue_id}/upvote", response_model=IssueOut)
async def upvote_issue(issue_id: str, payload: UpvoteRequest):
    """Increment an issue's upvote count.

    TODO(Dev 1):
        1. Locate the issue by `_id` (`ObjectId(issue_id)`); 404 if missing
           or if the id is not a valid ObjectId.
        2. Guard against double-voting — e.g. keep a `voters: [...]` array on
           the issue and use `$addToSet`, returning 400 if already present.
        3. `$inc: {"upvotes": 1}` and bump `updated_at`.
        4. Optionally recompute `priority` since it depends on upvotes.
        5. Return the updated issue.

    Raises:
        404: issue not found.
        400: reporter already upvoted (if you add that guard).
    """
    raise NotImplementedError("TODO(Dev 1): implement upvote_issue()")
