# Binary Brains

A civic-issue reporting platform: citizens photograph and pin a problem (pothole,
broken streetlight, overflowing bin), the app checks for **nearby duplicates** using
a Haversine/geospatial check, ranks reports with a **priority algorithm**, and gives
municipal admins a **Kanban board** with **analytics**.

> **Status:** scaffolded. Shared/locked files are complete; per-developer files are
> marked with `TODO(Dev N)` and carry a fixed contract — see [Ownership](#ownership).

---

## Live links

| What | Link |
| --- | --- |
| Deployed frontend | _TBD — Dev 2_ |
| Deployed backend | _TBD — Dev 2_ |
| Demo video (3-5 min) | _TBD — Dev 2_ |

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

## Repo layout

```
Binary-Brains/
├── backend/
│   ├── main.py                  # LOCKED after setup (only imports routers & CORS)
│   ├── database.py              # MongoDB Atlas connection setup
│   ├── models.py                # Pydantic schemas for validation
│   ├── requirements.txt         # fastapi, uvicorn, pymongo, motor, pydantic, python-multipart
│   ├── .env.example             # copy to .env
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
└── README.md                    # Dev 2: Live link, architecture, and 3-5 min demo video link
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

---

## Setup

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

### 2. Frontend

```powershell
cd frontend
Copy-Item .env.example .env
npm install
npm run dev
```

App: <http://localhost:5173>

> **Note:** during initial scaffolding Node was not installed on the setup machine,
> so `npm install` has **not** been run yet. Run it once after installing Node LTS.

### 3. Environment variables

**`backend/.env`**

| Key | Purpose | Example |
| --- | --- | --- |
| `MONGO_URI` | Atlas / local connection string | `mongodb+srv://user:pass@cluster.mongodb.net/` |
| `MONGO_DB_NAME` | Database name | `binary_brains` |
| `CORS_ORIGIN` | Allowed frontend origin | `http://localhost:5173` |

**`frontend/.env`**

| Key | Purpose | Example |
| --- | --- | --- |
| `VITE_API_URL` | Backend origin, no trailing slash | `http://localhost:8000` (dev) / deployed URL (prod) |

`.env` files are gitignored — only `.env.example` is committed.

### 4. What was verified at setup

| Check | Result |
| --- | --- |
| `pip install -r requirements.txt` into `backend/.venv` | ✅ installed |
| `import main` | ✅ imports cleanly |
| `uvicorn main:app` boots | ✅ (also boots **without** MongoDB, printing a startup warning) |
| All 9 API routes registered | ✅ confirmed via `/openapi.json` |
| `GET /health` | ✅ `{"status":"ok"}` |
| CORS from `http://localhost:5173` | ✅ `Access-Control-Allow-Origin` reflected |
| Unimplemented endpoints | ✅ return `501` with the Dev tag, not an opaque `500` |
| `python scripts/check_frontend_imports.py` | ✅ 9 files, 7 relative imports, 0 unresolved |
| `npm install` / `npm run dev` | ⛔ **not run** — Node was not installed on the setup machine |

> `backend/.venv` currently has Python **3.12.4** and the pinned dependency set.
> Note `pymongo==4.9.2` is deliberate: `motor==3.6.0` requires `pymongo<4.10`.

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

## Key algorithms

### Duplicate check

`priority_engine.haversine_distance()` (implemented) gives great-circle distance in
metres. `find_duplicates()` (Dev 1) pairs it with Mongo's `2dsphere` index via
`$near` so the candidate set comes from the index and Python confirms the distance.

### Priority score

`calculate_priority()` (Dev 1) returns an **int in 0–100**. Baseline weights per
category live in `CATEGORY_WEIGHTS`; upvotes, age open, and duplicate status adjust
the score. Must stay deterministic — `AnalyticsPage` sorts on it.

---

## Demo script (for the 3-5 min video)

1. **Report** — drop a pin on `MapPicker`, add a photo, trigger the duplicate alert. (~45s)
2. **Duplicate → upvote** — show the nearby-report warning and upvote instead. (~30s)
3. **Admin Kanban** — move the card Yet to Start → Working → Done, upload worker proof. (~60s)
4. **Analytics** — resolution rate, created-vs-resolved chart, priority leaderboard. (~45s)
5. **Priority explanation** — show how the score drives the leaderboard ordering. (~30s)

---

## License

See [LICENSE](LICENSE).
