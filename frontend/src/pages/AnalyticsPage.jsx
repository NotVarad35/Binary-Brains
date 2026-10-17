/**
 * Dev 4 — Resolution metrics, charts, priority leaderboard.
 *
 * Endpoint this page must call (contract agreed in setup):
 *   GET /api/admin/analytics → AnalyticsResponse (see backend/models.py)
 *
 * Response shape:
 *   stats               : { total_issues, yet_to_start, working, done,
 *                            resolution_rate, avg_resolution_hours, total_upvotes }
 *   category_breakdown  : [{ category, total, done }]
 *   priority_leaderboard: [{ id, title, category, priority, upvotes, status }]
 *   daily_created       : [{ date: "YYYY-MM-DD", count }]
 *   daily_resolved      : [{ date: "YYYY-MM-DD", count }]
 *
 * Uses: recharts, axios + BASE_URL from apiConfig.
 *
 * TODO(Dev 4):
 *   1. Fetch once on mount; handle loading + error states.
 *   2. Stat cards across the top: total, done, resolution rate (% — note
 *      `resolution_rate` is 0.0-1.0, multiply by 100), avg resolution hours.
 *   3. Line/area chart of daily_created vs daily_resolved over 14 days
 *      (recharts <LineChart> with two <Line> series).
 *   4. Pie chart of category_breakdown.
 *   5. Horizontal BarChart of priority_leaderboard (top 10 by priority).
 *   6. Keep charts responsive with <ResponsiveContainer width="100%" height={300}>.
 */

import { BarChart3 } from "lucide-react";

export default function AnalyticsPage() {
  return (
    <section>
      <header className="page-header">
        <h1>
          <BarChart3 size={20} style={{ verticalAlign: "text-bottom" }} /> Analytics
        </h1>
        <p>Resolution metrics, category breakdown, and the priority leaderboard.</p>
      </header>

      <div className="todo-banner">
        <span aria-hidden="true">🚧</span>
        <div>
          <strong>TODO(Dev 4).</strong> Fetch <code>GET /api/admin/analytics</code> and
          render the stat cards, the daily created/resolved line chart, the category
          breakdown pie, and the priority leaderboard bar chart with{" "}
          <code>recharts</code>.
        </div>
      </div>
    </section>
  );
}
