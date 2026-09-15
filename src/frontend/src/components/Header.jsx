import React from 'react';

/**
 * GridPulse Application Header.
 *
 * Displays logo, title, control-room classification, last update timestamp,
 * refresh action, and the global system status indicator badge.
 */
export default function Header({ systemStatus, timestamp, onRefresh, isRefreshing }) {
  const getStatusBadge = () => {
    switch (systemStatus) {
      case 'CRITICAL':
        return {
          label: 'CRITICAL ALERT',
          className: 'status-badge critical',
          dotClass: 'status-dot critical pulse',
        };
      case 'WARNING':
        return {
          label: 'SYSTEM WARNING',
          className: 'status-badge warning',
          dotClass: 'status-dot warning pulse',
        };
      case 'NOMINAL':
      default:
        return {
          label: 'SYSTEM NOMINAL',
          className: 'status-badge nominal',
          dotClass: 'status-dot nominal',
        };
    }
  };

  const statusInfo = getStatusBadge();

  return (
    <header className="app-header">
      <div className="header-brand">
        <div className="brand-logo-container">
          <svg className="brand-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
          </svg>
          <div className="brand-text">
            <div className="brand-title-row">
              <span className="brand-title">GridPulse</span>
              <span className="prototype-tag">Decision-Support</span>
            </div>
            <span className="brand-subtitle">Grid Operations Dashboard</span>
          </div>
        </div>
      </div>

      <div className="header-meta">
        <div className="telemetry-time">
          <span className="time-label">Data Timestamp</span>
          <span className="time-value">{timestamp || 'Awaiting telemetry...'}</span>
        </div>

        <div className={statusInfo.className}>
          <span className={statusInfo.dotClass}></span>
          <span className="badge-text">{statusInfo.label}</span>
        </div>

        <button 
          className={`btn-refresh ${isRefreshing ? 'refreshing' : ''}`}
          onClick={onRefresh}
          disabled={isRefreshing}
          title="Refresh telemetry and evaluations"
        >
          <svg className="refresh-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M23 4v6h-6M1 20v-6h6" />
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
          </svg>
          <span>{isRefreshing ? 'Refreshing...' : 'Refresh'}</span>
        </button>
      </div>
    </header>
  );
}
