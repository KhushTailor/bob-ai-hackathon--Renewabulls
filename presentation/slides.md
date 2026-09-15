# GridPulse — AI-Assisted Grid Optimisation
## IBM BOB AI Innovation Hackathon 2026 | Sustainability Track
**Team:** Renewabulls | **Author:** Khush Tailor

---

## Slide 1: Executive Summary & Problem

### The Problem
- **Renewable Volatility:** Solar and wind generation fluctuate wildly based on rapid weather shifts.
- **Interconnection Bottlenecks:** Microgrids face hard import limits (180 MW), risking cascade trips if demand outstrips supply.
- **Battery Reserve Degradation:** Over-discharging utility storage below physical minimum reserves (5% SOC / 4 MWh) causes permanent damage.
- **Operator Cognitive Overload:** Raw telemetry across disjoint EMS/SCADA screens forces manual correlation under high-stress emergencies.

---

## Slide 2: Solution — GridPulse

### Single Decision-Ready View
GridPulse consolidates 15-minute telemetry into five real-time decision-support capabilities:
1. **72-Hour Demand Forecast:** 288-point lookahead projecting cyclic peaks and troughs.
2. **Renewable Performance Monitoring:** Solar and wind Performance Ratios (PR%) and curtailment tracking.
3. **12-Rule Anomaly Engine:** Deterministic classification of frequency, voltage, and battery hazards.
4. **72-Hour What-If & Action Generator:** True energy-bounded simulation testing battery, load shift, and import interventions.
5. **AI Operator Brief:** Plain-English synthesis answering the 6 critical operational incident questions.

---

## Slide 3: System Architecture & Data Flow

### Three-Tier Decoupled Design
- **Data & Physics Layer:** Continuous 6-month microgrid dataset (17,520 intervals), physics-based solar irradiance and wind power curve estimation.
- **FastAPI Application Runtime:** Python 3.11 backend hosting endpoints (`/api/status`, `/api/forecast`, `/api/renewables`, `/api/alerts`, `/api/simulate`, `/api/operator-brief`).
- **Interactive Operations Frontend:** React 18 single-page dashboard built with Vite and Recharts, featuring live simulation controls and comparison matrices.

---

## Slide 4: IBM Technology & Tool Integration

### 1. IBM Bob (Development & Agent Interaction)
- Scaffolded, authored, tested, and audited all six service layers and React dashboard components.
- Domain skill encoded in `.bob/skills/gridpulse/SKILL.md` enforcing physics rules across development sessions.

### 2. Model Context Protocol (MCP) Server
- Implemented with `@modelcontextprotocol/sdk` (Node.js).
- Exposes 6 real-time tools (`get_grid_status`, `get_active_alerts`, `get_renewable_performance`, `get_demand_forecast`, `simulate_grid_action`, `generate_operator_brief`) to AI assistants.

### 3. IBM Granite Foundation Models (Optional Cloud AI)
- `granite-ttm-512-96-r2`: Zero-shot time-series forecasting.
- `granite-3-3-8b-instruct`: Operator brief natural language generation.
- Robust deterministic fallbacks operate 100% offline without credentials.

---

## Slide 5: Validated Demonstration Highlights

- **Battery Simulation Physics:** Discharging 20 MW for 1 hour from 50.2% SOC ($40.16\text{ MWh}$) safely reaches 25.2% ($20.16\text{ MWh}$), preserving a 20.2% reserve above the 5% minimum floor.
- **Feasibility Verification:** Infeasible actions exceeding the 180 MW intertie or draining storage are deterministically rejected with unmet power accounting.
- **Automated Verification:** 165 backend unit/API tests passing, 32 MCP client integration tests passing, zero production build errors.

---

## Slide 6: Sustainability Impact & Future Roadmap

### Immediate Benefits
- **Maximised Renewable Utilisation:** Early curtailment detection allows excess solar/wind to charge batteries rather than being wasted.
- **Prevented Outages:** Feasible what-if dispatch schedules intertie relief before transmission lines overload.

### Production Horizons
- Multi-bus AC power flow integration (incorporating line impedance and reactive power).
- Fleet-scale microgrid coordination via distributed MCP tool endpoints.
