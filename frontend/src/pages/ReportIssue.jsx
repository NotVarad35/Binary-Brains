/**
 * Dev 3 — Citizen form: Photo, Category, GPS, Duplicate alert.
 *
 * Endpoints this page must call (contract agreed in setup):
 *   GET  /api/citizen/issues/nearby?lat=&lon=&radius_m=  → duplicate check
 *   POST /api/citizen/issues                              → multipart submit
 *
 * Uses: MapPicker (pin-drop), axios + BASE_URL from apiConfig.
 *
 * TODO(Dev 3):
 *   1. Form state: title, description, category (from models.Category),
 *      latitude/longitude, photo (File), reporter_id (persist a stable id
 *      in localStorage so "My Reports" and upvotes work across reloads).
 *   2. GPS: navigator.geolocation.getCurrentPosition → set lat/lon, with a
 *      clear error state if permission is denied.
 *   3. MapPicker for manual pin-dropping (`onPick` updates lat/lon).
 *   4. Duplicate alert: debounce a call to /issues/nearby as the user picks
 *      a location. If `duplicates.length > 0`, render a warning panel with
 *      an "Upvote existing report instead" action → POST /issues/{id}/upvote.
 *   5. Submit as FormData (photo + fields) to POST /api/citizen/issues.
 *      Show 409 handling if the backend rejects as a duplicate.
 *   6. Clear validation + success states.
 */

import { MapPin } from "lucide-react";

export default function ReportIssue() {
  return (
    <section>
      <header className="page-header">
        <h1>
          <MapPin size={20} style={{ verticalAlign: "text-bottom" }} /> Report an Issue
        </h1>
        <p>Pin the location on the map, add a photo, and submit. We will check for duplicates automatically.</p>
      </header>

      <div className="todo-banner">
        <span aria-hidden="true">🚧</span>
        <div>
          <strong>TODO(Dev 3).</strong> Build the citizen form here: photo upload,
          category select, GPS capture, <code>MapPicker</code> pin-dropping, and the
          duplicate alert backed by <code>GET /api/citizen/issues/nearby</code>.
          Submit via <code>POST /api/citizen/issues</code> using{" "}
          <code>BASE_URL</code> from <code>src/apiConfig.js</code>.
        </div>
      </div>
    </section>
  );
}
