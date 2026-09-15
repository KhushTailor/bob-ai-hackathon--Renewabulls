import React, { useState } from 'react';
import SectionCard from './SectionCard';
import { simulateAction, compareScenarios } from '../services/api';

/**
 * Standard strategy presets for one-click hackathon demonstration.
 */
const PRESETS = [
  {
    label: 'Relieve Import (Battery 20 MW / 1h)',
    action: 'BATTERY_DISPATCH',
    amount_mw: 20.0,
    duration_hours: 1.0,
  },
  {
    label: 'Peak Load Shift (25 MW / 2h)',
    action: 'LOAD_SHIFT',
    amount_mw: 25.0,
    duration_hours: 2.0,
  },
  {
    label: 'Conservative Battery (10 MW / 1h)',
    action: 'BATTERY_DISPATCH',
    amount_mw: 10.0,
    duration_hours: 1.0,
  },
  {
    label: 'Excess Import Test (300 MW / 2h - Infeasible)',
    action: 'GRID_IMPORT',
    amount_mw: 300.0,
    duration_hours: 2.0,
  },
];

const MULTI_COMPARE_DEFAULT = [
  { action: 'BATTERY_DISPATCH', amount_mw: 20.0, duration_hours: 1.0 },
  { action: 'LOAD_SHIFT', amount_mw: 25.0, duration_hours: 2.0 },
  { action: 'BATTERY_DISPATCH', amount_mw: 10.0, duration_hours: 1.0 },
  { action: 'GRID_IMPORT', amount_mw: 300.0, duration_hours: 2.0 },
];

/**
 * 72-Hour What-If & Action Generator (Interactive Simulator Panel — Stage S12).
 *
 * Evaluates proposed dispatch and load intervention scenarios across a 288-step
 * forecast horizon. Renders single scenario evaluations or multi-strategy comparisons.
 */
export default function SimulatorShell({ statusData }) {
  // Mode: 'single' | 'compare'
  const [mode, setMode] = useState('single');

  // Single Simulation Form State
  const [action, setAction] = useState('BATTERY_DISPATCH');
  const [amountMw, setAmountMw] = useState(20.0);
  const [durationHours, setDurationHours] = useState(1.0);

  // Results & UI State
  const [simResult, setSimResult] = useState(null);
  const [compareResults, setCompareResults] = useState(null);
  const [simulating, setSimulating] = useState(false);
  const [error, setError] = useState(null);

  // Interconnection & Battery headroom from current state
  const currentImport = statusData?.grid_import_mw ?? 176.1;
  const currentSoc = statusData?.battery_soc_pct ?? 50.2;
  const currentDemand = statusData?.demand_mw ?? 204.5;
  const currentRenewable = statusData?.total_renewable_mw ?? 47.2;
  const importHeadroom = Math.max(0, 180.0 - currentImport).toFixed(1);
  const usableBatteryMwh = Math.max(0, ((currentSoc - 5.0) / 100.0) * 80.0).toFixed(1);

  // Run Single Scenario Simulation
  const handleRunSimulation = async (scenarioOverride = null) => {
    const payload = scenarioOverride || {
      action,
      amount_mw: parseFloat(amountMw),
      duration_hours: parseFloat(durationHours),
    };

    // Client-side validation
    if (isNaN(payload.amount_mw) || payload.amount_mw <= 0) {
      setError(new Error('Power magnitude must be a positive number.'));
      return;
    }
    if (isNaN(payload.duration_hours) || payload.duration_hours <= 0) {
      setError(new Error('Duration must be greater than zero.'));
      return;
    }

    setSimulating(true);
    setError(null);

    try {
      const res = await simulateAction(payload);
      setSimResult(res);
    } catch (err) {
      console.error('Simulation request failed:', err);
      setError(err);
    } finally {
      setSimulating(false);
    }
  };

  // Run Multi-Strategy Comparison
  const handleRunCompare = async () => {
    setSimulating(true);
    setError(null);

    try {
      const res = await compareScenarios(MULTI_COMPARE_DEFAULT);
      setCompareResults(res?.results || []);
    } catch (err) {
      console.error('Compare request failed:', err);
      setError(err);
    } finally {
      setSimulating(false);
    }
  };

  // Apply a preset directly
  const handleApplyPreset = (preset) => {
    setAction(preset.action);
    setAmountMw(preset.amount_mw);
    setDurationHours(preset.duration_hours);
    handleRunSimulation(preset);
  };

  // Format Action Display Names
  const getActionLabel = (act) => {
    switch (act) {
      case 'BATTERY_DISPATCH': return 'Battery Dispatch';
      case 'LOAD_SHIFT': return 'Demand Load Shift';
      case 'GRID_IMPORT': return 'Scheduled Import';
      case 'RENEWABLE_CURTAILMENT': return 'Renewable Curtailment';
      default: return act;
    }
  };

  return (
    <SectionCard
      title="72-Hour What-If & Action Generator"
      subtitle="Deterministic decision-support simulation across 288 forecast steps"
      badge="Decision Support"
      badgeVariant="accent"
      className="simulator-section-card"
    >
      {/* 72-Hour Operating Context Ribbon */}
      <div className="shell-summary-row sim-context-ribbon">
        <div className="shell-stat">
          <span className="shell-stat-label">Evaluation Horizon</span>
          <span className="shell-stat-value">72 Hours</span>
          <span className="shell-stat-meta">288 Steps (15-min intervals)</span>
        </div>

        <div className="shell-stat">
          <span className="shell-stat-label">Intertie Headroom</span>
          <span className="shell-stat-value text-accent">{importHeadroom} MW</span>
          <span className="shell-stat-meta">Current: {currentImport.toFixed(1)} / 180 MW</span>
        </div>

        <div className="shell-stat">
          <span className="shell-stat-label">Usable Battery Buffer</span>
          <span className="shell-stat-value">{usableBatteryMwh} MWh</span>
          <span className="shell-stat-meta">Current SOC: {currentSoc.toFixed(1)}% (5% Min)</span>
        </div>

        <div className="shell-stat">
          <span className="shell-stat-label">System Demand</span>
          <span className="shell-stat-value">{currentDemand.toFixed(1)} MW</span>
          <span className="shell-stat-meta">Renewable: {currentRenewable.toFixed(1)} MW</span>
        </div>
      </div>

      {/* Mode Switcher & Quick Presets */}
      <div className="sim-toolbar">
        <div className="mode-toggle-group">
          <button
            className={`btn-mode ${mode === 'single' ? 'active' : ''}`}
            onClick={() => setMode('single')}
          >
            Single Scenario
          </button>
          <button
            className={`btn-mode ${mode === 'compare' ? 'active' : ''}`}
            onClick={() => {
              setMode('compare');
              if (!compareResults) handleRunCompare();
            }}
          >
            Multi-Strategy Compare
          </button>
        </div>

        {mode === 'single' && (
          <div className="presets-row">
            <span className="presets-label">Presets:</span>
            {PRESETS.map((p, idx) => (
              <button
                key={idx}
                className="btn-preset"
                onClick={() => handleApplyPreset(p)}
                disabled={simulating}
              >
                {p.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Error Message if API fails */}
      {error && (
        <div className="sim-error-alert">
          <strong>Simulation Error:</strong> {error.message || 'Failed to evaluate scenario.'}
        </div>
      )}

      {/* SINGLE SCENARIO MODE */}
      {mode === 'single' && (
        <div className="single-sim-layout">
          {/* Controls Form */}
          <div className="sim-form-card">
            <div className="form-group">
              <label className="form-label">Intervention Action</label>
              <select
                className="form-control"
                value={action}
                onChange={(e) => setAction(e.target.value)}
                disabled={simulating}
              >
                <option value="BATTERY_DISPATCH">Battery Dispatch (Floor 5% SOC)</option>
                <option value="LOAD_SHIFT">Demand Load Shift (Flexible Load)</option>
                <option value="GRID_IMPORT">Scheduled Grid Import (Cap 180 MW)</option>
                <option value="RENEWABLE_CURTAILMENT">Renewable Curtailment (Surplus Relief)</option>
              </select>
            </div>

            <div className="form-row">
              <div className="form-group flex-1">
                <label className="form-label">
                  Power Magnitude {action === 'BATTERY_DISPATCH' ? '(Max 40 MW)' : '(MW)'}
                </label>
                <input
                  type="number"
                  className="form-control font-mono"
                  value={amountMw}
                  min="1"
                  max={action === 'BATTERY_DISPATCH' ? '40' : '400'}
                  step="5"
                  onChange={(e) => setAmountMw(e.target.value)}
                  disabled={simulating}
                />
              </div>

              <div className="form-group flex-1">
                <label className="form-label">Duration</label>
                <select
                  className="form-control font-mono"
                  value={durationHours}
                  onChange={(e) => setDurationHours(e.target.value)}
                  disabled={simulating}
                >
                  <option value="0.25">15 Minutes (0.25h)</option>
                  <option value="0.5">30 Minutes (0.50h)</option>
                  <option value="1.0">1.0 Hour (4 Steps)</option>
                  <option value="2.0">2.0 Hours (8 Steps)</option>
                  <option value="4.0">4.0 Hours (16 Steps)</option>
                </select>
              </div>
            </div>

            <button
              className="btn-run-sim"
              onClick={() => handleRunSimulation()}
              disabled={simulating}
            >
              {simulating ? 'Simulating 288 Steps...' : '⚡ Run 72h Simulation'}
            </button>
          </div>

          {/* Results Display */}
          <div className="sim-result-card">
            {!simResult ? (
              <div className="sim-empty-state">
                <span className="empty-icon">📊</span>
                <h4>Ready for What-If Simulation</h4>
                <p>Select an action above and click "Run 72h Simulation" or pick a quick preset to evaluate operational impact.</p>
              </div>
            ) : (
              <div className="sim-result-content">
                {/* Result Header & Feasibility */}
                <div className="result-header">
                  <div>
                    <span className="result-action-title">
                      {getActionLabel(simResult.action)}: {simResult.amount_mw} MW × {simResult.duration_hours}h
                    </span>
                    <p className="result-explanation">{simResult.explanation}</p>
                  </div>

                  <div className={`feasibility-badge ${simResult.is_feasible ? 'feasible' : 'infeasible'}`}>
                    <span className="status-dot"></span>
                    <span>{simResult.is_feasible ? 'FEASIBLE' : 'INFEASIBLE'}</span>
                  </div>
                </div>

                {/* Core Impact Grid */}
                <div className="result-metrics-grid">
                  {/* Action Execution */}
                  <div className="result-metric-box">
                    <span className="res-label">Action Execution</span>
                    <span className="res-value">{simResult.applied_action_mw} MW</span>
                    <span className={`res-meta ${simResult.unmet_action_mw > 0 ? 'text-critical' : 'text-nominal'}`}>
                      {simResult.unmet_action_mw > 0 
                        ? `Unmet: ${simResult.unmet_action_mw} MW` 
                        : '100% Satisfied'}
                    </span>
                  </div>

                  {/* Grid Import Relief */}
                  <div className="result-metric-box">
                    <span className="res-label">Grid Import Relief</span>
                    <div className="res-flow">
                      <span>{simResult.original_grid_import_mw}</span>
                      <span className="flow-arrow">→</span>
                      <span className="text-accent">{simResult.adjusted_grid_import_mw} MW</span>
                    </div>
                    <span className="res-meta text-nominal">
                      {(simResult.original_grid_import_mw - simResult.adjusted_grid_import_mw) > 0 
                        ? `-${(simResult.original_grid_import_mw - simResult.adjusted_grid_import_mw).toFixed(1)} MW Net Relief` 
                        : 'No Import Reduction'}
                    </span>
                  </div>

                  {/* Battery SOC Trajectory */}
                  <div className="result-metric-box">
                    <span className="res-label">Battery SOC Trajectory</span>
                    <div className="res-flow">
                      <span>{simResult.battery_soc_before_pct}%</span>
                      <span className="flow-arrow">→</span>
                      <span className={`res-val-focus ${simResult.battery_soc_after_pct < 5 ? 'text-critical' : 'text-nominal'}`}>
                        {simResult.battery_soc_after_pct}%
                      </span>
                    </div>
                    <span className="res-meta">
                      {(simResult.battery_soc_before_pct - simResult.battery_soc_after_pct).toFixed(1)}% Reserve Discharged
                    </span>
                  </div>

                  {/* Operational Score */}
                  <div className="result-metric-box">
                    <span className="res-label">Strategy Score</span>
                    <span className="res-value font-mono">{simResult.score} / 100</span>
                    <span className={`res-meta risk-${simResult.risk_severity.toLowerCase()}`}>
                      Risk Level: {simResult.risk_severity}
                    </span>
                  </div>
                </div>

                {/* Constraint Violations Bar */}
                <div className="violations-container">
                  <span className="violations-title">Constraint Violations:</span>
                  {simResult.constraint_violations && simResult.constraint_violations.length > 0 ? (
                    <div className="violations-list">
                      {simResult.constraint_violations.map((v, idx) => (
                        <span key={idx} className="violation-tag">{v}</span>
                      ))}
                    </div>
                  ) : (
                    <span className="text-nominal font-medium text-xs">✓ None. Zero physical or operational limits breached.</span>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* MULTI-STRATEGY COMPARE MODE */}
      {mode === 'compare' && (
        <div className="compare-mode-container">
          <div className="compare-header-row">
            <div>
              <h4 className="compare-title">Multi-Strategy Comparison Matrix</h4>
              <p className="compare-subtitle">Ranked deterministically by backend score (Feasible strategies strictly prioritized)</p>
            </div>
            <button
              className="btn-refresh-compare"
              onClick={handleRunCompare}
              disabled={simulating}
            >
              {simulating ? 'Evaluating...' : '↻ Re-evaluate Comparison'}
            </button>
          </div>

          <div className="compare-cards-list">
            {compareResults && compareResults.length > 0 ? (
              compareResults.map((item, idx) => {
                const isBest = idx === 0 && item.is_feasible;
                const relief = (item.original_grid_import_mw - item.adjusted_grid_import_mw).toFixed(1);

                return (
                  <div
                    key={item.scenario_id || idx}
                    className={`compare-strategy-card ${isBest ? 'best-strategy' : ''} ${!item.is_feasible ? 'card-infeasible' : ''}`}
                  >
                    <div className="strat-top-row">
                      <div className="strat-title-group">
                        {isBest && <span className="best-badge">★ RECOMMENDED STRATEGY</span>}
                        <span className="strat-name">
                          {getActionLabel(item.action)} ({item.amount_mw} MW × {item.duration_hours}h)
                        </span>
                      </div>

                      <div className={`feasibility-badge ${item.is_feasible ? 'feasible' : 'infeasible'}`}>
                        <span>{item.is_feasible ? 'FEASIBLE' : 'INFEASIBLE'}</span>
                      </div>
                    </div>

                    <div className="strat-metrics-row">
                      <div className="strat-col">
                        <span className="strat-label">Applied Action</span>
                        <span className="strat-val">{item.applied_action_mw} MW</span>
                        {item.unmet_action_mw > 0 && (
                          <span className="strat-sub text-critical">{item.unmet_action_mw} MW unmet</span>
                        )}
                      </div>

                      <div className="strat-col">
                        <span className="strat-label">Grid Import Relief</span>
                        <span className="strat-val text-accent">
                          {Number(relief) > 0 ? `-${relief} MW` : '0.0 MW'}
                        </span>
                        <span className="strat-sub">{item.original_grid_import_mw} → {item.adjusted_grid_import_mw} MW</span>
                      </div>

                      <div className="strat-col">
                        <span className="strat-label">Battery SOC</span>
                        <span className="strat-val">
                          {item.battery_soc_before_pct}% → {item.battery_soc_after_pct}%
                        </span>
                        <span className="strat-sub">Remaining buffer</span>
                      </div>

                      <div className="strat-col">
                        <span className="strat-label">Risk Severity</span>
                        <span className={`strat-val risk-${item.risk_severity.toLowerCase()}`}>
                          {item.risk_severity}
                        </span>
                      </div>

                      <div className="strat-col score-col">
                        <span className="strat-label">Score</span>
                        <span className="strat-score font-mono">{item.score}</span>
                      </div>
                    </div>

                    {item.constraint_violations && item.constraint_violations.length > 0 && (
                      <div className="strat-violations">
                        <span className="strat-v-label">Violations:</span>
                        {item.constraint_violations.map((v, vIdx) => (
                          <span key={vIdx} className="violation-tag small">{v}</span>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })
            ) : (
              <div className="empty-chart-box" style={{ height: 160 }}>
                {simulating ? 'Evaluating strategies across 288 timesteps...' : 'Awaiting comparison execution...'}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Decision-Support Prototype Disclaimer */}
      <div className="sim-disclaimer-box">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="disclaimer-icon">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="16" x2="12" y2="12" />
          <line x1="12" y1="8" x2="12.01" y2="8" />
        </svg>
        <span>
          <strong>DECISION-SUPPORT PROTOTYPE:</strong> This is a simulation and decision-support prototype. It does not control physical grid equipment.
        </span>
      </div>
    </SectionCard>
  );
}
