/**
 * Dev 3 — Citizen form: photo, category, GPS + duplicate alert.
 *
 * Endpoints (real contract from backend/models.py + routers/citizen_routes.py):
 *   GET  /api/citizen/issues/nearby?lat=&lon=&radius_m=  → pre-submit duplicate check
 *   POST /api/citizen/issues                             → multipart submit
 *   POST /api/citizen/issues/{id}/upvote                 → "upvote existing instead"
 *
 * Notes on the contract mapping:
 *   - Photos are sent as multipart (`photo`), so the canvas-compressed image is
 *     turned into a JPEG Blob and uploaded. The same compression also yields the
 *     Base64 data URL used for the instant "before" preview.
 *   - The backend has no `severity` column, so the 1–5 severity the citizen picks
 *     is persisted as a short tag appended to the description.
 *   - Duplicates surface two ways: proactively from /nearby, and from the submit
 *     response via `duplicate_of`.
 */

import { useEffect, useMemo, useState } from "react";
import axios from "axios";
import {
  AlertTriangle,
  Camera,
  CheckCircle2,
  Loader2,
  MapPin,
  Navigation,
  RefreshCw,
  ThumbsUp,
  X,
} from "lucide-react";
import { BASE_URL } from "../apiConfig";
import MapPicker from "../components/MapPicker.jsx";

// Keep in sync with models.Category (backend rejects anything else).
const CATEGORIES = [
  "Pothole",
  "Street Light",
  "Garbage",
  "Graffiti",
  "Water Logging",
  "Broken Road",
  "Sewage",
  "Other",
];

const REPORTER_KEY = "civicfix.reporter_id";
const DEFAULT_CENTER = [12.9716, 77.5946];
const DUPLICATE_RADIUS_M = 40;

const DUPLICATE_MESSAGE =
  "Duplicate Complaint Detected! Your report has automatically boosted the priority of an existing nearby issue.";

/* ------------------------------- helpers -------------------------------- */

/** Stable per-browser citizen id, shared with CitizenDashboard's upvotes. */
function getReporterId() {
  let id = null;
  try {
    id = localStorage.getItem(REPORTER_KEY);
  } catch {
    /* storage may be blocked; fall through to an in-memory id */
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

/**
 * Downscale an image to `maxWidth` and re-encode as JPEG at `quality`,
 * entirely client-side. Returns both the Base64 data URL (preview / before_image)
 * and a Blob ready for multipart upload.
 */
function compressImage(file, maxWidth = 800, quality = 0.7) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Could not read the selected file."));
    reader.onload = () => {
      const img = new Image();
      img.onerror = () => reject(new Error("That file does not look like an image."));
      img.onload = () => {
        const scale = Math.min(1, maxWidth / img.width);
        const width = Math.max(1, Math.round(img.width * scale));
        const height = Math.max(1, Math.round(img.height * scale));

        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext("2d");
        ctx.drawImage(img, 0, 0, width, height);

        const dataUrl = canvas.toDataURL("image/jpeg", quality);
        canvas.toBlob(
          (blob) => {
            if (!blob) {
              reject(new Error("Image compression failed."));
              return;
            }
            resolve({ dataUrl, blob });
          },
          "image/jpeg",
          quality
        );
      };
      img.src = reader.result;
    };
    reader.readAsDataURL(file);
  });
}

function formatKb(bytes) {
  return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

/* -------------------------------- styles -------------------------------- */

const cardStyle = {
  background: "var(--surface)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius)",
  padding: 18,
};

const labelStyle = {
  display: "block",
  fontSize: 12,
  fontWeight: 600,
  letterSpacing: "0.04em",
  textTransform: "uppercase",
  color: "var(--text-muted)",
  marginBottom: 6,
};

const inputStyle = {
  width: "100%",
  padding: "10px 12px",
  borderRadius: 8,
  border: "1px solid var(--border)",
  background: "var(--surface-2)",
  color: "var(--text)",
  fontSize: 14,
  outline: "none",
};

const fieldGap = { marginBottom: 16 };

/* ------------------------------- component ------------------------------ */

export default function ReportIssue() {
  const reporterId = useMemo(() => getReporterId(), []);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState(CATEGORIES[0]);
  const [severity, setSeverity] = useState(3);

  const [lat, setLat] = useState(null);
  const [lon, setLon] = useState(null);

  const [photoPreview, setPhotoPreview] = useState(null); // Base64 data URL ("before_image")
  const [photoBlob, setPhotoBlob] = useState(null);
  const [photoName, setPhotoName] = useState("");
  const [photoError, setPhotoError] = useState(null);

  const [gpsStatus, setGpsStatus] = useState("idle"); // idle | loading | error
  const [gpsError, setGpsError] = useState(null);

  const [duplicates, setDuplicates] = useState([]);
  const [upvoted, setUpvoted] = useState(() => new Set());

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null); // { issue, isDuplicate }
  const [showDuplicateBanner, setShowDuplicateBanner] = useState(false);

  const pin = lat != null && lon != null ? { lat, lon } : null;
  const mapCenter = pin ? [lat, lon] : DEFAULT_CENTER;
  const hasLocation = lat != null && lon != null;

  /* --- pre-submit duplicate detection (debounced on location/category) --- */
  useEffect(() => {
    if (!hasLocation) return undefined;
    const handle = setTimeout(async () => {
      try {
        const { data } = await axios.get(`${BASE_URL}/api/citizen/issues/nearby`, {
          params: { lat, lon, radius_m: DUPLICATE_RADIUS_M },
        });
        setDuplicates(Array.isArray(data?.duplicates) ? data.duplicates : []);
      } catch {
        setDuplicates([]); // nearby is a nice-to-have; never block the form
      }
    }, 500);
    return () => clearTimeout(handle);
  }, [lat, lon, category, hasLocation]);

  /* ------------------------------ handlers ------------------------------- */

  async function handlePhoto(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    setPhotoError(null);
    if (!file.type.startsWith("image/")) {
      setPhotoError("Please choose an image file (JPG or PNG).");
      return;
    }
    try {
      const { dataUrl, blob } = await compressImage(file);
      setPhotoPreview(dataUrl);
      setPhotoBlob(blob);
      setPhotoName(file.name);
    } catch (err) {
      setPhotoError(err.message || "Could not process that image.");
    }
  }

  function clearPhoto() {
    setPhotoPreview(null);
    setPhotoBlob(null);
    setPhotoName("");
    setPhotoError(null);
  }

  function detectLocation() {
    if (!navigator.geolocation) {
      setGpsStatus("error");
      setGpsError("Geolocation is not supported by this browser.");
      return;
    }
    setGpsStatus("loading");
    setGpsError(null);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLat(pos.coords.latitude);
        setLon(pos.coords.longitude);
        setGpsStatus("idle");
      },
      (err) => {
        setGpsStatus("error");
        setGpsError(
          err.code === err.PERMISSION_DENIED
            ? "Location permission denied — drop a pin on the map instead."
            : "Could not detect your location — drop a pin on the map instead."
        );
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
    );
  }

  async function upvoteExisting(id) {
    try {
      await axios.post(`${BASE_URL}/api/citizen/issues/${id}/upvote`, {
        reporter_id: reporterId,
      });
      setUpvoted((prev) => new Set(prev).add(id));
    } catch (err) {
      if (err.response?.status === 400) {
        setUpvoted((prev) => new Set(prev).add(id)); // already voted — treat as done
      } else {
        setError("Could not record your upvote. Please try again.");
      }
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);
    setResult(null);

    if (title.trim().length < 3) {
      setError("Give the issue a title of at least 3 characters.");
      return;
    }
    if (!hasLocation) {
      setError("Add a location — use “Detect My Location” or click the map.");
      return;
    }

    const taggedDescription = severity
      ? `${description.trim()}\n\n[Reported severity: ${severity}/5]`.trim()
      : description.trim();

    const form = new FormData();
    form.append("title", title.trim());
    form.append("description", taggedDescription.slice(0, 1000));
    form.append("category", category);
    form.append("latitude", String(lat));
    form.append("longitude", String(lon));
    form.append("reporter_id", reporterId);
    if (photoBlob) {
      form.append("photo", photoBlob, photoName || "before.jpg");
    }

    setSubmitting(true);
    try {
      const { data } = await axios.post(`${BASE_URL}/api/citizen/issues`, form);
      const isDuplicate = data?.is_duplicate === true || Boolean(data?.duplicate_of);
      setResult({ issue: data, isDuplicate });
      setShowDuplicateBanner(isDuplicate);
      setDuplicates([]);
    } catch (err) {
      const status = err.response?.status;
      const detail = err.response?.data?.detail;
      if (status === 409) {
        // Backend chose the "reject" duplicate strategy.
        setShowDuplicateBanner(true);
        setResult({ issue: err.response?.data?.existing || null, isDuplicate: true });
      } else {
        setError(
          typeof detail === "string"
            ? detail
            : "Submission failed. Check the backend is running and try again."
        );
      }
    } finally {
      setSubmitting(false);
    }
  }

  function reportAnother() {
    setTitle("");
    setDescription("");
    setCategory(CATEGORIES[0]);
    setSeverity(3);
    setLat(null);
    setLon(null);
    clearPhoto();
    setResult(null);
    setShowDuplicateBanner(false);
    setDuplicates([]);
    setError(null);
  }

  return (
    <section>
      {/* Scoped spinner keyframes — keeps the page self-contained without
          touching the locked global stylesheet. */}
      <style>{`@keyframes civic-spin { to { transform: rotate(360deg); } }
        .civic-spin { animation: civic-spin 1s linear infinite; }
        .civic-clamp { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }`}</style>

      <header className="page-header">
        <h1>
          <MapPin size={20} style={{ verticalAlign: "text-bottom" }} /> Report an Issue
        </h1>
        <p>
          Pin the location, add a photo, and submit. We check for nearby
          duplicates automatically and boost their priority when you agree.
        </p>
      </header>

      {/* Duplicate alert — exact wording from the brief. */}
      {showDuplicateBanner ? (
        <div
          role="alert"
          style={{
            display: "flex",
            gap: 12,
            alignItems: "flex-start",
            padding: 16,
            marginBottom: 18,
            border: "1px solid var(--warning)",
            background: "rgba(245, 158, 11, 0.12)",
            borderRadius: "var(--radius)",
          }}
        >
          <AlertTriangle color="var(--warning)" size={22} style={{ flexShrink: 0 }} />
          <div>
            <div style={{ fontWeight: 700, color: "var(--warning)", marginBottom: 4 }}>
              {DUPLICATE_MESSAGE}
            </div>
            <div style={{ color: "var(--text-muted)", fontSize: 14 }}>
              Another citizen already reported something very close by. Your
              report has been linked to it and its priority was increased.
            </div>
          </div>
        </div>
      ) : null}

      {/* Success card */}
      {result && !result.isDuplicate ? (
        <div
          role="status"
          style={{
            display: "flex",
            gap: 12,
            alignItems: "flex-start",
            padding: 16,
            marginBottom: 18,
            border: "1px solid var(--success)",
            background: "rgba(34, 197, 94, 0.1)",
            borderRadius: "var(--radius)",
          }}
        >
          <CheckCircle2 color="var(--success)" size={22} style={{ flexShrink: 0 }} />
          <div>
            <div style={{ fontWeight: 700, color: "var(--success)", marginBottom: 4 }}>
              Report submitted — thank you!
            </div>
            <div style={{ color: "var(--text-muted)", fontSize: 14 }}>
              {result.issue?.title
                ? `“${result.issue.title}” is now queued at priority ${result.issue.priority ?? "—"}. Track it on My Reports.`
                : "Your issue is on the board."}
            </div>
          </div>
        </div>
      ) : null}

      {/* Error banner */}
      {error ? (
        <div
          role="alert"
          style={{
            display: "flex",
            gap: 12,
            alignItems: "center",
            padding: 14,
            marginBottom: 18,
            border: "1px solid var(--danger)",
            background: "rgba(239, 68, 68, 0.1)",
            borderRadius: "var(--radius)",
            color: "var(--danger)",
            fontSize: 14,
          }}
        >
          <AlertTriangle size={18} style={{ flexShrink: 0 }} />
          <span>{error}</span>
        </div>
      ) : null}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
          gap: 20,
          alignItems: "start",
        }}
      >
        {/* ------------------------------ form ------------------------------ */}
        <form style={cardStyle} onSubmit={handleSubmit}>
          {/* Photo / before_image */}
          <div style={fieldGap}>
            <label style={labelStyle}>
              <Camera size={13} style={{ verticalAlign: "text-bottom" }} /> Photo
            </label>

            {photoPreview ? (
              <div style={{ position: "relative" }}>
                <img
                  src={photoPreview}
                  alt="Before"
                  style={{
                    width: "100%",
                    height: 200,
                    objectFit: "cover",
                    borderRadius: 8,
                    border: "1px solid var(--border)",
                  }}
                />
                <span
                  style={{
                    position: "absolute",
                    top: 8,
                    left: 8,
                    padding: "2px 8px",
                    borderRadius: 999,
                    fontSize: 11,
                    fontWeight: 700,
                    background: "rgba(15,23,42,.8)",
                    color: "var(--text)",
                  }}
                >
                  Before
                </span>
                <button
                  type="button"
                  onClick={clearPhoto}
                  aria-label="Remove photo"
                  style={{
                    position: "absolute",
                    top: 8,
                    right: 8,
                    display: "inline-flex",
                    padding: 6,
                    borderRadius: 999,
                    border: "none",
                    background: "rgba(15,23,42,.8)",
                    color: "var(--text)",
                    cursor: "pointer",
                  }}
                >
                  <X size={14} />
                </button>
                <div style={{ marginTop: 6, fontSize: 12, color: "var(--text-muted)" }}>
                  Compressed to {photoBlob ? formatKb(photoBlob.size) : "—"} (max 800px, JPEG 70%).
                </div>
              </div>
            ) : (
              <label
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 8,
                  padding: "28px 16px",
                  borderRadius: 8,
                  border: "1px dashed var(--border)",
                  background: "var(--surface-2)",
                  color: "var(--text-muted)",
                  cursor: "pointer",
                  textAlign: "center",
                  fontSize: 13,
                }}
              >
                <Camera size={26} />
                <span>Click to upload a photo</span>
                <span style={{ fontSize: 11 }}>
                  Resized on your device before uploading.
                </span>
                <input
                  type="file"
                  accept="image/*"
                  onChange={handlePhoto}
                  style={{ display: "none" }}
                />
              </label>
            )}
            {photoError ? (
              <div style={{ marginTop: 6, fontSize: 12, color: "var(--danger)" }}>
                {photoError}
              </div>
            ) : null}
          </div>

          {/* Title */}
          <div style={fieldGap}>
            <label style={labelStyle} htmlFor="ri-title">
              Title
            </label>
            <input
              id="ri-title"
              style={inputStyle}
              value={title}
              maxLength={120}
              placeholder="e.g. Deep pothole outside the market"
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>

          {/* Category + severity */}
          <div style={{ ...fieldGap, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div>
              <label style={labelStyle} htmlFor="ri-category">
                Category
              </label>
              <select
                id="ri-category"
                style={{ ...inputStyle, cursor: "pointer" }}
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              >
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label style={labelStyle}>Severity (1–5)</label>
              <div style={{ display: "flex", gap: 6 }}>
                {[1, 2, 3, 4, 5].map((level) => {
                  const active = severity === level;
                  return (
                    <button
                      key={level}
                      type="button"
                      onClick={() => setSeverity(level)}
                      aria-pressed={active}
                      style={{
                        flex: 1,
                        padding: "9px 0",
                        borderRadius: 8,
                        border: `1px solid ${active ? "var(--brand)" : "var(--border)"}`,
                        background: active ? "rgba(56,189,248,.16)" : "var(--surface-2)",
                        color: active ? "var(--brand)" : "var(--text-muted)",
                        fontWeight: 700,
                        cursor: "pointer",
                      }}
                    >
                      {level}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Description */}
          <div style={fieldGap}>
            <label style={labelStyle} htmlFor="ri-description">
              Description
            </label>
            <textarea
              id="ri-description"
              style={{ ...inputStyle, minHeight: 110, resize: "vertical" }}
              value={description}
              maxLength={900}
              placeholder="Describe what you see and anything that helps the crew find it."
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              width: "100%",
              padding: "12px 16px",
              borderRadius: 8,
              border: "none",
              background: submitting ? "var(--surface-2)" : "var(--brand-strong)",
              color: submitting ? "var(--text-muted)" : "#04121f",
              fontWeight: 700,
              fontSize: 15,
              cursor: submitting ? "not-allowed" : "pointer",
            }}
          >
            {submitting ? <Loader2 size={18} className="civic-spin" /> : <MapPin size={18} />}
            {submitting ? "Submitting…" : "Submit report"}
          </button>

          {result ? (
            <button
              type="button"
              onClick={reportAnother}
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 8,
                width: "100%",
                marginTop: 10,
                padding: "10px 16px",
                borderRadius: 8,
                border: "1px solid var(--border)",
                background: "transparent",
                color: "var(--text)",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              <RefreshCw size={16} /> Report another issue
            </button>
          ) : null}
        </form>

        {/* --------------------------- location side --------------------------- */}
        <div style={{ display: "grid", gap: 16 }}>
          <div style={cardStyle}>
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
              <div>
                <div style={{ fontWeight: 700, marginBottom: 2 }}>Location</div>
                <div style={{ fontSize: 13, color: "var(--text-muted)" }}>
                  {hasLocation
                    ? `${lat.toFixed(5)}, ${lon.toFixed(5)}`
                    : "Detect your location or click the map."}
                </div>
              </div>
              <button
                type="button"
                onClick={detectLocation}
                disabled={gpsStatus === "loading"}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "9px 14px",
                  borderRadius: 8,
                  border: "1px solid var(--brand)",
                  background: "rgba(56,189,248,.12)",
                  color: "var(--brand)",
                  fontWeight: 600,
                  fontSize: 13,
                  cursor: gpsStatus === "loading" ? "wait" : "pointer",
                }}
              >
                {gpsStatus === "loading" ? (
                  <Loader2 size={15} className="civic-spin" />
                ) : (
                  <Navigation size={15} />
                )}
                Detect My Location
              </button>
            </div>

            {gpsError ? (
              <div style={{ fontSize: 12, color: "var(--warning)", marginBottom: 10 }}>
                {gpsError}
              </div>
            ) : null}

            <MapPicker
              center={mapCenter}
              position={pin}
              setPosition={(pt) => {
                setLat(pt.lat);
                setLon(pt.lon);
              }}
            />
            <div style={{ marginTop: 8, fontSize: 12, color: "var(--text-muted)" }}>
              Tip: click anywhere on the map to move the pin.
            </div>
          </div>

          {/* Nearby duplicates (pre-submit) */}
          {duplicates.length > 0 ? (
            <div
              style={{
                ...cardStyle,
                borderColor: "var(--warning)",
                background: "rgba(245,158,11,.08)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  gap: 8,
                  alignItems: "center",
                  fontWeight: 700,
                  color: "var(--warning)",
                  marginBottom: 8,
                }}
              >
                <AlertTriangle size={16} /> {duplicates.length} nearby report
                {duplicates.length > 1 ? "s" : ""} found
              </div>
              <div style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 12 }}>
                Something similar is already on the board. Upvoting it raises its
                priority instead of creating a duplicate.
              </div>
              <div style={{ display: "grid", gap: 10 }}>
                {duplicates.map((dup) => (
                  <div
                    key={dup.id}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      gap: 10,
                      alignItems: "center",
                      padding: 10,
                      borderRadius: 8,
                      background: "var(--surface-2)",
                    }}
                  >
                    <div style={{ minWidth: 0 }}>
                      <div
                        style={{
                          fontWeight: 600,
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                        }}
                      >
                        {dup.title || "Nearby issue"}
                      </div>
                      <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
                        {dup.category} · Priority {dup.priority ?? "—"}
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => upvoteExisting(dup.id)}
                      disabled={upvoted.has(dup.id)}
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 6,
                        flexShrink: 0,
                        padding: "7px 10px",
                        borderRadius: 8,
                        border: "1px solid var(--border)",
                        background: upvoted.has(dup.id) ? "var(--success)" : "var(--surface)",
                        color: upvoted.has(dup.id) ? "#04121f" : "var(--text)",
                        fontWeight: 600,
                        fontSize: 12,
                        cursor: upvoted.has(dup.id) ? "default" : "pointer",
                      }}
                    >
                      <ThumbsUp size={13} />
                      {upvoted.has(dup.id) ? "Upvoted" : "I see this too (+1)"}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}
