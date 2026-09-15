import React from 'react';

/**
 * ErrorState Component.
 *
 * Explicit error indicator. Ensures errors are never silently suppressed or
 * replaced with fabricated telemetry.
 */
export default function ErrorState({ error, onRetry, title = 'Telemetry Connection Failure' }) {
  const errorMessage = error?.message || (typeof error === 'string' ? error : 'Failed to connect to backend service.');

  return (
    <div className="error-container">
      <div className="error-icon-box">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
      </div>
      <h3 className="error-title">{title}</h3>
      <p className="error-description">{errorMessage}</p>
      <div className="error-guidance">
        Verify that the FastAPI backend is running on <code>http://127.0.0.1:8000</code> and the dataset is accessible.
      </div>
      {onRetry && (
        <button className="btn-retry" onClick={onRetry}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M23 4v6h-6M1 20v-6h6" />
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
          </svg>
          Retry Connection
        </button>
      )}
    </div>
  );
}
