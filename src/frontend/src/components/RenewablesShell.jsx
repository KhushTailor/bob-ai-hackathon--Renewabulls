import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import SectionCard from './SectionCard';

/**
 * Custom Tooltip for Actual vs Expected Generation Comparison.
 */
function GenerationTooltip({ active, payload, label }) {
  if (active && payload && payload.length) {
    const actual = payload.find(p => p.dataKey === 'actual')?.value || 0;
    const expected = payload.find(p => p.dataKey === 'expected')?.value || 0;
    const diff = actual - expected;
    const pr = expected > 0 ? ((actual / expected) * 100).toFixed(1) : '—';

    return (
      <div className="chart-tooltip">
        <div className="tooltip-time">{label}</div>
        <div className="tooltip-metric">
          <span className="tooltip-label">Actual Output:</span>
          <span className="tooltip-val text-nominal">{actual.toFixed(2)} MW</span>
        </div>
        <div className="tooltip-metric">
          <span className="tooltip-label">Expected Output:</span>
          <span className="tooltip-val text-accent">{expected.toFixed(2)} MW</span>
        </div>
        <div className="tooltip-metric">
          <span className="tooltip-label">Variance:</span>
          <span className={`tooltip-val ${diff >= 0 ? 'text-nominal' : 'text-warning'}`}>
            {diff >= 0 ? `+${diff.toFixed(2)}` : diff.toFixed(2)} MW ({pr}%)
          </span>
        </div>
      </div>
    );
  }
  return null;
}

/**
 * Renewable Performance Monitoring Dashboard Panel (Stage S11).
 *
 * Visualizes Solar, Wind, and Combined fleet performance metrics and
 * presents an Actual vs Expected generation comparison using Recharts.
 */
export default function RenewablesShell({ renewables, error }) {
  if (error) {
    return (
      <SectionCard
        title="Renewable Performance Monitoring"
        subtitle="Fleet generation and performance ratios"
        badge="Error"
        badgeVariant="critical"
      >
        <div className="shell-error-box">
          <p className="error-text">Failed to load renewable metrics: {error.message || 'API error'}</p>
        </div>
      </SectionCard>
    );
  }

  const solar = renewables?.solar || {};
  const wind = renewables?.wind || {};
  const combined = renewables?.combined || {};

  // Formatted KPI values
  const solarActual = solar.actual_generation_mw ?? 0;
  const solarExpected = solar.expected_generation_mw ?? 0;
  const solarPR = solar.performance_ratio ? (solar.performance_ratio * 100).toFixed(1) : '—';
  const solarCF = solar.capacity_factor ? (solar.capacity_factor * 100).toFixed(1) : '—';
  const solarStatus = solar.underperforming ? 'UNDERPERFORMING' : 'HEALTHY';

  const windActual = wind.actual_generation_mw ?? 0;
  const windExpected = wind.expected_generation_mw ?? 0;
  const windPR = wind.performance_ratio ? (wind.performance_ratio * 100).toFixed(1) : '—';
  const windCF = wind.capacity_factor ? (wind.capacity_factor * 100).toFixed(1) : '—';
  const windStatus = wind.underperforming ? 'UNDERPERFORMING' : 'HEALTHY';

  const totalActual = combined.total_renewable_mw ?? (solarActual + windActual);
  const totalExpected = solarExpected + windExpected;
  const combinedPct = combined.renewable_pct_of_demand ? combined.renewable_pct_of_demand.toFixed(1) : '—';
  const combinedUtil = combined.renewable_utilisation ? combined.renewable_utilisation.toFixed(1) : '—';
  const curtailmentStatus = combined.curtailment_active ? 'Active (Export Saturated)' : 'None (0 MW)';
  const overallStatus = combined.status || 'HEALTHY';

  // Recharts Bar Data: Real backend comparison only (zero fabrication)
  const comparisonData = [
    {
      asset: 'Solar Fleet (150 MW)',
      actual: solarActual,
      expected: solarExpected,
    },
    {
      asset: 'Wind Fleet (80 MW)',
      actual: windActual,
      expected: windExpected,
    },
    {
      asset: 'Combined Total',
      actual: totalActual,
      expected: totalExpected,
    },
  ];

  return (
    <SectionCard
      title="Renewable Performance Monitoring"
      subtitle="Generation KPIs, performance ratios, and actual vs expected output"
      badge={`Status: ${overallStatus}`}
      badgeVariant={overallStatus === 'UNDERPERFORMING' ? 'warning' : 'nominal'}
    >
      {/* Fleet Cards Grid */}
      <div className="renewables-fleet-grid">
        {/* Solar Card */}
        <div className="fleet-card">
          <div className="fleet-card-header">
            <span className="fleet-card-title">☀️ Solar Generation</span>
            <span className={`fleet-pill ${solarStatus === 'HEALTHY' ? 'pill-nominal' : 'pill-warning'}`}>
              {solarStatus}
            </span>
          </div>
          <div className="fleet-card-metrics">
            <div className="fleet-metric-col">
              <span className="fleet-label">Actual</span>
              <span className="fleet-val">{solarActual.toFixed(2)} MW</span>
            </div>
            <div className="fleet-metric-col">
              <span className="fleet-label">Expected</span>
              <span className="fleet-val text-muted">{solarExpected.toFixed(2)} MW</span>
            </div>
            <div className="fleet-metric-col">
              <span className="fleet-label">Perf. Ratio</span>
              <span className={`fleet-val ${Number(solarPR) >= 80 ? 'text-nominal' : 'text-warning'}`}>
                {solarPR}%
              </span>
            </div>
            <div className="fleet-metric-col">
              <span className="fleet-label">Capacity Factor</span>
              <span className="fleet-val">{solarCF}%</span>
            </div>
          </div>
        </div>

        {/* Wind Card */}
        <div className="fleet-card">
          <div className="fleet-card-header">
            <span className="fleet-card-title">💨 Wind Generation</span>
            <span className={`fleet-pill ${windStatus === 'HEALTHY' ? 'pill-nominal' : 'pill-warning'}`}>
              {windStatus}
            </span>
          </div>
          <div className="fleet-card-metrics">
            <div className="fleet-metric-col">
              <span className="fleet-label">Actual</span>
              <span className="fleet-val">{windActual.toFixed(2)} MW</span>
            </div>
            <div className="fleet-metric-col">
              <span className="fleet-label">Expected</span>
              <span className="fleet-val text-muted">{windExpected.toFixed(2)} MW</span>
            </div>
            <div className="fleet-metric-col">
              <span className="fleet-label">Perf. Ratio</span>
              <span className={`fleet-val ${Number(windPR) >= 75 ? 'text-nominal' : 'text-warning'}`}>
                {windPR}%
              </span>
            </div>
            <div className="fleet-metric-col">
              <span className="fleet-label">Capacity Factor</span>
              <span className="fleet-val">{windCF}%</span>
            </div>
          </div>
        </div>

        {/* Combined Fleet Summary Card */}
        <div className="fleet-card combined-card">
          <div className="fleet-card-header">
            <span className="fleet-card-title">⚡ Combined Renewable Fleet</span>
            <span className={`fleet-pill ${overallStatus === 'HEALTHY' ? 'pill-nominal' : 'pill-warning'}`}>
              {overallStatus}
            </span>
          </div>
          <div className="fleet-card-metrics">
            <div className="fleet-metric-col">
              <span className="fleet-label">Total Output</span>
              <span className="fleet-val text-nominal">{totalActual.toFixed(2)} MW</span>
            </div>
            <div className="fleet-metric-col">
              <span className="fleet-label">Demand Share</span>
              <span className="fleet-val">{combinedPct}%</span>
            </div>
            <div className="fleet-metric-col">
              <span className="fleet-label">Utilisation</span>
              <span className="fleet-val">{combinedUtil}%</span>
            </div>
            <div className="fleet-metric-col">
              <span className="fleet-label">Curtailment</span>
              <span className="fleet-val text-muted">{curtailmentStatus}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Actual vs Expected Comparison Chart */}
      <div className="chart-header-row">
        <span className="chart-subhead">Actual vs Expected Generation Comparison</span>
        <span className="chart-meta-note">Derived from physical solar irradiance & wind speed models</span>
      </div>

      <div className="chart-container" style={{ width: '100%', height: 210 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={comparisonData} margin={{ top: 10, right: 15, left: -10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f293d" vertical={false} />
            <XAxis
              dataKey="asset"
              tickLine={false}
              stroke="#64748b"
              tick={{ fontSize: 11, fill: '#94a3b8' }}
            />
            <YAxis
              stroke="#64748b"
              tickLine={false}
              tick={{ fontSize: 11, fill: '#94a3b8' }}
              unit=" MW"
            />
            <Tooltip content={<GenerationTooltip />} />
            <Legend
              wrapperStyle={{ fontSize: '11px', paddingTop: '6px' }}
              iconType="circle"
              iconSize={8}
            />
            <Bar
              dataKey="actual"
              fill="#10b981"
              name="Actual Generation (MW)"
              radius={[4, 4, 0, 0]}
              maxBarSize={45}
              isAnimationActive={false}
            />
            <Bar
              dataKey="expected"
              fill="#0284c7"
              name="Expected Generation (MW)"
              radius={[4, 4, 0, 0]}
              maxBarSize={45}
              isAnimationActive={false}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="chart-footer-meta">
        <span className="chart-endpoint-tag">Source: GET /api/renewables • IEC Class II & Irradiance Baseline</span>
      </div>
    </SectionCard>
  );
}
