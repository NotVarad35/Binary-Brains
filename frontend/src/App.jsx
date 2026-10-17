/**
 * App shell — LOCKED after setup.
 *
 * Navbar + pre-wired Routes. Feature work belongs in `pages/` and
 * `components/` — do not add page-level logic here.
 *
 * Routes:
 *   /report      → ReportIssue      (Dev 3)
 *   /dashboard   → CitizenDashboard (Dev 3)
 *   /admin       → AdminKanban      (Dev 4)
 *   /analytics   → AnalyticsPage    (Dev 4)
 *   /            → redirect to /report
 */

import { Navigate, Route, Routes } from "react-router-dom";
import Navbar from "./components/Navbar.jsx";
import AdminKanban from "./pages/AdminKanban.jsx";
import AnalyticsPage from "./pages/AnalyticsPage.jsx";
import CitizenDashboard from "./pages/CitizenDashboard.jsx";
import ReportIssue from "./pages/ReportIssue.jsx";

export default function App() {
  return (
    <div className="app-shell">
      <Navbar />
      <main className="app-main">
        <Routes>
          <Route path="/" element={<Navigate to="/report" replace />} />
          <Route path="/report" element={<ReportIssue />} />
          <Route path="/dashboard" element={<CitizenDashboard />} />
          <Route path="/admin" element={<AdminKanban />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="*" element={<Navigate to="/report" replace />} />
        </Routes>
      </main>
    </div>
  );
}
