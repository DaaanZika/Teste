import axios from 'axios'

/**
 * Single axios instance for the whole app. No component talks to
 * `fetch`/`axios` directly — everything goes through `api/*` (see
 * src/api/), which uses this client. Base URL is configured via
 * `VITE_API_BASE_URL`; nothing secret ever lives here (PROMPT 2 §32).
 */
export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000',
  timeout: 30_000,
  // Session cookies (Google login) are cross-origin (frontend/backend run
  // on different ports even in dev) — without this the browser never
  // sends or stores them. Harmless when auth_provider="local" (no cookie
  // is ever set), see backend/app/core/security.py.
  withCredentials: true,
})
