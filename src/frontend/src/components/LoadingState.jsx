import React from 'react';

/**
 * LoadingState Component.
 *
 * Clean industrial loading spinner and state indicator for telemetry data.
 */
export default function LoadingState({ message = 'Connecting to GridPulse telemetry...' }) {
  return (
    <div className="loading-container">
      <div className="loading-spinner"></div>
      <p className="loading-text">{message}</p>
    </div>
  );
}
