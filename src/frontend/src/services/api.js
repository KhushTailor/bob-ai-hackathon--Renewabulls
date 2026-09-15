/**
 * GridPulse API Client Service Layer.
 *
 * In development: uses Vite proxy (/api → http://127.0.0.1:8000).
 * In production (Vercel): points to the live Render backend.
 * Handles error responses strictly without fabricating data.
 */

// Production backend URL (Render). Used when VITE_API_URL env var is not set.
const RENDER_BACKEND = 'https://gridpulse-api-2zh2.onrender.com';

// Detect whether we are running on Vercel (production) or local dev.
// In local dev, window.location.hostname is 'localhost' or '127.0.0.1'.
const isLocalDev =
  typeof window !== 'undefined' &&
  (window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1');

const API_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : isLocalDev
  ? '/api'
  : `${RENDER_BACKEND}/api`;

/**
 * Generic JSON request helper with HTTP error handling.
 */
async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  try {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
      try {
        const errorData = await response.json();
        if (errorData?.detail) {
          errorMessage = typeof errorData.detail === 'string' 
            ? errorData.detail 
            : JSON.stringify(errorData.detail);
        }
      } catch {
        // Not a JSON error body
      }
      throw new Error(errorMessage);
    }

    return await response.json();
  } catch (err) {
    console.error(`[GridPulse API] Request to ${url} failed:`, err);
    throw err;
  }
}

/**
 * Fetch latest grid KPIs and system state.
 * GET /api/status
 */
export async function fetchStatus() {
  return await apiRequest('/status');
}

/**
 * Fetch active anomaly detection alerts.
 * GET /api/alerts
 */
export async function fetchAlerts() {
  return await apiRequest('/alerts');
}

/**
 * Fetch 72-hour electricity demand forecast.
 * GET /api/forecast?horizon_hours=72
 */
export async function fetchForecast(horizonHours = 72) {
  return await apiRequest(`/forecast?horizon_hours=${horizonHours}`);
}

/**
 * Fetch renewable energy fleet performance metrics.
 * GET /api/renewables
 */
export async function fetchRenewables() {
  return await apiRequest('/renewables');
}

/**
 * Fetch current AI Operator Brief.
 * GET /api/operator-brief
 */
export async function fetchOperatorBrief() {
  return await apiRequest('/operator-brief');
}

/**
 * Submit a single what-if action simulation.
 * POST /api/simulate
 */
export async function simulateAction(actionData) {
  return await apiRequest('/simulate', {
    method: 'POST',
    body: JSON.stringify(actionData),
  });
}

/**
 * Compare multiple what-if scenarios.
 * POST /api/simulate/compare
 */
export async function compareScenarios(scenarios) {
  return await apiRequest('/simulate/compare', {
    method: 'POST',
    body: JSON.stringify({ scenarios }),
  });
}
