/**
 * Dev 3 — Citizen dashboard: map of every report, filters, priority-sorted cards,
 * "before & after" resolution proof, and upvoting.
 *
 * Endpoints (real contract):
 *   GET  /api/admin/issues                     → flat list of all issues (primary)
 *   GET  /api/citizen/issues/mine?reporter_id= → fallback: this citizen's reports
 *   GET  /api/citizen/issues/nearby?lat=&lon=  → fallback: nearby issues
 *   POST /api/citizen/issues/{id}/upvote       → "I See This Too (+1)"
 *
 * The board fetches all issues when the backend exposes it, and degrades to the
 * citizen-scoped endpoints when it does not (e.g. while Dev 2's admin endpoints
 * are still stubs returning 501).
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  CheckCircle2,
  ClipboardList,
  Clock,
  Construction,
  Droplets,
  Filter,
  ImageOff,
  Lightbulb,
  Loader2,
  MapPin,
  Navigation,
  RefreshCw,
  Route,
  SprayCan,
  ThumbsUp,
  Trash2,
  Waves,
} from "lucide-react";
import { BASE_URL } from "../apiConfig";
import MapPicker, { normalizeStatus } from "../components/MapPicker.jsx";

const REPORTER_KEY = "civicfix.reporter_id";
const DEFAULT_CENTER = [12.9716, 77.5946];

const CATEGORY_ICONS = {
  Pothole: Construction,
  "Broken Road": Route,
  "Street Light": Lightbulb,
  Garbage: Trash2,
  Graffiti: SprayCan,
  "Water Logging": Waves,
  Sewage: Droplets,
  Other: MapPin,
};

const STATUS_META = {
  "Yet to Start": { label: "Pending", color: "#ef4444" },
  Working: { label: "In Progress", color: "#38bdf8" },
  Done: { label: "Resolved", color: "#22c55e" },
};

const STATUS_FILTERS = ["All", "Yet to Start", "Working", "Done"];

function categoryIcon(category) {
  return CATEGORY_ICONS[category] || MapPin;
}

function statusMeta(status) {
  return (
    STATUS_META[normalizeStatus(status)] || {
      label: status ? String(status) : "Unknown",
      color: "#94a3b8",
    }
  );
}

function priorityColor(priority) {
  const p = Number(priority) || 0;
  if (p >= 70) return "#ef4444";
  if (p >= 40) return "#f59e0b";
  return "#22c55e";
}

/** Prefix relative `/uploads/...` paths with the API origin; pass through data/http URLs. */
function mediaUrl(url) {
  if (!url) return null;
  if (/^(https?:|data:|blob:)/i.test(url)) return url;
  return `${BASE_URL}${url.startsWith("/") ? "" : "/"}${url}`;
}

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function getReporterId() {
  let id = null;
  try {
    id = localStorage.getItem(REPORTER_KEY);
  } catch {
    /* ignore */
  }
  if (!id) {
    const rand =
      typeof crypto !== "undefined" && crypto.randomUUID
        ? crypto.randomUUID()
        : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    id = `cit-${rand}`;
    try {
      localStorage.setItem(REPORTER_KEY, id);
    } catch {
      /* ignore */
    }
  }
  return id;
}

const cardStyle = {
  background: "var(--surface)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius)",
  padding: 18,
};

function Pill({ label, value, color }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "10px 16px",
        borderRadius: 999,
        background: "var(--surface)",
        border: "1px solid var(--border)",
      }}
    >
      <span
        style={{
          width: 10,
          height: 10,
          borderRadius: 999,
          background: color,
          flexShrink: 0,
        }}
      />
      <span style={{ fontSize: 13, color: "var(--text-muted)" }}>{label}</span>
      <span style={{ fontSize: 15, fontWeight: 700 }}>{value}</span>
    </div>
  );
}

function ProofImage({ src, label }) {
  const [failed, setFailed] = useState(false);
  const url = mediaUrl(src);
  const isAfter = label === "After";
  return (
    <figure style={{ margin: 0 }}>
      <div
        style={{
          height: 130,
          borderRadius: 8,
          overflow: "hidden",
          border: "1px solid var(--border)",
          background: "var(--surface-2)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {url && !failed ? (
          <img
            src={url}
            alt={label}
            onError={() => setFailed(true)}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        ) : (
          <ImageOff size={22} color="var(--text-muted)" />
        )}
      </div>
      <figcaption
        style={{
          marginTop: 6,
          fontSize: 11,
          fontWeight: 700,
          letterSpacing: "0.04em",
          textTransform: "uppercase",
          color: isAfter ? "var(--success)" : "var(--text-muted)",
        }}
      >
        {label}
      </figcaption>
    </figure>
  );
}

export default function CitizenDashboard() {
  const reporterId = useMemo(() => getReporterId(), []);

  const [issues, setIssues] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [source, setSource] = useState(null);

  const [filterCategory, setFilterCategory] = useState("All");
  const [filterStatus, setFilterStatus] = useState("All");

  const [upvotingId, setUpvotingId] = useState(null);
  const [upvotedIds, setUpvotedIds] = useState(() => new Set());
  const [notice, setNotice] = useState(null);

  const [mapCenter, setMapCenter] = useState(DEFAULT_CENTER);
  const [locating, setLocating] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setNotice(null);

    // 1) Preferred: the full board.
    try {
      const { data } = await axios.get(`${BASE_URL}/api/admin/issues`);
      if (Array.isArray(data)) {
        setIssues(data);
        setSource("all");
        setLoading(false);
        return;
      }
    } catch {
      /* fall through to citizen-scoped endpoints */
    }

    // 2) Fallback: this citizen's reports.
    try {
      const { data } = await axios.get(`${BASE_URL}/api/citizen/issues/mine`, {
        params: { reporter_id: reporterId },
      });
      if (Array.isArray(data)) {
        setIssues(data);
        setSource("mine");
        setNotice("Showing your reports — the full civic board is not available yet.");
        setLoading(false);
        return;
      }
    } catch {
      /* fall through */
    }

    setIssues([]);
    setError(
      "Could not load issues. Make sure the backend is running at " +
        BASE_URL +
        " and try again."
    );
    setLoading(false);
  }, [reporterId]);

  useEffect(() => {
    load();
  }, [load]);

  const stats = useMemo(() => {
    let pending = 0;
    let working = 0;
    let done = 0;
    let mine = 0;
    for (const issue of issues) {
      const status = normalizeStatus(issue.status);
      if (status === "Done") done += 1;
      else if (status === "Working") working += 1;
      else pending += 1;
      if (issue.reporter_id && issue.reporter_id === reporterId) mine += 1;
    }
    return { total: issues.length, pending, working, done, mine };
  }, [issues, reporterId]);

  const categories = useMemo(() => {
    const set = new Set();
    for (const issue of issues) {
      if (issue.category) set.add(issue.category);
    }
    return ["All", ...Array.from(set).sort()];
  }, [issues]);

  const visibleIssues = useMemo(() => {
    const filtered = issues.filter((issue) => {
      const byCategory =
        filterCategory === "All" || issue.category === filterCategory;
      const byStatus =
        filterStatus === "All" ||
        normalizeStatus(issue.status) === normalizeStatus(filterStatus);
      return byCategory && byStatus;
    });
    return filtered.sort(
      (a, b) => (Number(b.priority) || 0) - (Number(a.priority) || 0)
    );
  }, [issues, filterCategory, filterStatus]);

  async function handleUpvote(id) {
    if (upvotedIds.has(id) || upvotingId === id) return;
    setUpvotingId(id);
    setNotice(null);
    try {
      const { data } = await axios.post(
        `${BASE_URL}/api/citizen/issues/${id}/upvote`,
        { reporter_id: reporterId }
      );
      setUpvotedIds((prev) => new Set(prev).add(id));
      setIssues((prev) =>
        prev.map((issue) => (issue.id === id ? { ...issue, ...data } : issue))
      );
    } catch (err) {
      if (err.response?.status === 400) {
        setUpvotedIds((prev) => new Set(prev).add(id));
        setNotice("You already upvoted that report.");
      } else {
        setNotice("Upvote failed — please try again.");
      }
    } finally {
      setUpvotingId(null);
    }
  }

  function locateMe() {
    if (!navigator.geolocation) {
      setNotice("Geolocation is not supported by this browser.");
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setMapCenter([pos.coords.latitude, pos.coords.longitude]);
        setLocating(false);
      },
      () => {
        setNotice("Could not detect your location.");
        setLocating(false);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  const selectStyle = {
    padding: "9px 12px",
    borderRadius: 8,
    border: "1px solid var(--border)",
    background: "var(--surface-2)",
    color: "var(--text)",
    fontSize: 13,
    cursor: "pointer",
  };

  return (
    <section>
      <style>{`@keyframes civic-spin { to { transform: rotate(360deg); } }
        .civic-spin { animation: civic-spin 1s linear infinite; }
        .civic-clamp { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }`}</style>

      <header className="page-header">
        <h1>
          <ClipboardList size={20} style={{ verticalAlign: "text-bottom" }} /> My Reports
        </h1>
        <p>
          Track reports, see every pin on the map, and upvote the issues that
          matter to your neighbourhood.
        </p>
      </header>

      {/* Summary pills */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginBottom: 18 }}>
        <Pill label="Total" value={stats.total} color="var(--brand)" />
        <Pill label="Pending" value={stats.pending} color="#ef4444" />
        <Pill label="In Progress" value={stats.working} color="#38bdf8" />
        <Pill label="Resolved" value={stats.done} color="#22c55e" />
        <Pill label="My Reports" value={stats.mine} color="var(--warning)" />
      </div>

      {notice ? (
        <div
          role="status"
          style={{
            display: "flex",
            gap: 10,
            alignItems: "center",
            padding: 12,
            marginBottom: 16,
            border: "1px solid var(--warning)",
            background: "rgba(245,158,11,.1)",
            borderRadius: "var(--radius)",
            color: "var(--warning)",
            fontSize: 13,
          }}
        >
          <AlertTriangle size={16} style={{ flexShrink: 0 }} />
          <span>{notice}</span>
        </div>
      ) : null}

      {/* Map */}
      <div style={{ ...cardStyle, marginBottom: 16 }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 12,
            marginBottom: 12,
            flexWrap: "wrap",
          }}
        >
          <div style={{ fontWeight: 700 }}>
            Issue map{" "}
            <span style={{ color: "var(--text-muted)", fontWeight: 400, fontSize: 13 }}>
              ({visibleIssues.length} pin{visibleIssues.length === 1 ? "" : "s"})
            </span>
          </div>
          <button
            type="button"
            onClick={locateMe}
            disabled={locating}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              padding: "8px 12px",
              borderRadius: 8,
              border: "1px solid var(--brand)",
              background: "rgba(56,189,248,.12)",
              color: "var(--brand)",
              fontWeight: 600,
              fontSize: 13,
              cursor: locating ? "wait" : "pointer",
            }}
          >
            {locating ? <Loader2 size={14} className="civic-spin" /> : <Navigation size={14} />}
            Near me
          </button>
        </div>
        <MapPicker center={mapCenter} issues={visibleIssues} zoom={13} />
      </div>

      {/* Filters */}
      <div
        style={{
          ...cardStyle,
          display: "flex",
          flexWrap: "wrap",
          gap: 12,
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            fontSize: 13,
            color: "var(--text-muted)",
            fontWeight: 600,
          }}
        >
          <Filter size={15} /> Filters
        </span>

        <label style={{ display: "inline-flex", alignItems: "center", gap: 8, fontSize: 13 }}>
          <span style={{ color: "var(--text-muted)" }}>Category</span>
          <select
            style={selectStyle}
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
          >
            {categories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>

        <label style={{ display: "inline-flex", alignItems: "center", gap: 8, fontSize: 13 }}>
          <span style={{ color: "var(--text-muted)" }}>Status</span>
          <select
            style={selectStyle}
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
          >
            {STATUS_FILTERS.map((s) => (
              <option key={s} value={s}>
                {s === "All" ? "All" : statusMeta(s).label}
              </option>
            ))}
          </select>
        </label>

        <button
          type="button"
          onClick={load}
          style={{
            marginLeft: "auto",
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            padding: "8px 12px",
            borderRadius: 8,
            border: "1px solid var(--border)",
            background: "var(--surface-2)",
            color: "var(--text)",
            fontWeight: 600,
            fontSize: 13,
            cursor: "pointer",
          }}
        >
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {/* Content */}
      {loading ? (
        <div
          style={{
            ...cardStyle,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 10,
            color: "var(--text-muted)",
          }}
        >
          <Loader2 size={18} className="civic-spin" /> Loading reports…
        </div>
      ) : error ? (
        <div
          role="alert"
          style={{
            ...cardStyle,
            borderColor: "var(--danger)",
            display: "flex",
            gap: 12,
            alignItems: "center",
          }}
        >
          <AlertTriangle color="var(--danger)" size={18} style={{ flexShrink: 0 }} />
          <span style={{ fontSize: 14, color: "var(--text)" }}>{error}</span>
        </div>
      ) : visibleIssues.length === 0 ? (
        <div style={{ ...cardStyle, textAlign: "center", color: "var(--text-muted)" }}>
          <MapPin size={26} style={{ marginBottom: 8 }} />
          <p style={{ margin: "0 0 14px" }}>
            {issues.length === 0
              ? "No reports yet. Be the first to flag something for your area."
              : "No reports match these filters."}
          </p>
          <Link
            to="/report"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              padding: "10px 16px",
              borderRadius: 8,
              background: "var(--brand-strong)",
              color: "#04121f",
              fontWeight: 700,
              fontSize: 14,
            }}
          >
            <MapPin size={16} /> Report an issue
          </Link>
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))",
            gap: 16,
          }}
        >
          {visibleIssues.map((issue) => {
            const meta = statusMeta(issue.status);
            const Icon = categoryIcon(issue.category);
            const resolved = normalizeStatus(issue.status) === "Done";
            const upvoted = upvotedIds.has(issue.id);
            const isMine = issue.reporter_id && issue.reporter_id === reporterId;

            return (
              <article
                key={issue.id}
                className="card"
                style={{ display: "flex", flexDirection: "column", gap: 10 }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    gap: 10,
                    alignItems: "center",
                  }}
                >
                  <span
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 6,
                      fontSize: 12,
                      fontWeight: 600,
                      color: "var(--text-muted)",
                    }}
                  >
                    <Icon size={15} /> {issue.category || "Uncategorised"}
                    {isMine ? (
                      <span
                        style={{
                          marginLeft: 4,
                          padding: "1px 7px",
                          borderRadius: 999,
                          fontSize: 10,
                          fontWeight: 700,
                          background: "rgba(56,189,248,.16)",
                          color: "var(--brand)",
                        }}
                      >
                        MINE
                      </span>
                    ) : null}
                  </span>
                  <span
                    style={{
                      padding: "3px 10px",
                      borderRadius: 999,
                      fontSize: 11,
                      fontWeight: 700,
                      color: meta.color,
                      background: `${meta.color}22`,
                      border: `1px solid ${meta.color}`,
                      whiteSpace: "nowrap",
                    }}
                  >
                    {meta.label}
                  </span>
                </div>

                <h3 style={{ margin: 0, fontSize: "1.02rem", lineHeight: 1.35 }}>
                  {issue.title || "Untitled issue"}
                </h3>

                {issue.description ? (
                  <p
                    className="civic-clamp"
                    style={{
                      margin: 0,
                      fontSize: 13,
                      lineHeight: 1.5,
                      color: "var(--text-muted)",
                    }}
                  >
                    {issue.description}
                  </p>
                ) : null}

                {/* Priority */}
                <div>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      fontSize: 11,
                      color: "var(--text-muted)",
                      marginBottom: 4,
                    }}
                  >
                    <span>Priority</span>
                    <strong style={{ color: priorityColor(issue.priority) }}>
                      {issue.priority ?? 0}
                    </strong>
                  </div>
                  <div
                    style={{
                      height: 6,
                      borderRadius: 999,
                      background: "var(--surface-2)",
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        width: `${Math.max(0, Math.min(100, Number(issue.priority) || 0))}%`,
                        height: "100%",
                        background: priorityColor(issue.priority),
                      }}
                    />
                  </div>
                </div>

                {/* Before & After proof for resolved issues */}
                {resolved && (issue.worker_photo_url || issue.photo_url) ? (
                  <div>
                    <div
                      style={{
                        fontSize: 12,
                        fontWeight: 700,
                        color: "var(--success)",
                        marginBottom: 8,
                      }}
                    >
                      Before &amp; After Resolution Proof
                    </div>
                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns: "1fr 1fr",
                        gap: 10,
                      }}
                    >
                      <ProofImage src={issue.photo_url} label="Before" />
                      <ProofImage src={issue.worker_photo_url} label="After" />
                    </div>
                  </div>
                ) : issue.photo_url ? (
                  <ProofImage src={issue.photo_url} label="Reported" />
                ) : null}

                {/* Footer */}
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    gap: 10,
                    marginTop: "auto",
                    paddingTop: 10,
                    borderTop: "1px solid var(--border)",
                  }}
                >
                  <div
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 12,
                      fontSize: 12,
                      color: "var(--text-muted)",
                    }}
                  >
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                      <ThumbsUp size={13} /> {issue.upvotes ?? 0}
                    </span>
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                      <Clock size={13} /> {formatDate(issue.created_at)}
                    </span>
                  </div>

                  {resolved ? (
                    <span
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 6,
                        fontSize: 12,
                        fontWeight: 700,
                        color: "var(--success)",
                      }}
                    >
                      <CheckCircle2 size={14} /> Resolved
                    </span>
                  ) : (
                    <button
                      type="button"
                      onClick={() => handleUpvote(issue.id)}
                      disabled={upvoted || upvotingId === issue.id}
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 6,
                        padding: "7px 12px",
                        borderRadius: 8,
                        border: `1px solid ${upvoted ? "var(--success)" : "var(--border)"}`,
                        background: upvoted ? "rgba(34,197,94,.14)" : "var(--surface-2)",
                        color: upvoted ? "var(--success)" : "var(--text)",
                        fontWeight: 600,
                        fontSize: 12,
                        cursor: upvoted || upvotingId === issue.id ? "default" : "pointer",
                      }}
                    >
                      {upvotingId === issue.id ? (
                        <Loader2 size={13} className="civic-spin" />
                      ) : (
                        <ThumbsUp size={13} />
                      )}
                      {upvoted ? "Upvoted" : "I See This Too (+1)"}
                    </button>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
