import { MapContainer, Marker, TileLayer } from "react-leaflet";
import L from "leaflet";

/**
 * Dev 3 — Leaflet map component for pin-dropping & viewing nearby issues.
 *
 * Reusable between ReportIssue (drop a pin) and CitizenDashboard
 * (view nearby issues), so keep it prop-driven and page-agnostic.
 *
 * ============================ PROP CONTRACT ============================
 * Prop                 Type                                     Used by
 * ----------------------------------------------------------------------------
 * center      | [number, number]      | default [lat, lon] fallback view
 * zoom        | number                | default 16
 * position    | {lat, lon} | null     | controlled pin (ReportIssue, read-only)
 * onPick      | ({lat, lon}) => void  | click-to-drop-pins callback
 * markers     | Array<{id, lat, lon, title, status}>  | nearby issues (Dashboard)
 * onMarkerClick | (id) => void         | optional marker click handler
 *
 * `center` and `position` are in [lat, lon] order for react-leaflet, but
 * remember the API takes longitude FIRST when building GeoJSON: [lon, lat].
 * =======================================================================
 *
 * TODO(Dev 3):
 *   1. Default `center` from navigator.geolocation (watch out for the async
 *      permission prompt — keep a sensible fallback so the map still renders).
 *   2. When `onPick` is provided, attach a click handler to the map via
 *      `useMapEvents(({ latlng }) => onPick({ lat: latlng.lat, lon: latlng.lng }))`
 *      in a small child component — `useMapEvents` must live inside
 *      `MapContainer`.
 *   3. Render a `<Marker>` for `position` when set (pin drop).
 *   4. Render `markers` as `<Marker>` entries; colour them by `status`
 *      (Yet to Start / Working / Done) using a custom `divIcon`.
 *   5. Pass the clicked marker's id to `onMarkerClick`.
 *
 * Styling: `.map-picker` in index.css already gives the container a height —
 * Leaflet silently renders a 0-height box without it.
 */

const DEFAULT_CENTER = [12.9716, 77.5946]; // Bengaluru; swap for your city

// Leaflet's default marker icons 404 under bundlers because it resolves
// image paths relative to the CSS. Point them at the CDN copy instead.
// (This is a known Leaflet + Vite quirk — leave it in place.)
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

export default function MapPicker({
  center = DEFAULT_CENTER,
  zoom = 16,
  position = null,
  onPick = null,
  markers = [],
  onMarkerClick = null,
}) {
  return (
    <div className="map-picker">
      <MapContainer center={center} zoom={zoom} className="map-picker-container">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* TODO(Dev 3): controlled pin for the report form */}
        {position ? <Marker position={[position.lat, position.lon]} /> : null}

        {/* TODO(Dev 3): nearby issues, coloured by status */}
        {markers.map((m) => (
          <Marker
            key={m.id}
            position={[m.lat, m.lon]}
            eventHandlers={onMarkerClick ? { click: () => onMarkerClick(m.id) } : undefined}
          />
        ))}
      </MapContainer>
    </div>
  );
}
