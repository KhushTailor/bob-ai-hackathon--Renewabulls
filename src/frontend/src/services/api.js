/**
 * GridPulse API Client Service Layer.
 *
 * Communicates with the FastAPI backend over the configured development proxy (/api)
 * or direct base URL. Handles error responses strictly without fabricating data.
 */

const API_BASE = '/api';

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
