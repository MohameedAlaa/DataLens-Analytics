import axios from 'axios';

/**
 * Safely extracts a user-friendly error message from any error response.
 * Handles FastAPI Pydantic arrays, string details, object details, HTML error pages, and network dropouts.
 * Guarantees a clean string output without raw stack traces or raw objects that crash React rendering.
 */
export function extractErrorMessage(error, defaultMsg = 'An unexpected error occurred') {
  if (!error) return defaultMsg;

  // 1. If it's already a clean string
  if (typeof error === 'string') return error;

  // 2. Axios response error
  if (error.response) {
    const data = error.response.data;
    const status = error.response.status;

    // Check if response is HTML (e.g. 502/504 Bad Gateway from proxy)
    if (typeof data === 'string') {
      if (data.trim().startsWith('<!DOCTYPE') || data.trim().startsWith('<html')) {
        return `Server error (${status}): Service temporarily unavailable.`;
      }
      return data;
    }

    if (data && typeof data === 'object') {
      const detail = data.detail;

      // Case A: Pydantic validation error array: [{loc: [...], msg: "..."}]
      if (Array.isArray(detail)) {
        return detail
          .map((err) => {
            const loc = Array.isArray(err.loc) ? err.loc.join('.') : '';
            return loc ? `${err.msg} (${loc})` : err.msg || 'Invalid field';
          })
          .join('; ');
      }

      // Case B: Detail is an object
      if (detail && typeof detail === 'object') {
        try {
          return JSON.stringify(detail);
        } catch {
          return defaultMsg;
        }
      }

      // Case C: Detail is a string
      if (typeof detail === 'string') {
        return detail;
      }

      // Case D: Error or message field
      if (data.error && typeof data.error === 'string') {
        return data.error;
      }
      if (data.message && typeof data.message === 'string') {
        return data.message;
      }
    }

    return `Request failed with status ${status}`;
  }

  // 3. Request aborted / cancelled
  if (axios.isCancel(error) || error.name === 'CanceledError' || error.name === 'AbortError') {
    return 'Request was cancelled';
  }

  // 4. Network error / timeout
  if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
    return 'Request timed out. Please try again.';
  }
  if (error.message === 'Network Error') {
    return 'Network error: Please check your connection to the server.';
  }

  // 5. Standard Error object
  if (error.message && typeof error.message === 'string') {
    return error.message;
  }

  return defaultMsg;
}

/**
 * Resolves the API base URL.
 * In production with a persistent FastAPI backend (Option A), VITE_API_BASE_URL directs
 * requests directly to the persistent backend (e.g. 'https://api.datalens.example.com').
 * Defaults to '/api' for local dev proxying and single-origin deployments.
 */
const getApiBaseUrl = () => {
  try {
    if (typeof import.meta !== 'undefined' && import.meta.env) {
      if (import.meta.env.VITE_API_BASE_URL) {
        return import.meta.env.VITE_API_BASE_URL.trim().replace(/\/+$/, '');
      }
      if (import.meta.env.PROD && typeof window !== 'undefined') {
        console.warn(
          '[DataLens] VITE_API_BASE_URL is not configured in this production build. Requests will route to relative "/api". ' +
          'Ensure requests reach the persistent FastAPI backend rather than serverless adapters.'
        );
      }
    }
  } catch {
    // In test / non-Vite environments
  }
  return '/api';
};

/**
 * Creates a configured axios instance for DataLens API requests
 */
export const apiClient = axios.create({
  baseURL: getApiBaseUrl(),
  timeout: 30000, // 30s timeout
  headers: {
    'Accept': 'application/json',
  },
});

