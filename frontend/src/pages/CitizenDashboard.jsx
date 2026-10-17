/**
 * Dev 3 — Track reports, view nearby issues, upvote.
 *
 * Endpoints this page must call (contract agreed in setup):
 *   GET  /api/citizen/issues/mine?reporter_id=   → "My Reports" list
 *   GET  /api/citizen/issues/nearby?lat=&lon=    → nearby layer for MapPicker
 *   POST /api/citizen/issues/{id}/upvote         → upvote an issue
 *
 * Uses: MapPicker (nearby markers), axios + BASE_URL from apiConfig.
 *
 * TODO(Dev 3):
 *   1. Read `reporter_id` from localStorage (same key ReportIssue writes).
 *      Prompt to report an issue first if it is missing.
 *   2. Fetch /issues/mine and render each with its status badge
 *      (Yet to Start / Working / Done), priority, and upvote count.
 *   3. Fetch geolocation once, then /issues/nearby, and feed the results
 *      into <MapPicker markers={...} /> as {id, lat, lon, title, status}.
 *   4. Upvote button → POST /upvote with { reporter_id }, then update the
 *      row in state from the returned issue. Handle the 400 double-vote case.
 *   5. Empty state (no reports yet) and loading/error states.
 */

import { ClipboardList } from "lucide-react";

export default function CitizenDashboard() {
  return (
    <section>
      <header className="page-header">
        <h1>
          <ClipboardList size={20} style={{ verticalAlign: "text-bottom" }} /> My Reports
        </h1>
        <p>Track the status of issues you have reported, see what is nearby, and upvote others.</p>
      </header>

      <div className="todo-banner">
        <span aria-hidden="true">🚧</span>
        <div>
          <strong>TODO(Dev 3).</strong> Load <code>GET /api/citizen/issues/mine</code>{" "}
          for the tracked-reports list, <code>GET /api/citizen/issues/nearby</code> for
          the map layer, and wire the upvote button to{" "}
          <code>POST /api/citizen/issues/{"{id}"}/upvote</code>.
        </div>
      </div>
    </section>
  );
}
