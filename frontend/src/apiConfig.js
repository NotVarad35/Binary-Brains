/**
 * Exported API base URL — switch between localhost and prod.
 *
 * LOCKED shared file. All axios calls go through this so flipping between
 * local dev and a deployed backend is a single env var, not a code edit.
 *
 * Usage:
 *   import { BASE_URL } from "../apiConfig";
 *   axios.get(`${BASE_URL}/api/citizen/issues/nearby`, { params: { lat, lon } });
 */

// Vite inlines `import.meta.env.VITE_*` at build time.
const RAW_BASE_URL = import.meta.env.VITE_API_URL;

/**
 * Backend origin with no trailing slash.
 * - Set `VITE_API_URL` in `frontend/.env` for prod (e.g. https://api.example.com)
 * - Leave unset in dev to hit http://localhost:8000
 */
export const BASE_URL = (RAW_BASE_URL || "http://localhost:8000").replace(/\/+$/, "");

/** Convenience helper so route paths stay consistent across the app. */
export const api = (path) => `${BASE_URL}${path}`;

export default BASE_URL;
