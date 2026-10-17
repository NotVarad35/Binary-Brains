"""Dev 2 — Admin routes: Kanban status update, worker photo upload, analytics.

The paths, methods and payloads below are the agreed API contract with
Dev 4 (frontend AdminKanban + AnalyticsPage). Implement the TODO bodies;
do not rename endpoints or change response models.

Mounted by main.py under the router's own prefix (`/api/admin`).
"""

from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile
from models import (
    AnalyticsResponse,
    IssueOut,
    PhotoUploadResponse,
    StatusUpdateRequest,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/issues", response_model=List[IssueOut])
async def list_all_issues():
    """Every issue, for rendering the Kanban board.

    TODO(Dev 2): return all docs from `get_issues_collection()`, sorted by
    `priority` desc then `created_at` desc. Group client-side by `status`
    into the three columns — the frontend does that, not the API.

    This endpoint is not in the original brief, but AdminKanban needs a
    list view and the column grouping is cheaper to do in React.
    """
    raise NotImplementedError("TODO(Dev 2): implement list_all_issues()")


@router.patch("/issues/{issue_id}/status", response_model=IssueOut)
async def update_status(issue_id: str, payload: StatusUpdateRequest):
    """Move an issue between Yet to Start / Working / Done.

    TODO(Dev 2):
        1. Validate `_id` (404 if not found or invalid ObjectId).
        2. Update `status`, bump `updated_at`.
        3. When status becomes `Status.DONE`, set `resolved_at = now` —
           AnalyticsPage computes avg resolution time off this field.
        4. When a DONE issue is reopened, clear `resolved_at` back to None.
        5. Return the updated issue.

    Raises:
        404: issue not found.
    """
    raise NotImplementedError("TODO(Dev 2): implement update_status()")


@router.post("/issues/{issue_id}/photo", response_model=PhotoUploadResponse)
async def upload_worker_proof(issue_id: str, photo: UploadFile = File(...)):
    """Upload the worker's "before/after" proof photo for an issue.

    TODO(Dev 2):
        1. Validate `_id` (404 if not found).
        2. Validate content type is an image (`image/jpeg`, `image/png`,
           `image/webp`) — reject others with 400.
        3. Save to `backend/uploads/` under a unique filename (include the
           issue id + timestamp to avoid collisions).
        4. Store `worker_photo_url` on the issue and bump `updated_at`.
        5. Return `PhotoUploadResponse(photo_url=...)`.

    Raises:
        404: issue not found.
        400: unsupported file type.
    """
    raise NotImplementedError("TODO(Dev 2): implement upload_worker_proof()")


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics():
    """Aggregate stats powering every chart on AnalyticsPage.

    TODO(Dev 2): build an `AnalyticsResponse` containing:
        - `stats`: total / per-status counts, `resolution_rate` =
          done / total (0.0-1.0, guard division by zero), `avg_resolution_hours`
          = mean of (`resolved_at - created_at`) over DONE issues,
          `total_upvotes` sum.
        - `category_breakdown`: per-category total + done counts (pie/bar chart).
        - `priority_leaderboard`: top ~10 issues by `priority` desc
          (recharts bar chart on the AnalyticsPage).
        - `daily_created` / `daily_resolved`: `{"date": "YYYY-MM-DD",
          "count": n}` buckets for the last 14 days — use an aggregation
          pipeline with `$dateToString`, and zero-fill missing days so the
          line chart doesn't have gaps.

    Use `collection.aggregate(...)` rather than loading every doc into Python.
    """
    raise NotImplementedError("TODO(Dev 2): implement get_analytics()")
