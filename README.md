# Binary Brains

A civic-issue reporting platform: citizens photograph and pin a problem (pothole,
broken streetlight, overflowing bin), the app checks for **nearby duplicates** using
a Haversine/geospatial check, ranks reports with a **priority algorithm**, and gives
municipal admins a **Kanban board** with **analytics**.

> **Status:** scaffolded. Shared/locked files are complete; per-developer files are
> marked with `TODO(Dev N)` and carry a fixed contract — see [Ownership](#ownership).

---

## Live Deployment & Demo Video

> **Paste the final URLs here before submitting.**

| What | Link |
| --- | --- |
| 🚀 Deployed frontend (Vercel) | _TBD — paste URL_ |
| ⚙️ Deployed backend (Render / Railway) | _TBD — paste URL_ |
| 📘 Swagger API docs | `<backend-url>/docs` |
| 🎥 Demo video (3–5 min) | _TBD — paste URL_ |

---

## Problem Statement

City infrastructure is inspected on slow fixed cycles, so the issues citizens
notice fastest — potholes, dead streetlights, overflowing bins, sewage spills —
sit unfixed for weeks. Two things make it worse:

1. **Duplicate noise.** Twenty people report the *same* pothole, so the
   municipality sees twenty "new" tickets and exactly one real problem.
2. **No prioritisation.** A dangerous crater on a bus route is treated the same
   as a cosmetic complaint, because severity is never quantified.

**Civic-Fix** closes that loop end to end: a citizen reports an issue with a
photo and a GPS pin, a Haversine geo-check merges duplicates into the original
and boosts its priority, an explainable score ranks what to fix first, and
authorities get a Kanban board plus live resolution analytics.

## Key Features

- **Geo-tagged reporting** — drop a pin on a Leaflet map, attach a photo, pick a category and severity.
- **Duplicate detection** — a second report within ~50 m of an existing one is flagged and merged (`duplicate_of`) instead of becoming a second ticket, and the original's count/priority goes up.
- **Dynamic priority score** — category severity + community demand (upvotes) + time open − duplicate penalty, clamped to `0–100`.
- **Citizen tracking** — "My Reports" list, a nearby-issues map layer, and one-tap **Upvote / Me Too**.
- **Admin Kanban triage** — Yet to Start → Working → Done, auto-sorted by priority, with a worker "after" photo required before an issue can be closed.
- **Live impact analytics** — total issues, resolution rate, average resolution time, category breakdowns, and a priority leaderboard.
- **One-click demo seeding** — `POST /api/seed` repopulates 10 realistic Pune issues in under a second.

---

## Architecture

```
┌────────────────────────────┐        HTTP / JSON + multipart        ┌────────────────────────────┐
│   frontend/  (React + Vite)│  ───────────────────────────────────▶ │   backend/   (FastAPI)     │
│                            │                                       │                            │
│  pages/                    │                                       │  main.py         [LOCKED]  │
│   ReportIssue      (Dev 3) │   axios → BASE_URL from apiConfig.js  │  routers/                   │
│   CitizenDashboard (Dev 3) │                                       │   citizen_routes  (Dev 1)  │
│   AdminKanban      (Dev 4) │                                       │   admin_routes    (Dev 2)  │
│   AnalyticsPage    (Dev 4) │                                       │  services/                  │
│  components/               │                                       │   priority_engine (Dev 1)  │
│   Navbar          [LOCKED] │                                       │  models.py        [LOCKED]  │
│   MapPicker       (Dev 3)  │                                       │  database.py      [LOCKED]  │
└────────────────────────────┘                                       └──────────────┬───────────────┘
                                                                                   │ motor (async)
                                                                                   ▼
                                                                      ┌────────────────────────────┐
                                                                      │   MongoDB Atlas            │
                                                                      │   db: binary_brains        │
                                                                      │   collection: issues       │
                                                                      │   index: 2dsphere(location)│
                                                                      └────────────────────────────┘
```

### Request flow

1. Citizen drops a pin → frontend calls `GET /api/citizen/issues/nearby`.
2. Backend runs a geospatial query + `haversine_distance()` to flag duplicates.
3. Frontend shows a "this may already be reported" alert; citizen can upvote instead.
4. Submit → `POST /api/citizen/issues`, priority computed server-side.
5. Admin moves the card on the Kanban → `PATCH /api/admin/issues/{id}/status`.
6. Worker uploads proof → `POST /api/admin/issues/{id}/photo`.
7. Analytics reads `GET /api/admin/analytics` and renders the charts.

---

## Tech Stack

| Layer | Choice |
| --- | --- |
| Frontend | React 18 + Vite, React Router 6, axios |
| Maps | Leaflet + react-leaflet (`MapPicker`) |
| Charts | Recharts |
| Icons | lucide-react |
| Backend | FastAPI + Uvicorn (async), Pydantic v2 |
| Database | MongoDB Atlas via Motor (async PyMongo) |
| Geo | MongoDB `2dsphere` index + hand-rolled Haversine check |
| Deploy | Vercel (frontend) · Render / Railway (backend) |

---

## Repo layout

```
Binary-Brains/
├── backend/
│   ├── main.py                  # LOCKED after setup (only imports routers & CORS)
│   ├── database.py              # MongoDB Atlas connection setup
│   ├── models.py                # Pydantic schemas for validation
│   ├── seed_data.py             # Dev 3: 10-issue Pune demo dataset (+ CLI & POST /api/seed)
│   ├── requirements.txt         # fastapi, uvicorn, pymongo, motor, pydantic, python-multipart
│   ├── .env.example             # copy to .env
│   ├── Procfile                 # Dev 3: start command for Render/Railway/Heroku
│   ├── .python-version          # Dev 3: pins Python 3.12 for the deploy host
│   ├── .venv/                   # virtualenv (gitignored)
│   ├── uploads/                 # citizen photos + worker proof (gitignored)
│   ├── services/
│   │   └── priority_engine.py   # Dev 1: Duplicate check (Haversine) + Priority algorithm
│   └── routers/
│       ├── citizen_routes.py    # Dev 1: Submit issue, get nearby issues, upvote
│       └── admin_routes.py      # Dev 2: Kanban status update, worker photo upload, analytics stats
│
├── frontend/
│   ├── package.json             # axios, react-router-dom, lucide-react, leaflet, react-leaflet, recharts
│   ├── index.html / vite.config.js / src/main.jsx / src/index.css   # Vite boot files
│   ├── vercel.json              # Dev 3: Vite build + SPA rewrite for client-side routes
│   ├── .env.example             # copy to .env
│   └── src/
│       ├── App.jsx              # LOCKED after setup (Navbar + pre-wired Routes)
│       ├── apiConfig.js         # Exports BASE_URL (switches between localhost and prod)
│       ├── components/
│       │   ├── Navbar.jsx       # Shared top navigation
│       │   └── MapPicker.jsx    # Dev 3: Leaflet map component for pin-dropping & viewing nearby
│       └── pages/
│           ├── ReportIssue.jsx      # Dev 3: Citizen form (Photo, Category, GPS, Duplicate alert)
│           ├── CitizenDashboard.jsx # Dev 3: Track reports, view nearby issues, upvote
│           ├── AdminKanban.jsx      # Dev 4: Yet to Start / Working / Done board + Worker proof modal
│           └── AnalyticsPage.jsx    # Dev 4: Resolution metrics, charts, priority leaderboard
│
├── scripts/
│   └── check_frontend_imports.py    # stdlib-only: verifies every relative import resolves (no Node needed)
│
├── render.yaml                  # Dev 3: Render Blueprint (one-click backend deploy)
└── README.md                    # Live link, architecture, and 3-5 min demo video link
```

---

## Ownership

Files marked **LOCKED** were finished during setup — do not edit them without
team agreement, since everyone's work depends on them.

| Dev | Files | Scope |
| --- | --- | --- |
| **Dev 1** | `services/priority_engine.py`, `routers/citizen_routes.py` | Haversine duplicate check, priority scoring, submit / nearby / mine / upvote endpoints |
| **Dev 2** | `routers/admin_routes.py`, **this `README.md`** | Kanban status updates, worker photo upload, analytics aggregation; live link + demo video |
| **Dev 3** | `components/MapPicker.jsx`, `pages/ReportIssue.jsx`, `pages/CitizenDashboard.jsx` | Leaflet map, citizen form, duplicate alert, report tracking, upvoting |
| **Dev 4** | `pages/AdminKanban.jsx`, `pages/AnalyticsPage.jsx` | Kanban board + worker proof modal, recharts analytics |
| **All** | `main.py` 🔒, `database.py` 🔒, `models.py` 🔒, `App.jsx` 🔒, `Navbar.jsx` 🔒, `apiConfig.js` 🔒 | Setup contract — extend `models.py` with new schemas rather than inventing ad-hoc shapes |

> **Dev 3 (infrastructure & seeding)** additionally owns `backend/seed_data.py`
> (the 10-issue Pune demo dataset, runnable as a CLI or via `POST /api/seed`),
> `backend/.env.example`, and this README's polish. The only edit to a 🔒 file
> is the deliberate `POST /api/seed` hook in `main.py` (documented in that
> file's docstring) and opening CORS for deployment. Seeding writes exactly the
> `IssueOut` shape below — it never invents new fields.

---

## Local Setup

### Prerequisites

- Python **3.12**
- Node.js **20+** (LTS) and npm
- A MongoDB Atlas account (or a local MongoDB on `27017`)

### 1. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# copy the env template and fill in your Atlas connection string
Copy-Item .env.example .env

.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

API: <http://localhost:8000> · Swagger docs: <http://localhost:8000/docs> · Health: `/health`

### 2. Seed the demo data (Dev 3)

Populate MongoDB with 10 realistic Pune issues so the Kanban board and
Analytics charts are full from the first load:

```powershell
# seeds only if the collection is empty
.\.venv\Scripts\python.exe seed_data.py

# or wipe + reseed (handy right before recording the demo)
.\.venv\Scripts\python.exe seed_data.py --force
```

Or, with the API running, hit the convenience endpoint — this also works
against the **deployed** backend:

```powershell
Invoke-RestMethod -Method Post "http://localhost:8000/api/seed?force=true"
```

> `seed_data.py` deliberately leaves `photo_url` / `worker_photo_url` as
> `null`, so there are no broken images during the demo — real photos are
> uploaded live.

### 3. Frontend

```powershell
cd frontend
Copy-Item .env.example .env
npm install
npm run dev
```

App: <http://localhost:5173>

> **Note:** during initial scaffolding Node was not installed on the setup machine,
> so `npm install` has **not** been run yet. Run it once after installing Node LTS.

### 4. Environment variables

**`backend/.env`**

| Key | Purpose | Example |
| --- | --- | --- |
| `MONGO_URI` | Atlas / local connection string | `mongodb+srv://user:pass@cluster.mongodb.net/` |
| `MONGO_DB_NAME` | Database name | `binary_brains` |
| `MONGO_SERVER_SELECTION_TIMEOUT_MS` | Mongo connect timeout, keeps boot fast | `3000` |

> CORS is intentionally wide open (`allow_origins=["*"]`) so the local Vite
> server and the deployed frontend both work without per-origin config, so
> `CORS_ORIGIN` is no longer used.

**`frontend/.env`**

| Key | Purpose | Example |
| --- | --- | --- |
| `VITE_API_URL` | Backend origin, no trailing slash | `http://localhost:8000` (dev) / deployed URL (prod) |

`.env` files are gitignored — only `.env.example` is committed.

### 5. What was verified at setup

| Check | Result |
| --- | --- |
| `pip install -r requirements.txt` into `backend/.venv` | ✅ installed |
| `import main` | ✅ imports cleanly |
| `uvicorn main:app` boots | ✅ (also boots **without** MongoDB, printing a startup warning) |
| All 10 API routes registered | ✅ confirmed via `/openapi.json` |
| `GET /health` | ✅ `{"status":"ok"}` |
| CORS | ✅ `allow_origins=["*"]` — works for localhost **and** the deployed frontend |
| `POST /api/seed` (Dev 3) | ✅ registered; reseeds the demo dataset via `seed_data.py` |
| `seed_data.py` document build (Dev 3) | ✅ 10 issues, valid categories/statuses, `[lng, lat]` geo, duplicate pair ≈23 m apart |
| `python seed_data.py` with Mongo down (Dev 3) | ✅ exits with an actionable message instead of a traceback |
| Unimplemented endpoints | ✅ return `501` with the Dev tag, not an opaque `500` |
| `python scripts/check_frontend_imports.py` | ✅ 9 files, 7 relative imports, 0 unresolved |
| `npm install` / `npm run dev` | ⛔ **not run** — Node was not installed on the setup machine |

> `backend/.venv` currently has Python **3.12.4** and the pinned dependency set.
> Note `pymongo==4.9.2` is deliberate: `motor==3.6.0` requires `pymongo<4.10`.

---

## Deployment

Three managed services, no servers to babysit:

```
MongoDB Atlas  ──▶  Render / Railway (FastAPI)  ──▶  Vercel (React + Vite)
  free M0            ./render.yaml + backend/Procfile        ./frontend/vercel.json
```

### 1. MongoDB Atlas

1. Create a free **M0** cluster and a database user (username + password).
2. **Network Access → Add IP Address → `0.0.0.0/0`** (allow from anywhere — required
   for Render's dynamic egress IPs).
3. Copy the connection string and append the db name:
   `mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority`

### 2. Backend → Render (or Railway)

**Render (Blueprint):** New → **Blueprint** → pick this repo. Render reads
`render.yaml`, builds with `pip install -r requirements.txt`, starts with
`uvicorn main:app --host 0.0.0.0 --port $PORT`, and health-checks `/health`.
Set `MONGO_URI` when prompted (it is `sync: false`, so it is never committed).

**Railway alternative:** new project → deploy from repo → set the root directory
to `backend`. `backend/Procfile` and `backend/.python-version` tell it how to run.

Either way, confirm the deploy:
- `GET https://<your-api>/health` → `{"status":"ok"}`
- `GET https://<your-api>/docs` → Swagger UI

### 3. Seed the deployed database (one click)

```powershell
Invoke-RestMethod -Method Post "https://<your-api>/api/seed?force=true"
```

Run this right before recording so the live Kanban/Analytics are always full.

### 4. Frontend → Vercel

1. Import this repo; set the **root directory** to `frontend` (Vercel auto-detects Vite).
2. Add an environment variable: **`VITE_API_URL` = `https://<your-api>`** (no trailing slash).
3. Deploy. `frontend/vercel.json` handles the SPA fallback so deep links like
   `/admin` don't 404.

CORS is already wide open in `main.py`, so the Vercel domain reaches Render with
no extra configuration.

### 5. Post-deploy checklist

- [ ] Paste the frontend, backend, and demo-video URLs into the [table at the top](#live-deployment--demo-video).
- [ ] `POST /api/seed?force=true` against the deployed backend.
- [ ] Smoke-test the flow: report → duplicate alert → Kanban move → analytics.

---

## Working with the TODOs

Per-dev files raise `NotImplementedError("TODO(Dev N): …")`. `main.py` maps that to a
**`501 Not Implemented`** whose body names the owner:

```json
{ "detail": "TODO(Dev 2): implement get_analytics()", "path": "/api/admin/analytics" }
```

So Dev 3 / Dev 4 can call any endpoint from day one and immediately see who owns it,
instead of debugging a blank `500`.

---

## API contract

Base URL: `http://localhost:8000`. All paths below are fixed; Dev 1 and Dev 2
implement them, Dev 3 and Dev 4 consume them.

### Citizen — `routers/citizen_routes.py` (Dev 1)

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/citizen/issues` | Submit an issue (multipart: photo + fields) |
| `GET` | `/api/citizen/issues/nearby?lat=&lon=&radius_m=` | Nearby issues + flagged duplicates |
| `GET` | `/api/citizen/issues/mine?reporter_id=` | A citizen's own reports |
| `POST` | `/api/citizen/issues/{id}/upvote` | Increment upvotes (body: `{ reporter_id }`) |

### Admin — `routers/admin_routes.py` (Dev 2)

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/admin/issues` | Flat list for the Kanban board |
| `PATCH` | `/api/admin/issues/{id}/status` | Move column (body: `{ status }`) |
| `POST` | `/api/admin/issues/{id}/photo` | Worker proof upload (multipart) |
| `GET` | `/api/admin/analytics` | Stats, breakdown, leaderboard, daily series |

### Infrastructure — `main.py` + `seed_data.py` (Dev 3)

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/seed?force=true` | Wipe + re-insert the 10 Pune demo issues. `force=false` seeds only when empty. |
| `GET` | `/health` | Liveness probe used by the frontend and deploy checks. |

### Issue document (MongoDB `issues` collection)

```jsonc
{
  "_id": "…",
  "title": "Deep pothole outside market",
  "description": "…",
  "category": "Pothole",           // models.Category
  "status": "Yet to Start",        // models.Status: Yet to Start | Working | Done
  "priority": 72,                  // 0-100, from priority_engine.calculate_priority()
  "upvotes": 14,
  "location": { "type": "Point", "coordinates": [77.5946, 12.9716] }, // [lon, lat]
  "latitude": 12.9716,             // denormalised for cheap frontend use
  "longitude": 77.5946,
  "photo_url": "/uploads/…",
  "worker_photo_url": "/uploads/…",
  "reporter_id": "cit-…",          // stable id in localStorage
  "duplicate_of": null,            // _id of the original report, if a dupe
  "created_at": "2026-10-17T09:00:00Z",
  "updated_at": "2026-10-17T09:00:00Z",
  "resolved_at": null              // stamped when status → Done
}
```

> ⚠️ GeoJSON `coordinates` are **`[longitude, latitude]`** — the reverse of the
> `latitude`/`longitude` fields. This is the single most common bug in this codebase.

---

## Dynamic Priority & Haversine Duplicate Algorithm

### Duplicate detection (Haversine)

`priority_engine.haversine_distance(lat1, lon1, lat2, lon2)` returns the
great-circle distance between two WGS-84 points in **metres** using the
standard Haversine formula:

```text
a = sin²(Δφ/2) + cos φ1 · cos φ2 · sin²(Δλ/2)
c = 2 · atan2(√a, √(1−a))
distance = R · c          # R = 6 371 000 m  (mean Earth radius)
```

`find_duplicates()` pairs it with MongoDB's `2dsphere` index via `$near`, so
the geometry index produces the candidate set and Python confirms the exact
distance. A new report within the duplicate radius (~50 m, same category) is
**merged into the original**: the original's `upvotes` goes up and the new
document stores `duplicate_of = <original _id>` instead of becoming a separate
ticket — which is what stops twenty reports of one pothole becoming twenty
tickets.

> ⚠️ GeoJSON `coordinates` are **`[longitude, latitude]`** — the reverse of the
> `latitude`/`longitude` fields. This is the single most common bug in this
> codebase.

### Priority score

`priority_engine.calculate_priority()` returns a deterministic **integer in
`0–100`** that the Kanban board and the analytics leaderboard sort on:

```text
score = CATEGORY_WEIGHTS.get(category, 20)   # base severity, 15–55
      + min(upvotes * 5, 40)                 # community demand
      + min(age_hours * 0.5, 20)             # time left open
      − (20 if is_duplicate else 0)          # duplicate penalty
score = clamp(score, 0, PRIORITY_MAX)        # PRIORITY_MAX = 100
```

Category weights live in `CATEGORY_WEIGHTS` (e.g. `Sewage` 55, `Broken Road`
50, `Water Logging` 45, `Pothole` 40, `Garbage` 25, `Graffiti` 15). Because the
score is a pure function of its inputs, the same issue always ranks the same
way — `AnalyticsPage` depends on that determinism.

---

## Demo script (for the 3-5 min video)

0. **Reset the data** — `POST /api/seed?force=true` so the board and charts are fully populated. (~5s)
1. **Report** — drop a pin on `MapPicker`, add a photo, trigger the duplicate alert. (~45s)
2. **Duplicate → upvote** — show the nearby-report warning and upvote instead. (~30s)
3. **Admin Kanban** — move the card Yet to Start → Working → Done, upload worker proof. (~60s)
4. **Analytics** — resolution rate, created-vs-resolved chart, priority leaderboard. (~45s)
5. **Priority explanation** — show how the score drives the leaderboard ordering. (~30s)

---

## License

See [LICENSE](LICENSE).
