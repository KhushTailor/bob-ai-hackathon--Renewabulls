---
name: gridpulse
description: >
  GridPulse domain knowledge for the Renewabulls IBM Bob AI Innovation Hackathon project.
  Activates when working on any GridPulse component: backend services, frontend, MCP server,
  data pipeline, documentation, or tests.
---

# GridPulse — IBM Bob Skill

You are assisting with GridPulse, an AI-assisted grid optimisation system built by team
Renewabulls for the IBM Bob AI Innovation Hackathon (Track: Sustainability).

## Project Overview

GridPulse is a single-page dashboard + FastAPI backend that provides five features:
1. Demand Forecasting (IBM Granite TTM via watsonx.ai, or STL fallback)
2. Renewable Performance Monitoring (rule-based, Pandas)
3. Anomaly & Red-Flag Engine (12 deterministic rules)
4. 72-Hour What-If & Action Generator (deterministic scoring, 4 actions)
5. AI Operator Brief (IBM Granite ibm/granite-3-3-8b-instruct, or Jinja2 fallback)

## Architecture

- Backend: FastAPI (Python 3.11), `src/backend/`
- Frontend: React 18 + Recharts + plain CSS, `src/frontend/`
- MCP Server: TypeScript (~80 lines), `src/mcp-server/`
- Data: CSV (6 months, 17,520 rows, 15-min intervals), `src/data/grid_data.csv`
- No database — all state is in the CSV and in-memory

## IBM Technology Integration

### IBM Bob (this tool)
- Development environment for all GridPulse code
- GridPulse skill (this file) — loaded during all development sessions
- MCP server (`src/mcp-server/`) exposes 3 tools: get_grid_status, get_active_alerts,
  get_operator_brief — allowing Bob to query live GridPulse data during demos

### watsonx.ai — Granite TTM (Feature 1: Demand Forecasting)
- Model: `ibm/granite-ttm-512-96-r2`
- SDK: `ibm-watsonx-ai` Python package
- Pattern: ModelInference with credentials dict {"apikey": ..., "url": ...}
- Toggled by: WATSONX_GRANITE_TTM_ENABLED=true in .env
- Fallback: statsmodels STL decomposition (always implemented, zero credentials needed)

### watsonx.ai — Granite Instruct (Feature 5: Operator Brief)
- Model: `ibm/granite-3-3-8b-instruct`
- SDK: `ibm-watsonx-ai` Python package, ModelInference.generate_text()
- Toggled by: WATSONX_BRIEF_ENABLED=true in .env
- Fallback: Jinja2 template covering all 6 required brief fields

## Data Schema (grid_data.csv)

Columns (all present, 15-min intervals, UTC):
  timestamp, demand_mw, solar_actual_mw, wind_actual_mw,
  solar_capacity_mw, wind_capacity_mw, solar_irradiance_wm2, wind_speed_ms,
  temperature_c, battery_soc_pct, grid_import_mw, grid_export_mw,
  frequency_hz, voltage_pu, hour_of_day, day_of_week, month, is_weekend

## Anomaly Rules (12 rules — src/backend/services/anomaly_engine.py)

  ANO-001: abs(frequency_hz - 50.0) > 0.5  → CRITICAL  Frequency deviation
  ANO-002: abs(frequency_hz - 50.0) > 0.2  → WARNING   Frequency drift
  ANO-003: voltage_pu < 0.95 or > 1.05     → WARNING   Voltage excursion
  ANO-004: voltage_pu < 0.90 or > 1.10     → CRITICAL  Severe voltage excursion
  ANO-005: demand > forecast × 1.15        → WARNING   Demand surge >15%
  ANO-006: demand > forecast × 1.25        → CRITICAL  Extreme demand surge
  ANO-007: battery_soc_pct < 15            → WARNING   Battery low
  ANO-008: battery_soc_pct < 5             → CRITICAL  Battery critical
  ANO-009: solar PR < 0.80 for ≥3 periods  → WARNING   Solar underperformance
  ANO-010: wind PR < 0.75 for ≥3 periods   → WARNING   Wind underperformance
  ANO-011: grid_import > 0.9 × capacity    → WARNING   Near import limit
  ANO-012: curtailment > 20 MWh in 2h      → INFO      High curtailment

## Simulation Actions (4 actions — src/backend/services/simulator.py)

  ACT-01: Battery Dispatch    — discharge battery; limited by SOC (floor 10%)
  ACT-02: Load Shift          — shift ≤15% of peak ±4 hours
  ACT-03: Grid Import         — import from external grid; capped at import_capacity_mw
  ACT-04: Renewable Curtailment — reduce RE output; only when surplus exists

  Scoring weights: Stability 35%, Renewable Utilisation 30%, Cost 20%, Risk 15%

## API Endpoints (src/backend/routers/)

  GET  /api/status        → KPIs: frequency, demand, SOC, renewable %
  GET  /api/forecast      → 288-row demand forecast (72h × 15min)
  GET  /api/renewable     → performance ratios, curtailment, utilisation
  GET  /api/alerts        → active anomaly alerts, sorted by severity
  GET  /api/simulate      → what-if simulation results (all 4 actions)
  POST /api/simulate      → simulation with custom query parameters
  GET  /api/brief         → current operator brief (watsonx.ai or Jinja2)
  POST /api/brief/refresh → force-regenerate the operator brief
  GET  /health            → health check

## Operator Brief (6 required fields)

The brief must answer:
  1. What is happening right now?
  2. Why is it happening?
  3. What is the risk if unaddressed?
  4. What action is recommended?
  5. Why is that action the best choice?
  6. What happens if no action is taken?

## Coding Conventions

- Python: PEP 8, type hints on all function signatures, docstrings on all public functions
- FastAPI: Pydantic v2 response models for every endpoint; no naked dicts
- React: functional components + hooks only; no class components; no Redux
- CSS: plain CSS in src/frontend/src/styles/main.css — no Tailwind, no CSS-in-JS
- Tests: pytest; every service module has a corresponding test file; no live credentials in tests
- Environment: all config from .env via config.py; no hardcoded values anywhere

## Important Constraints

- Do NOT modify .github/workflows/validate.yml
- Do NOT commit .env files (they are in .gitignore)
- Do NOT add a database — CSV + Pandas is the data layer
- Do NOT invent watsonx.ai endpoints or model IDs not listed above
- Do NOT claim IBM Bob is a runtime inference API
- All watsonx.ai calls must be wrapped in try/except with fallback to local implementation
- The demo must work with WATSONX_GRANITE_TTM_ENABLED=false and WATSONX_BRIEF_ENABLED=false
