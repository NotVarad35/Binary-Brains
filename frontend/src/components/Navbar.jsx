import { BarChart3, ClipboardList, LayoutDashboard, MapPin } from "lucide-react";
import { NavLink } from "react-router-dom";

/**
 * Shared top navigation. LOCKED shared file — renders on every page via App.jsx.
 * All four routes are already wired; nav styling is intentionally minimal so
 * Dev 3 / Dev 4 can theme pages without touching this.
 */

const LINKS = [
  { to: "/report", label: "Report Issue", Icon: MapPin },
  { to: "/dashboard", label: "My Reports", Icon: ClipboardList },
  { to: "/admin", label: "Admin Board", Icon: LayoutDashboard },
  { to: "/analytics", label: "Analytics", Icon: BarChart3 },
];

export default function Navbar() {
  return (
    <header className="navbar">
      <div className="navbar-brand">
        <span className="navbar-logo" aria-hidden="true">◉</span>
        <span className="navbar-title">Binary Brains</span>
      </div>

      <nav className="navbar-links" aria-label="Primary">
        {LINKS.map(({ to, label, Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              isActive ? "nav-link nav-link-active" : "nav-link"
            }
          >
            <Icon size={16} strokeWidth={2} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </header>
  );
}
