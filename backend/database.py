"""MongoDB Atlas connection setup.

LOCKED shared file — every dev consumes this, nobody edits it without
agreeing on the contract first.

Usage:
    from database import get_issues_collection

    collection = get_issues_collection()
    await collection.find_one({"_id": issue_id})
"""

import os
from typing import Optional

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

load_dotenv()

MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "binary_brains")

# Lazily created so importing this module never blocks or throws at
# import time (keeps `uvicorn main:app` boot resilient while dev is running).
_client: Optional[AsyncIOMotorClient] = None


# Fail fast rather than hanging the default 30s when Mongo is unreachable —
# keeps `uvicorn main:app` startup (and error output) responsive.
SERVER_SELECTION_TIMEOUT_MS = int(os.getenv("MONGO_SERVER_SELECTION_TIMEOUT_MS", "3000"))


def get_client() -> AsyncIOMotorClient:
    """Return the singleton motor client, creating it on first use."""
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(
            MONGO_URI,
            serverSelectionTimeoutMS=SERVER_SELECTION_TIMEOUT_MS,
        )
    return _client


def get_database() -> AsyncIOMotorDatabase:
    """Return the database handle for MONGO_DB_NAME."""
    return get_client()[MONGO_DB_NAME]


def get_issues_collection():
    """Return the `issues` collection handle."""
    return get_database()["issues"]


async def ensure_indexes() -> None:
    """Create the indexes the app relies on. Safe to call repeatedly.

    - 2dsphere on `location` powers the $geoNear / $near duplicate checks.
    - Upserts on `reporter_id` keep dashboard lookups cheap.
    """
    await get_issues_collection().create_index([("location", "2dsphere")])
    await get_issues_collection().create_index([("reporter_id", 1)])
    await get_issues_collection().create_index([("status", 1)])


async def close_client() -> None:
    """Close the pooled connection on shutdown."""
    global _client
    if _client is not None:
        _client.close()
        _client = None
