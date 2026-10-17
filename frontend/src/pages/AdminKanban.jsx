/**
 * Dev 4 — Yet to Start / Working / Done board + Worker proof modal.
 *
 * Endpoints this page must call (contract agreed in setup):
 *   GET   /api/admin/issues                  → all issues (group client-side)
 *   PATCH /api/admin/issues/{id}/status      → move between columns
 *   POST  /api/admin/issues/{id}/photo       → worker proof upload (multipart)
 *
 * Uses: axios + BASE_URL from apiConfig, lucide-react icons.
 *
 * TODO(Dev 4):
 *   1. Fetch once, then group into three columns by `status` — the API
 *      returns a flat list, column grouping happens here:
 *        Yet to Start | Working | Done
 *   2. Move an issue: PATCH /status with { status }. Optimistically update
 *      the board, roll back if the request fails. Setting Done should make
 *      the backend stamp `resolved_at`.
 *   3. Drag-and-drop between columns (HTML5 DnD is enough) OR explicit
 *      ← / → buttons — buttons are faster to ship and easier to demo.
 *   4. Worker proof modal: file input → POST /photo as multipart form-data
 *      with the issue id, then show the returned `worker_photo_url`.
 *   5. Sort cards inside each column by `priority` desc so the most urgent
 *      work sits at the top.
 */

import { LayoutDashboard } from "lucide-react";

const COLUMNS = ["Yet to Start", "Working", "Done"];

export default function AdminKanban() {
  return (
    <section>
      <header className="page-header">
        <h1>
          <LayoutDashboard size={20} style={{ verticalAlign: "text-bottom" }} /> Admin Board
        </h1>
        <p>Move issues across the pipeline and upload worker proof photos.</p>
      </header>

      <div className="todo-banner">
        <span aria-hidden="true">🚧</span>
        <div>
          <strong>TODO(Dev 4).</strong> Fetch <code>GET /api/admin/issues</code>, group the
          flat list into these three columns, and wire status moves to{" "}
          <code>PATCH /api/admin/issues/{"{id}"}/status</code> plus the worker proof modal
          to <code>POST /api/admin/issues/{"{id}"}/photo</code>.
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, marginTop: 20 }}>
        {COLUMNS.map((col) => (
          <div className="card" key={col} style={{ minHeight: 240 }}>
            <h3 style={{ margin: "0 0 12px", fontSize: "0.95rem", color: "var(--text-muted)" }}>{col}</h3>
            {/* TODO(Dev 4): render issue cards per column */}
          </div>
        ))}
      </div>
    </section>
  );
}
