import React from 'react';

/**
 * StatusCard Component.
 *
 * Displays a single primary operational metric with high information density,
 * unit, optional secondary context/change, and color-coded status styling.
 */
export default function StatusCard({
  label,
  value,
  unit,
  subtext,
  status = 'neutral', // 'neutral' | 'nominal' | 'warning' | 'critical' | 'accent'
  icon,
}) {
  return (
    <div className={`status-card status-${status}`}>
      <div className="status-card-header">
        <span className="status-card-label">{label}</span>
        {icon && <span className="status-card-icon">{icon}</span>}
      </div>

      <div className="status-card-body">
        <div className="status-card-metric">
          <span className="status-card-value">{value}</span>
          {unit && <span className="status-card-unit">{unit}</span>}
        </div>
        {subtext && <div className="status-card-subtext">{subtext}</div>}
      </div>
    </div>
  );
}
