"""Dev 3 — Demo seed data for Civic-Fix (Binary Brains).

Populates the `issues` collection with 10 realistic, hand-written civic
complaints around Pune so the Kanban board and Analytics page look alive the
moment the app boots (or right before recording the demo video).

The documents produced here match `models.IssueOut` / the README "API
contract" exactly:

    priority   -> int 0-100   (matches priority_engine.PRIORITY_MAX)
    status     -> "Yet to Start" | "Working" | "Done"   (models.Status)
    category   -> one of models.Category
    location   -> {"type": "Point", "coordinates": [lng, lat]}

Images (`photo_url` / `worker_photo_url`) are intentionally left as `None`.
The demo uploads real photos live, and leaving them empty guarantees no
broken-image tiles during the presentation.

Usage — CLI (works from any working directory):

    python backend/seed_data.py           # seed only if the collection is empty
    python backend/seed_data.py --force   # wipe existing issues, then reseed

Usage — programmatic:

    from seed_data import seed_demo_issues
    result = await seed_demo_issues(force=True)

Usage — live API (server running):

    curl -X POST "http://localhost:8000/api/seed?force=true"

Atlas note: make sure your IP is in the cluster's Network Access list and
`MONGO_URI` is set in `backend/.env` (copy `.env.example`).
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

# Allow `python backend/seed_data.py` (or `python seed_data.py`) from any cwd by
# putting this file's directory on the import path before importing `database`.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bson import ObjectId  # noqa: E402  (provided by pymongo, a dependency)
from database import (  # noqa: E402
    close_client,
    get_database,
    get_issues_collection,
)

# reporter_id baked into every seeded issue, so the data is trivial to spot or
# delete (e.g. `db.issues.deleteMany({reporter_id: /^seed-citizen-/})`).
SEED_REPORTER_PREFIX = "seed-citizen-"


# ---------------------------------------------------------------------------
# The dataset
# ---------------------------------------------------------------------------
# `lat`/`lng` are plain numbers; `_build_documents()` derives the GeoJSON
# `location` as [lng, lat] so the two representations can never drift apart.
# Timestamps are relative to "now" so the analytics charts always look recent.
DEMO_ISSUES: List[Dict[str, Any]] = [
    {
        "key": "fc-road-pothole",
        "title": "Deep pothole outside Vaishali on FC Road",
        "description": (
            "A knee-deep pothole has opened up in the left lane right outside "
            "Vaishali. Two-wheelers swerve into oncoming traffic to avoid it, "
            "and it fills with water after every shower."
        ),
        "category": "Pothole",
        "status": "Yet to Start",
        "priority": 88,
        "upvotes": 14,
        "lat": 18.52360,
        "lng": 73.84780,
        "created_hours_ago": 30,
    },
    {
        # ~23 m from the issue above -> demonstrates duplicate detection.
        "key": "fc-road-pothole-dupe",
        "title": "Pothole near Vaishali, FC Road (possible duplicate)",
        "description": (
            "Reported the pothole outside Vaishali before realising someone "
            "had already pinned it a few metres away."
        ),
        "category": "Pothole",
        "status": "Yet to Start",
        "priority": 28,
        "upvotes": 2,
        "lat": 18.52375,
        "lng": 73.84795,
        "created_hours_ago": 6,
        "duplicate_of_key": "fc-road-pothole",
    },
    {
        "key": "kothrud-water-leak",
        "title": "Burst water pipeline flooding Paud Road, Kothrud",
        "description": (
            "A main pipeline has been leaking for three days near the Kothrud "
            "depot. Water is pooling across the footpath and the road surface "
            "is starting to sink."
        ),
        "category": "Water Logging",
        "status": "Working",
        "priority": 74,
        "upvotes": 9,
        "lat": 18.50740,
        "lng": 73.80770,
        "created_hours_ago": 52,
    },
    {
        "key": "viman-nagar-garbage",
        "title": "Overflowing garbage bin near Phoenix Mall gate, Viman Nagar",
        "description": (
            "The community bin behind the mall gate has not been cleared in a "
            "week. Stray dogs are scattering waste across the service road."
        ),
        "category": "Garbage",
        "status": "Done",
        "priority": 71,
        "upvotes": 12,
        "lat": 18.56790,
        "lng": 73.91430,
        "created_hours_ago": 96,
        "resolved_hours_ago": 20,
    },
    {
        "key": "shivajinagar-streetlight",
        "title": "Streetlight dead on JM Road near Balgandharva, Shivajinagar",
        "description": (
            "The streetlight opposite Balgandharva Chowk has been dark for "
            "over a week. The stretch is unsafe for pedestrians after 8 pm."
        ),
        "category": "Street Light",
        "status": "Yet to Start",
        "priority": 52,
        "upvotes": 5,
        "lat": 18.52750,
        "lng": 73.84980,
        "created_hours_ago": 18,
    },
    {
        "key": "hadapsar-sewage",
        "title": "Sewage overflow on the road at Gadital, Hadapsar",
        "description": (
            "A manhole is overflowing and sewage is running along the gutter "
            "for about 100 metres. The smell is unbearable and it is a clear "
            "health hazard for nearby shops."
        ),
        "category": "Sewage",
        "status": "Working",
        "priority": 82,
        "upvotes": 11,
        "lat": 18.50890,
        "lng": 73.92600,
        "created_hours_ago": 70,
    },
    {
        "key": "hinjewadi-broken-road",
        "title": "Cratered stretch on Hinjewadi Phase 1 internal road",
        "description": (
            "Multiple deep craters across the full width of the road near the "
            "Phase 1 gate. Autos and bikes crawl through it and several riders "
            "have already fallen."
        ),
        "category": "Broken Road",
        "status": "Yet to Start",
        "priority": 95,
        "upvotes": 15,
        "lat": 18.59130,
        "lng": 73.73890,
        "created_hours_ago": 120,
    },
    {
        "key": "baner-potholes",
        "title": "Pothole cluster on Baner Road near Balewadi junction",
        "description": (
            "Five or six potholes in a row right at the signal. Repaired by "
            "the ward team after repeated complaints from commuters."
        ),
        "category": "Pothole",
        "status": "Done",
        "priority": 66,
        "upvotes": 8,
        "lat": 18.55900,
        "lng": 73.78680,
        "created_hours_ago": 140,
        "resolved_hours_ago": 30,
    },
    {
        "key": "aundh-water-logging",
        "title": "Water logging at Parihar Chowk, Aundh",
        "description": (
            "A storm drain was blocked, so the junction flooded every evening. "
            "The drain has been cleared and the stretch stayed dry through the "
            "next two spells of rain."
        ),
        "category": "Water Logging",
        "status": "Done",
        "priority": 61,
        "upvotes": 7,
        "lat": 18.55900,
        "lng": 73.80770,
        "created_hours_ago": 110,
        "resolved_hours_ago": 48,
    },
    {
        "key": "katraj-streetlight",
        "title": "Flickering streetlight on Katraj-Kondhwa Road",
        "description": (
            "The pole outside the society gate flickers all night and goes "
            "fully dark for hours at a time. The team has inspected it and "
            "ordered a replacement driver."
        ),
        "category": "Street Light",
        "status": "Working",
        "priority": 44,
        "upvotes": 3,
        "lat": 18.45290,
        "lng": 73.85670,
        "created_hours_ago": 40,
    },
]


# ---------------------------------------------------------------------------
# Document construction (pure — no database access, so it is easy to test)
# ---------------------------------------------------------------------------

def _build_documents(now: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """Turn `DEMO_ISSUES` into ready-to-insert Mongo documents.

    Returns a list of dicts shaped exactly like `models.IssueOut`, each with a
    fresh `ObjectId`. `duplicate_of` is wired in a second pass so a document
    can reference another seeded issue by its `key`.
    """
    now = now or datetime.now(timezone.utc)
    documents: List[Dict[str, Any]] = []
    by_key: Dict[str, Dict[str, Any]] = {}

    for index, spec in enumerate(DEMO_ISSUES, start=1):
        created_at = now - timedelta(hours=spec["created_hours_ago"])

        resolved_hours_ago = spec.get("resolved_hours_ago")
        resolved_at = (
            now - timedelta(hours=resolved_hours_ago)
            if resolved_hours_ago is not None
            else None
        )
        # A resolved issue was last touched when it was closed; anything still
        # open was last touched when it was reported.
        updated_at = resolved_at or created_at

        document = {
            "_id": ObjectId(),
            "title": spec["title"],
            "description": spec["description"],
            "category": spec["category"],
            "status": spec["status"],
            "priority": spec["priority"],
            "upvotes": spec["upvotes"],
            # GeoJSON is [longitude, latitude] — the reverse of lat/lng below.
            "location": {
                "type": "Point",
                "coordinates": [spec["lng"], spec["lat"]],
            },
            "latitude": spec["lat"],
            "longitude": spec["lng"],
            "photo_url": None,
            "worker_photo_url": None,
            "reporter_id": f"{SEED_REPORTER_PREFIX}{index:02d}",
            "duplicate_of": None,
            "created_at": created_at,
            "updated_at": updated_at,
            "resolved_at": resolved_at,
        }

        documents.append(document)
        by_key[spec["key"]] = document

    # Second pass: link duplicates now that every _id exists.
    for spec in DEMO_ISSUES:
        original_key = spec.get("duplicate_of_key")
        if original_key:
            by_key[spec["key"]]["duplicate_of"] = by_key[original_key]["_id"]

    return documents


# ---------------------------------------------------------------------------
# Database seeding
# ---------------------------------------------------------------------------

async def seed_demo_issues(force: bool = False) -> Dict[str, Any]:
    """Insert the demo dataset into the `issues` collection.

    Args:
        force: When True, delete every existing issue first and reseed. When
            False (default), seed only if the collection is currently empty —
            safe to call on every boot.

    Returns:
        A JSON-friendly summary: inserted / deleted counts, whether seeding
        was skipped, and a human-readable message.
    """
    collection = get_issues_collection()
    existing = await collection.count_documents({})

    if existing and not force:
        return {
            "inserted": 0,
            "deleted": 0,
            "skipped": True,
            "existing_count": existing,
            "message": (
                f"Collection already holds {existing} issue(s); "
                f"pass force=True (or ?force=true) to reset and reseed."
            ),
        }

    deleted = 0
    if force and existing:
        deleted = (await collection.delete_many({})).deleted_count

    documents = _build_documents()
    await collection.insert_many(documents)

    message = f"Seeded {len(documents)} demo issues"
    if deleted:
        message += f" (removed {deleted} existing)"
    message += "."

    return {
        "inserted": len(documents),
        "deleted": deleted,
        "skipped": False,
        "existing_count": existing,
        "message": message,
    }


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

async def _run(force: bool) -> Dict[str, Any]:
    """Ping Mongo for a clear error, then seed, then release the connection."""
    try:
        await get_database().command("ping")
    except Exception as exc:  # noqa: BLE001 - surface any connection problem
        raise SystemExit(
            f"[seed] Could not reach MongoDB: {exc}\n"
            f"[seed] Check MONGO_URI in backend/.env and that this machine's IP "
            f"is allowed in the Atlas Network Access list."
        ) from exc

    try:
        return await seed_demo_issues(force=force)
    finally:
        await close_client()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed the Civic-Fix demo dataset into MongoDB.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete existing issues before seeding (default: seed only if empty).",
    )
    args = parser.parse_args()

    result = asyncio.run(_run(args.force))
    print(f"[seed] {result['message']}")


if __name__ == "__main__":
    main()
