"""Pydantic schemas for validation.

LOCKED shared file — these are the single source of truth for the API
contract. Dev 1 (citizen) and Dev 2 (admin) both read/write these shapes,
and the frontend mirrors them. Add to this file rather than defining
ad-hoc dicts elsewhere.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums — keep these in sync with the frontend labels the UI renders.
# ---------------------------------------------------------------------------

class Status(str, Enum):
    """Kanban column the issue lives in."""

    YET_TO_START = "Yet to Start"
    WORKING = "Working"
    DONE = "Done"


class Category(str, Enum):
    """Issue categories a citizen can pick when reporting."""

    POTHOLES = "Pothole"
    STREET_LIGHT = "Street Light"
    GARBAGE = "Garbage"
    GRAFFITI = "Graffiti"
    WATER_LOGGING = "Water Logging"
    BROKEN_ROAD = "Broken Road"
    SEWAGE = "Sewage"
    OTHER = "Other"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Issue schemas
# ---------------------------------------------------------------------------

class GeoPoint(BaseModel):
    """WGS-84 point. Mongo stores this as {type:"Point", coordinates:[lon,lat]}."""

    type: str = "Point"
    coordinates: List[float]  # [longitude, latitude]

    @field_validator("coordinates")
    @classmethod
    def _check_pair(cls, v: List[float]) -> List[float]:
        if len(v) != 2:
            raise ValueError("coordinates must be [longitude, latitude]")
        return v


class IssueCreate(BaseModel):
    """Payload a citizen submits via POST /api/citizen/issues.

    Photo is sent as multipart alongside these fields, so `photo_url` is
    filled in by the route handler, not by the client.
    """

    title: str = Field(..., min_length=3, max_length=120)
    description: str = Field(..., max_length=1000)
    category: Category
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    reporter_id: str = Field(..., min_length=1, max_length=64)


class IssueUpdate(BaseModel):
    """Admin patches a status. Also accepts worker proof + priority."""

    status: Optional[Status] = None
    worker_photo_url: Optional[str] = None
    priority: Optional[int] = Field(None, ge=0, le=100)


class IssueOut(BaseModel):
    """Issue as returned to the frontend. `_id` is stringified for convenience."""

    id: str
    title: str
    description: str
    category: Category
    status: Status
    priority: int = 0
    upvotes: int = 0
    latitude: float
    longitude: float
    photo_url: Optional[str] = None
    worker_photo_url: Optional[str] = None
    reporter_id: str
    duplicate_of: Optional[str] = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    resolved_at: Optional[datetime] = None

    @field_validator("id", mode="before")
    @classmethod
    def _stringify_id(cls, v):
        return str(v)


# ---------------------------------------------------------------------------
# Request / response envelopes for specific endpoints
# ---------------------------------------------------------------------------

class NearbyIssuesResponse(BaseModel):
    """GET /api/citizen/issues/nearby.

    `duplicates` lets the report form show a "this may already be reported"
    alert before the citizen submits.
    """

    issues: List[IssueOut] = []
    duplicates: List[IssueOut] = []
    duplicate_radius_m: float


class UpvoteRequest(BaseModel):
    """POST /api/citizen/issues/{id}/upvote."""

    reporter_id: str = Field(..., min_length=1, max_length=64)


class StatusUpdateRequest(BaseModel):
    """PATCH /api/admin/issues/{id}/status."""

    status: Status


class PhotoUploadResponse(BaseModel):
    """POST /api/admin/issues/{id}/photo (and citizen issue photo upload)."""

    photo_url: str


class ResolutionStats(BaseModel):
    """GET /api/admin/analytics — headline numbers."""

    total_issues: int = 0
    yet_to_start: int = 0
    working: int = 0
    done: int = 0
    resolution_rate: float = 0.0
    avg_resolution_hours: Optional[float] = None
    total_upvotes: int = 0


class CategoryBreakdown(BaseModel):
    category: str
    total: int
    done: int


class PriorityLeaderboardEntry(BaseModel):
    id: str
    title: str
    category: str
    priority: int
    upvotes: int
    status: str

    @field_validator("id", mode="before")
    @classmethod
    def _stringify_id(cls, v):
        return str(v)


class AnalyticsResponse(BaseModel):
    """GET /api/admin/analytics — full payload for the AnalyticsPage charts."""

    stats: ResolutionStats
    category_breakdown: List[CategoryBreakdown] = []
    priority_leaderboard: List[PriorityLeaderboardEntry] = []
    daily_created: List[dict] = []
    daily_resolved: List[dict] = []
