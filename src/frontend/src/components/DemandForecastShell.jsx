import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';
import SectionCard from './SectionCard';

/**
 * Custom Tooltip for the 72-hour Demand Forecast Chart.
 */
function ForecastTooltip({ active, payload, label }) {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="chart-tooltip">
        <div className="tooltip-time">{data.formattedTimeFull}</div>
        <div className="tooltip-metric">
          <span className="tooltip-label">Projected Demand:</span>
          <span className="tooltip-val">{data.predicted_demand_mw.toFixed(1)} MW</span>
        </div>
        <div className="tooltip-badge">72-Hour Statistical Forecast</div>
      </div>
    );
  }
  return null;
}

/**
 * Demand Forecasting Dashboard Panel (Stage S11).
 *
 * Visualizes the 72-hour / 288-point demand forecast using Recharts.
 * Clearly labels the series as a projection rather than measured real-time demand.
 */
export default function DemandForecastShell({ forecast, loading, error }) {
  if (error) {
    return (
      <SectionCard
        title="Demand Forecasting"
        subtitle="72-hour electricity demand forecast"
        badge="Error"
        badgeVariant="critical"
      >
        <div className="shell-error-box">
          <p className="error-text">Failed to load forecast: {error.message || 'API error'}</p>
        </div>
      </SectionCard>
    );
  }

  const rawPoints = forecast?.points || [];
  const totalPoints = rawPoints.length;

  // Process data points for Recharts with readable timestamps
  const chartData = rawPoints.map((pt, idx) => {
    const d = new Date(pt.timestamp);
    // Format: "01 Jul 12:00"
    const day = d.getUTCDate().toString().padStart(2, '0');
    const month = d.toLocaleString('en-US', { month: 'short', timeZone: 'UTC' });
    const hours = d.getUTCHours().toString().padStart(2, '0');
    const mins = d.getUTCMinutes().toString().padStart(2, '0');

    return {
      index: idx,
      timestamp: pt.timestamp,
      formattedTime: `${day} ${month} ${hours}:${mins}`,
      tickLabel: `${day} ${month} ${hours}:00`,
      formattedTimeFull: `${day} ${month} ${hours}:${mins} UTC`,
      predicted_demand_mw: pt.predicted_demand_mw,
    };
  });

  // Calculate summary metrics
  const demandValues = chartData.map(d => d.predicted_demand_mw);
  const peakDemand = demandValues.length > 0 ? Math.max(...demandValues) : 0;
  const minDemand = demandValues.length > 0 ? Math.min(...demandValues) : 0;
  const avgDemand = demandValues.length > 0 
    ? demandValues.reduce((a, b) => a + b, 0) / demandValues.length 
    : 0;

  // Find peak and trough timestamps
  const peakPoint = chartData.find(d => d.predicted_demand_mw === peakDemand);
  const minPoint = chartData.find(d => d.predicted_demand_mw === minDemand);

  const modelName = forecast?.model_used || 'Seasonal-Naive STL';

  return (
    <SectionCard
      title="Demand Forecasting"
      subtitle="72-hour forward electricity demand projection (15-min resolution)"
      badge="Projection • 72h"
      badgeVariant="accent"
    >
      {/* Forecast Metadata & Statistics Ribbon */}
      <div className="shell-summary-row forecast-ribbon">
        <div className="shell-stat">
          <span className="shell-stat-label">Forecast Horizon</span>
          <span className="shell-stat-value">72 Hours</span>
          <span className="shell-stat-meta">{totalPoints} Forecast Points</span>
        </div>

        <div className="shell-stat">
          <span className="shell-stat-label">Projected Peak</span>
          <span className="shell-stat-value text-accent">{peakDemand.toFixed(1)} MW</span>
          <span className="shell-stat-meta">{peakPoint ? peakPoint.formattedTime : '—'}</span>
        </div>

        <div className="shell-stat">
          <span className="shell-stat-label">Projected Trough</span>
          <span className="shell-stat-value">{minDemand.toFixed(1)} MW</span>
          <span className="shell-stat-meta">{minPoint ? minPoint.formattedTime : '—'}</span>
        </div>

        <div className="shell-stat">
          <span className="shell-stat-label">Average Demand</span>
          <span className="shell-stat-value">{avgDemand.toFixed(1)} MW</span>
          <span className="shell-stat-meta">Model: {modelName}</span>
        </div>
      </div>

      {/* Visual Indication: Projection Notice */}
      <div className="forecast-banner">
        <span className="forecast-banner-dot"></span>
        <span className="forecast-banner-text">
          <strong>STATISTICAL PROJECTION:</strong> Values represent predicted regional demand across the next 72 hours, not physical real-time measurements.
        </span>
      </div>

      {/* Recharts Area Chart */}
      <div className="chart-container" style={{ width: '100%', height: 260 }}>
        {totalPoints === 0 ? (
          <div className="empty-chart-box">Awaiting forecast points from backend...</div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 15, left: -10, bottom: 5 }}>
              <defs>
                <linearGradient id="demandGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#0284c7" stopOpacity={0.45} />
                  <stop offset="95%" stopColor="#0284c7" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f293d" vertical={false} />
              <XAxis
                dataKey="index"
                tickLine={false}
                stroke="#64748b"
                tick={{ fontSize: 11, fill: '#94a3b8' }}
                interval={35} // ~8 ticks across 288 points to avoid overcrowding
                tickFormatter={(idx) => chartData[idx]?.tickLabel || ''}
              />
              <YAxis
                stroke="#64748b"
                tickLine={false}
                tick={{ fontSize: 11, fill: '#94a3b8' }}
                domain={[
                  (dataMin) => Math.floor(Math.max(0, dataMin - 15)),
                  (dataMax) => Math.ceil(dataMax + 15),
                ]}
                unit=" MW"
              />
              <Tooltip content={<ForecastTooltip />} />
              <Area
                type="monotone"
                dataKey="predicted_demand_mw"
                stroke="#38bdf8"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#demandGradient)"
                name="Projected Demand"
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="chart-footer-meta">
        <span className="chart-legend-item">
          <span className="legend-color-box"></span>
          <span>Projected Demand (MW)</span>
        </span>
        <span className="chart-endpoint-tag">Source: GET /api/forecast?horizon_hours=72</span>
      </div>
    </SectionCard>
  );
}
