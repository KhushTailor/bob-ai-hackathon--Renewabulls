import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import StatusCard from './components/StatusCard';
import LoadingState from './components/LoadingState';
import ErrorState from './components/ErrorState';

import DemandForecastShell from './components/DemandForecastShell';
import RenewablesShell from './components/RenewablesShell';
import AnomalyEngineShell from './components/AnomalyEngineShell';
import SimulatorShell from './components/SimulatorShell';
import OperatorBriefShell from './components/OperatorBriefShell';

import {
  fetchStatus,
  fetchAlerts,
  fetchForecast,
  fetchRenewables,
  fetchOperatorBrief,
} from './services/api';

export default function App() {
  const [statusData, setStatusData] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [forecast, setForecast] = useState(null);
  const [renewables, setRenewables] = useState(null);
  const [brief, setBrief] = useState(null);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

  const loadDashboardData = useCallback(async (isSilent = false) => {
    if (!isSilent) setLoading(true);
    else setRefreshing(true);
    setError(null);

    try {
      const [statusRes, alertsRes, forecastRes, renewablesRes, briefRes] = await Promise.all([
        fetchStatus(),
        fetchAlerts(),
        fetchForecast(72),
        fetchRenewables(),
        fetchOperatorBrief(),
      ]);

      setStatusData(statusRes);
      setAlerts(Array.isArray(alertsRes) ? alertsRes : (alertsRes?.alerts || []));
      setForecast(forecastRes);
      setRenewables(renewablesRes);
      setBrief(briefRes);
    } catch (err) {
      console.error('Failed to load GridPulse telemetry:', err);
      setError(err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadDashboardData(false);
  }, [loadDashboardData]);

  // Compute Overall System State
  const computeSystemStatus = () => {
    if (!alerts || alerts.length === 0) return 'NOMINAL';
    if (alerts.some(a => a.severity === 'CRITICAL')) return 'CRITICAL';
    if (alerts.some(a => a.severity === 'WARNING')) return 'WARNING';
    return 'NOMINAL';
  };

  const systemStatus = computeSystemStatus();

  // Status card variants based on telemetry values
  const getImportVariant = (imp) => {
    if (imp >= 176.4) return 'critical';
    if (imp >= 162.0) return 'warning';
    return 'nominal';
  };

  const getBatteryVariant = (soc) => {
    if (soc < 5.0) return 'critical';
    if (soc < 15.0) return 'warning';
    return 'nominal';
  };

  const getFrequencyVariant = (freq) => {
    const dev = Math.abs(freq - 50.0);
    if (dev > 0.5) return 'critical';
    if (dev > 0.2) return 'warning';
    return 'nominal';
  };

  const getVoltageVariant = (volt) => {
    if (volt < 0.90 || volt > 1.10) return 'critical';
    if (volt < 0.95 || volt > 1.05) return 'warning';
    return 'nominal';
  };

  return (
    <div className="app-container">
      <Header
        systemStatus={systemStatus}
        timestamp={statusData?.timestamp}
        onRefresh={() => loadDashboardData(true)}
        isRefreshing={refreshing}
      />

      <main className="dashboard-content">
        {loading ? (
          <LoadingState message="Connecting to GridPulse operational telemetry..." />
        ) : error ? (
          <ErrorState
            error={error}
            onRetry={() => loadDashboardData(false)}
            title="GridPulse Telemetry Offline"
          />
        ) : (
          <>
            {/* Top Primary KPI Telemetry Ribbon */}
            <section className="status-ribbon">
              <StatusCard
                label="System Demand"
                value={statusData?.demand_mw?.toFixed(1) ?? '—'}
                unit="MW"
                subtext={`Renewables cover ${statusData?.renewable_pct?.toFixed(1) ?? '—'}%`}
                status="accent"
              />

              <StatusCard
                label="Renewable Generation"
                value={statusData?.total_renewable_mw?.toFixed(1) ?? '—'}
                unit="MW"
                subtext={`Solar: ${statusData?.solar_actual_mw?.toFixed(1) ?? '—'} • Wind: ${statusData?.wind_actual_mw?.toFixed(1) ?? '—'}`}
                status="nominal"
              />

              <StatusCard
                label="Battery Storage"
                value={statusData?.battery_soc_pct?.toFixed(1) ?? '—'}
                unit="%"
                subtext="80 MWh Capacity • 40 MW Max"
                status={getBatteryVariant(statusData?.battery_soc_pct ?? 50)}
              />

              <StatusCard
                label="Grid Import"
                value={statusData?.grid_import_mw?.toFixed(1) ?? '—'}
                unit="MW"
                subtext={`${((statusData?.grid_import_mw || 0) / 180 * 100).toFixed(1)}% of 180 MW limit`}
                status={getImportVariant(statusData?.grid_import_mw ?? 0)}
              />

              <StatusCard
                label="Grid Frequency"
                value={statusData?.frequency_hz?.toFixed(3) ?? '—'}
                unit="Hz"
                subtext="Nominal: 50.000 Hz (±0.2 Hz)"
                status={getFrequencyVariant(statusData?.frequency_hz ?? 50)}
              />

              <StatusCard
                label="Bus Voltage"
                value={statusData?.voltage_pu?.toFixed(3) ?? '—'}
                unit="pu"
                subtext="Nominal: 1.000 pu (±0.05 pu)"
                status={getVoltageVariant(statusData?.voltage_pu ?? 1)}
              />
            </section>

            {/* AI Operator Brief Section (Top Priority Decision-Support) */}
            <section className="dashboard-row">
              <OperatorBriefShell brief={brief} />
            </section>

            {/* Five Capabilities Grid Layout */}
            <section className="dashboard-grid">
              <DemandForecastShell forecast={forecast} />
              <RenewablesShell renewables={renewables} />
              <AnomalyEngineShell alerts={alerts} />
              <SimulatorShell statusData={statusData} />
            </section>
          </>
        )}
      </main>

      <footer className="app-footer">
        <div className="footer-content">
          <span className="footer-title">GridPulse • Team Renewabulls • IBM Bob AI Innovation Hackathon (Sustainability Track)</span>
          <span className="footer-disclaimer">
            Decision-Support Prototype • Non-autonomous • Does not directly command physical grid assets
          </span>
        </div>
      </footer>
    </div>
  );
}
