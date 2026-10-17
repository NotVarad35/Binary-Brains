"""Binary-Brains API entrypoint. LOCKED after setup.

This file is intentionally minimal: it wires CORS, registers the two
routers, and handles startup/shutdown. Feature work belongs in
`routers/` and `services/` — do not add business logic here.

One deliberate exception: `POST /api/seed` (Dev 3). It is an infrastructure
convenience hook that repopulates the demo dataset — see `seed_data.py`.

Run locally:
    cd backend
    uvicorn main:app --reload
Docs:
    http://localhost:8000/docs
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import close_client, ensure_indexes
from routers import admin_routes, citizen_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run once at boot and once at shutdown."""
    try:
        await ensure_indexes()  # 2dsphere index for the duplicate/Haversine checks
    except Exception as exc:
        # Don't refuse to boot: the team may not have MONGO_URI configured yet.
        # Routes will raise on use, and restarting after fixing .env is enough.
        print(
            f"[startup] WARNING: could not reach MongoDB, indexes NOT created: {exc}\n"
            f"[startup]          Check MONGO_URI in backend/.env, then restart.",
            flush=True,
        )
    yield
    await close_client()


app = FastAPI(
    title="Binary-Brains API",
    description="Citizen-reported civic issue reporting with duplicate detection and prioritisation.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — wide open so the Vite dev server, `localhost`, and the deployed
# frontend (e.g. Vercel) can all reach the API with no per-origin config.
#
# `allow_credentials` is False on purpose: the app authenticates nothing via
# cookies (the citizen `reporter_id` lives in localStorage), and browsers
# reject a wildcard origin combined with credentials anyway.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers register their own /api/citizen and /api/admin prefixes.
app.include_router(citizen_routes.router)
app.include_router(admin_routes.router)


@app.exception_handler(NotImplementedError)
async def _not_implemented_handler(request, exc: NotImplementedError):
    """Surface `TODO(Dev N)` stubs as 501 instead of an opaque 500.

    Keeps unfinished endpoints distinguishable from real bugs while the
    four devs work in parallel.
    """
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=501,
        content={
            "detail": str(exc) or "Not implemented yet",
            "path": request.url.path,
        },
    )


@app.get("/health", tags=["health"])
async def health_check():
    """Cheap liveness probe for the frontend and for deploy checks."""
    return {"status": "ok"}


@app.post("/api/seed", tags=["seed"])
async def seed_database(force: bool = True):
    """Dev 3 — one-click (re)population of the demo dataset.

    `force=true` (the default) wipes the `issues` collection and re-inserts
    the 10 curated Pune demo issues. Handy right before recording the demo
    video so the Kanban board and Analytics page always look full.

    Pass `force=false` to seed only when the collection is empty.

    The heavy lifting lives in `seed_data.py`; this endpoint is just the
    HTTP trigger.
    """
    from seed_data import seed_demo_issues

    return await seed_demo_issues(force=force)
