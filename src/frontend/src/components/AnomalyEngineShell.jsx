import React from 'react';
import SectionCard from './SectionCard';

/**
 * Anomaly & Red-Flag Engine Capability Shell (S10 Layout Shell).
 * Displays active anomaly alerts and severity summary.
 */
export default function AnomalyEngineShell({ alerts = [] }) {
  const criticalCount = alerts.filter(a => a.severity === 'CRITICAL').length;
  const warningCount = alerts.filter(a => a.severity === 'WARNING').length;
  const infoCount = alerts.filter(a => a.severity === 'INFO').length;

  const getAlertBadge = () => {
    if (criticalCount > 0) return { text: `${criticalCount} Critical`, variant: 'critical' };
    if (warningCount > 0) return { text: `${warningCount} Warning`, variant: 'warning' };
    return { text: 'All Nominal', variant: 'nominal' };
  };

  const badge = getAlertBadge();

  return (
    <SectionCard
      title="Anomaly & Red-Flag Engine"
      subtitle="16 deterministic operational rules evaluating grid stability limits"
      badge={badge.text}
      badgeVariant={badge.variant}
    >
      <div className="shell-summary-row">
        <div className="shell-stat">
          <span className="shell-stat-label">Critical Alerts</span>
          <span className={`shell-stat-value ${criticalCount > 0 ? 'text-critical' : ''}`}>
            {criticalCount}
          </span>
        </div>
        <div className="shell-stat">
          <span className="shell-stat-label">Warnings</span>
          <span className={`shell-stat-value ${warningCount > 0 ? 'text-warning' : ''}`}>
            {warningCount}
          </span>
        </div>
        <div className="shell-stat">
          <span className="shell-stat-label">Informational</span>
          <span className="shell-stat-value">{infoCount}</span>
        </div>
        <div className="shell-stat">
          <span className="shell-stat-label">Active Rules</span>
          <span className="shell-stat-value">16 Evaluated</span>
        </div>
      </div>

      <div className="alerts-preview-list">
        {alerts.length === 0 ? (
          <div className="empty-alerts">
            <span className="check-icon">✓</span>
            <span>No active anomaly alerts. All grid parameters within statutory bounds.</span>
          </div>
        ) : (
          alerts.map((alert, idx) => (
            <div key={alert.rule_id || idx} className={`alert-item alert-${alert.severity.toLowerCase()}`}>
              <div className="alert-badge-col">
                <span className={`alert-pill pill-${alert.severity.toLowerCase()}`}>
                  {alert.severity}
                </span>
                <span className="alert-rule">{alert.rule_id}</span>
              </div>
              <div className="alert-content-col">
                <span className="alert-title">{alert.title}</span>
                <span className="alert-desc">{alert.message || alert.description}</span>
              </div>
            </div>
          ))
        )}
      </div>

      <div className="shell-placeholder compact">
        <span className="shell-tag">Active Endpoint: GET /api/alerts</span>
      </div>
    </SectionCard>
  );
}
