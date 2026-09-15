import React from 'react';

/**
 * SectionCard Component.
 *
 * Consistent wrapper card for dashboard capability panels.
 * Features a structured title bar, status badges or action buttons, and content container.
 */
export default function SectionCard({
  title,
  subtitle,
  icon,
  badge,
  badgeVariant = 'neutral',
  action,
  children,
  className = '',
}) {
  return (
    <div className={`section-card ${className}`}>
      <div className="section-card-header">
        <div className="section-card-title-group">
          {icon && <span className="section-card-icon">{icon}</span>}
          <div>
            <h2 className="section-card-title">{title}</h2>
            {subtitle && <p className="section-card-subtitle">{subtitle}</p>}
          </div>
        </div>

        <div className="section-card-actions">
          {badge && (
            <span className={`section-badge badge-${badgeVariant}`}>
              {badge}
            </span>
          )}
          {action}
        </div>
      </div>

      <div className="section-card-content">
        {children}
      </div>
    </div>
  );
}
