from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class LocationModel(BaseModel):
    lat: float = Field(default=18.5204, description="Latitude coordinate")
    lng: float = Field(default=73.8567, description="Longitude coordinate")
    address: Optional[str] = Field(default="Pune, Maharashtra", description="Human-readable address")


class IssueCreate(BaseModel):
    title: str = Field(default="Civic Issue Report", min_length=1)
    description: Optional[str] = Field(default="")
    category: str = Field(default="Pothole")
    severity: int = Field(default=3, ge=1, le=5)
    location: Optional[LocationModel] = None
    # Flat fallback fields so frontend works whether it sends nested `location` or flat `lat`/`lng`
    lat: Optional[float] = None
    lng: Optional[float] = None
    address: Optional[str] = None
    before_image: Optional[str] = None
    image: Optional[str] = None
    assigned_team: Optional[str] = None

    def get_normalized_location(self) -> Dict[str, Any]:
        if self.location is not None:
            return {
                "lat": float(self.location.lat),
                "lng": float(self.location.lng),
                "address": self.location.address or self.address or "Pune, Maharashtra",
            }
        return {
            "lat": float(self.lat) if self.lat is not None else 18.5204,
            "lng": float(self.lng) if self.lng is not None else 73.8567,
            "address": self.address or "Pune, Maharashtra",
        }

    def get_before_image(self) -> Optional[str]:
        return self.before_image or self.image


class IssueUpdate(BaseModel):
    status: Optional[str] = None
    assigned_team: Optional[str] = None
    after_image: Optional[str] = None
    resolution_notes: Optional[str] = None


class IssueResponse(BaseModel):
    id: str
    _id: Optional[str] = None
    title: str
    description: Optional[str] = ""
    category: str
    severity: int = 3
    location: LocationModel
    before_image: Optional[str] = None
    after_image: Optional[str] = None
    status: str = "YET_TO_START"
    assigned_team: Optional[str] = "Unassigned"
    report_count: int = 1
    duplicate_of: Optional[str] = None
    priority_score: float = 0.0
    created_at: str = Field(default_factory=utc_now_iso)
    resolved_at: Optional[str] = None
    resolution_notes: Optional[str] = None


class IssueSubmitResponse(BaseModel):
    is_duplicate: bool
    message: str
    issue: Dict[str, Any]
    existing_issue: Optional[Dict[str, Any]] = None