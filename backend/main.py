"""Binary-Brains API entrypoint. LOCKED after setup.

This file is intentionally minimal: it wires CORS, registers the two
routers, and handles startup/shutdown. Feature work belongs in
`routers/` and `services/` — do not add business logic here.

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

import os


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

# CORS — allow the React dev server. Override with CORS_ORIGIN in backend/.env.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("CORS_ORIGIN", "http://localhost:5173"),
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
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
