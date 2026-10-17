/**
 * Dev 3 — Leaflet map component for pin-dropping & viewing civic issues.
 *
 * Two usage modes, both prop-driven so the component stays page-agnostic:
 *
 *   Picker mode   <MapPicker position={pin} setPosition={setPin} />
 *                 (an `onPick` callback works too). Clicking the map drops a
 *                 pin and reports `{ lat, lon }` back to the parent.
 *
 *   Display mode  <MapPicker issues={issues} />  (legacy `markers` still works)
 *                 Renders one colour-coded marker per issue; each popup shows
 *                 the title, category, a status badge and the priority score.
 *
 * Props: center, zoom, position, setPosition, onPick, issues, markers,
 *        onMarkerClick, style, scrollWheelZoom.
 *
 * NOTE on ordering: `center`, `position` and marker positions are [lat, lon]
 * for react-leaflet, whereas the API's GeoJSON `coordinates` are [lon, lat].
 */

import { useEffect } from "react";
import {
  MapContainer,
  Marker,
  Popup,
  TileLayer,
  useMap,
  useMapEvents,
} from "react-leaflet";
import L from "leaflet";

// --- Default marker icons -------------------------------------------------
// Leaflet's stock icons 404 under bundlers (they're resolved relative to the
// CSS). Resolving the PNGs through the package via Vite gives hashed, always
// valid URLs — no broken images, and no reliance on a CDN at runtime.
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

// Local city fallback (Bengaluru) so the map always has a sane view.
const DEFAULT_CENTER = [12.9716, 77.5946];

// Shared status palette — mirrors the badges used across the app.
const STATUS_META = {
  "Yet to Start": { color: "#ef4444", label: "Pending" },
  Working: { color: "#38bdf8", label: "In Progress" },
  Done: { color: "#22c55e", label: "Resolved" },
};

/** Accept "Working", "WORKING", "in_progress"… and return a canonical key. */
export function normalizeStatus(status) {
  const raw = String(status ?? "")
    .trim()
    .toUpperCase()
    .replace(/[\s-]+/g, "_");
  if (raw === "YET_TO_START" || raw === "PENDING") return "Yet to Start";
  if (raw === "WORKING" || raw === "IN_PROGRESS") return "Working";
  if (raw === "DONE" || raw === "RESOLVED") return "Done";
  return status ? String(status) : "Yet to Start";
}

function statusMeta(status) {
  return (
    STATUS_META[normalizeStatus(status)] || {
      color: "#94a3b8",
      label: status ? String(status) : "Unknown",
    }
  );
}

/** Colour-coded teardrop pin built with a Leaflet divIcon. */
function statusDivIcon(status) {
  const { color } = statusMeta(status);
  return L.divIcon({
    className: "map-status-marker",
    html:
      `<div style="width:18px;height:18px;background:${color};` +
      `border:2px solid #0b1220;border-radius:50% 50% 50% 0;` +
      `transform:rotate(-45deg);box-shadow:0 2px 6px rgba(0,0,0,.55);"></div>`,
    iconSize: [18, 18],
    iconAnchor: [9, 18],
    popupAnchor: [0, -16],
  });
}

/** Pull [lat, lon] out of either an IssueOut or a simplified {id,lat,lon} marker. */
function toLatLng(item) {
  if (!item) return null;
  const lat = item.latitude ?? item.lat;
  const lon = item.longitude ?? item.lon ?? item.lng;
  const nLat = Number(lat);
  const nLon = Number(lon);
  if (!Number.isFinite(nLat) || !Number.isFinite(nLon)) return null;
  return [nLat, nLon];
}

/** Attaches the click-to-drop handler. Must live inside <MapContainer>. */
function ClickToPick({ active, onPick }) {
  useMapEvents({
    click(event) {
      if (!active) return;
      onPick({ lat: event.latlng.lat, lon: event.latlng.lng });
    },
  });
  return null;
}

/** Re-centres the map whenever the controlled center changes. */
function Recenter({ center }) {
  const map = useMap();
  const lat = center?.[0];
  const lon = center?.[1];
  useEffect(() => {
    if (Number.isFinite(lat) && Number.isFinite(lon)) {
      map.setView([lat, lon], map.getZoom(), { animate: true });
    }
  }, [map, lat, lon]);
  return null;
}

/** Leaflet measures the container once; nudge it after layout settles. */
function ResizeFix() {
  const map = useMap();
  useEffect(() => {
    const fix = () => map.invalidateSize();
    const timer = setTimeout(fix, 200);
    let observer;
    if (typeof ResizeObserver !== "undefined") {
      observer = new ResizeObserver(fix);
      observer.observe(map.getContainer());
    }
    return () => {
      clearTimeout(timer);
      if (observer) observer.disconnect();
    };
  }, [map]);
  return null;
}

export default function MapPicker({
  center = DEFAULT_CENTER,
  zoom = 16,
  position = null,
  setPosition = null,
  onPick = null,
  issues = [],
  markers = [],
  onMarkerClick = null,
  style = undefined,
  scrollWheelZoom = true,
}) {
  const pinned = toLatLng(position);
  const pickEnabled = Boolean(onPick || setPosition);

  // Prefer full issue objects; fall back to the legacy `markers` prop.
  const points = (issues && issues.length ? issues : markers)
    .map((item) => ({ item, latlng: toLatLng(item) }))
    .filter((entry) => entry.latlng);

  const handlePick = (point) => {
    if (onPick) onPick(point);
    if (setPosition) setPosition(point);
  };

  const safeCenter =
    Array.isArray(center) &&
    Number.isFinite(Number(center[0])) &&
    Number.isFinite(Number(center[1]))
      ? [Number(center[0]), Number(center[1])]
      : DEFAULT_CENTER;

  return (
    <div className="map-picker" style={style}>
      <MapContainer
        center={safeCenter}
        zoom={zoom}
        className="map-picker-container"
        scrollWheelZoom={scrollWheelZoom}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <ClickToPick active={pickEnabled} onPick={handlePick} />
        <Recenter center={safeCenter} />
        <ResizeFix />

        {/* Picker mode: the dropped/controlled pin. */}
        {pinned ? (
          <Marker position={pinned}>
            <Popup autoPan>
              <strong>Selected location</strong>
              <br />
              {pinned[0].toFixed(5)}, {pinned[1].toFixed(5)}
            </Popup>
          </Marker>
        ) : null}

        {/* Display mode: every issue, coloured by status. */}
        {points.map(({ item, latlng }) => {
          const meta = statusMeta(item.status);
          return (
            <Marker
              key={item.id ?? `${latlng[0]},${latlng[1]}`}
              position={latlng}
              icon={statusDivIcon(item.status)}
              eventHandlers={
                onMarkerClick ? { click: () => onMarkerClick(item.id) } : undefined
              }
            >
              <Popup autoPan>
                <div style={{ minWidth: 170, color: "#0f172a", fontFamily: "inherit" }}>
                  <div style={{ fontWeight: 700, marginBottom: 4 }}>
                    {item.title || "Untitled issue"}
                  </div>
                  {item.category ? (
                    <div style={{ fontSize: 12, color: "#475569", marginBottom: 6 }}>
                      {item.category}
                    </div>
                  ) : null}
                  <span
                    style={{
                      display: "inline-block",
                      padding: "2px 8px",
                      borderRadius: 999,
                      fontSize: 11,
                      fontWeight: 700,
                      color: meta.color,
                      background: `${meta.color}22`,
                      border: `1px solid ${meta.color}`,
                    }}
                  >
                    {meta.label}
                  </span>
                  {Number.isFinite(Number(item.priority)) ? (
                    <div style={{ marginTop: 6, fontSize: 12, color: "#334155" }}>
                      Priority: <strong>{item.priority}</strong>
                    </div>
                  ) : null}
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
}
