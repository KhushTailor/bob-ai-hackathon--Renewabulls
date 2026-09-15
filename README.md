# GridPulse — AI-Assisted Grid Optimisation

> Intelligent decision support for renewable-heavy microgrids: 72-hour demand forecasting, renewable performance monitoring, anomaly detection, deterministic what-if simulation, and AI operator briefs.

---

## 👥 Team & Submission Information

| Field | Value |
| :--- | :--- |
| **Team Name** | Renewabulls |
| **Track** | Sustainability |
| **Team Lead** | Khush Tailor (`[PENDING_USER_EMAIL]`) |
| **Project** | GridPulse |
| **Hackathon** | IBM BOB AI Innovation Hackathon 2026 |

---

## 🎯 Problem Statement

Grid operators managing renewable-heavy microgrids (50–500 MW) face acute cognitive overload:
- **Generation Intermittency:** Sudden cloud cover or wind dropouts cause rapid generation deficits.
- **Interconnection Constraints:** Exceeding grid import intertie limits risks catastrophic blackouts and high penalty tariffs.
- **Battery Degradation & Reserve Violations:** Discharging utility batteries beyond safe physical operational reserves (5% minimum floor) causes permanent cell damage.
- **Information Fragmentation:** Existing SCADA and EMS systems display disaggregated metrics across disparate screens, forcing operators to mentally calculate energy balances under extreme time pressure.

---

## 💡 Solution

**GridPulse** delivers a consolidated, decision-ready operations dashboard designed to give grid controllers complete situational awareness within seconds of an incident:
- Combines continuous 15-minute telemetry analytics with a deterministic **Anomaly Engine**.
- Projects a **72-Hour Electricity Demand Forecast** (288 time steps).
- Audits solar and wind real-time performance against physics-based expected yields.
- Simulates candidate balancing interventions in a **72-Hour What-If Generator** that enforces physical battery storage constraints and intertie capacities.
- Delivers an **AI Operator Brief** answering the six core operational questions needed during emergencies.

---

## ✨ Five Core Implemented Features

### 1. 72-Hour Electricity Demand Forecasting
- Generates a 288-step demand curve across a 72-hour horizon at 15-minute intervals.
- Employs a deterministic Seasonal Naive lookback model capturing diurnal and weekly cyclic profiles.
- Supports optional IBM Granite Time-Series foundation models (`ibm/granite-ttm-512-96-r2`) via watsonx.ai.
- Interactive Recharts visualization with peak/trough indicators and time markers.

### 2. Renewable Performance Monitoring
- Continuous evaluation of Solar PV (60 MW nameplate) and Wind (50 MW nameplate) generation.
- Calculates Capacity Factor (CF%) and physics-based Performance Ratio (PR%) based on real-time solar irradiance and wind velocity.
- Automatically flags underperformance events and active curtailment.

### 3. 12-Rule Anomaly & Red-Flag Engine
- Deterministic threshold rule engine monitoring electrical and operational parameters.
- Evaluates frequency deviation (nominal 50.0 Hz), voltage excursions (nominal 33.0 kV), battery critical states, intertie overloads, and steep ramp rates.
- Classifies incidents into `CRITICAL`, `WARNING`, and `INFO` severities with clear remediation guidance.

### 4. 72-Hour What-If & Action Generator
- Interactive simulation control panel supporting single scenarios and multi-strategy comparisons.
- Evaluates interventions: Battery Dispatch, Load Shift, Grid Import, and Renewable Curtailment.
- **Strict Energy Physics**: True energy accounting ($E = P \times \Delta t$) preventing false feasibility and battery reserve violations below 5% SOC ($4.0\text{ MWh}$).
- Multi-dimensional scoring (0–100) prioritizing feasible actions and ranking strategies by grid stability, cost, and risk.

### 5. AI Operator Brief
- Synthesizes live status, active alerts, renewable yields, forecasts, and simulator outputs into a clear operational summary.
- Answers six core questions: *What is happening? Likely cause? Main risk? Recommended action? Rationale? Consequences of inaction?*
- Powered by structured deterministic synthesis with optional watsonx.ai Granite Instruct (`ibm/granite-3-3-8b-instruct`) enhancement.

---

## 🏗️ Architecture & Component Interaction

```
┌───────────────────────────────────────────────────────────┐
│                    AI Assistant Layer                     │
│  IBM Bob / Antigravity (AI Development & Operator Agent)   │
└─────────────────────────────┬─────────────────────────────┘
                              │ stdio / JSON-RPC
┌─────────────────────────────▼─────────────────────────────┐
│                 Tool Interface Layer (MCP)                │
│  src/mcp-server/ (6 registered tools via MCP SDK)         │
└─────────────────────────────┬─────────────────────────────┘
                              │ HTTP JSON fetch
┌─────────────────────────────▼─────────────────────────────┐
│             Application Runtime (FastAPI Backend)         │
│  src/backend/routers/ (status, alerts, forecast, etc.)    │
│  src/backend/services/ (forecaster, simulator, anomaly)   │
└──────────────────────┬──────────────────────┬─────────────┘
                       │                      │
┌──────────────────────▼───────┐  ┌───────────▼─────────────┐
│       Data / State Layer     │  │  Optional Cloud AI      │
│  src/data/grid_data.csv      │  │  watsonx.ai (Granite    │
│  (17,520 rows, 15-min res)   │  │   TTM & Instruct)       │
└──────────────────────────────┘  └─────────────────────────┘
```

### Architectural Distinctions & Boundaries
- **IBM Bob / Antigravity**: AI-assisted development environment used to scaffold, code, verify, and test the project, as well as interact with it via tool calls.
- **Model Context Protocol (MCP)**: Open standard tool interface layer (`@modelcontextprotocol/sdk`). MCP is **not** an IBM service, and its presence does **not** indicate that IBM Bob is hosting or executing the application runtime.
- **GridPulse Backend**: Python FastAPI application runtime hosting all physics calculations, data models, and REST endpoints.
- **watsonx.ai**: Optional cloud AI capability. All features include 100% operational offline fallbacks.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.11, FastAPI, Pydantic v2, Pandas, NumPy, Uvicorn, pytest
- **Frontend**: React 18, Vite, Recharts, Plain CSS
- **MCP Server**: Node.js v24+, `@modelcontextprotocol/sdk` (v1.30.0)
- **IBM Technologies**: IBM Bob (AI development environment & MCP assistant integration), optional watsonx.ai (IBM Granite TTM & Granite Instruct)

---

## ⚡ Quick Start & Setup

### Prerequisites
- Python 3.11+
- Node.js 18+ (Node v24 tested)
- Git

### 1. Clone Repository
```bash
git clone https://github.com/KhushTailor/bob-ai-hackathon--Renewabulls-.git
cd bob-ai-hackathon--Renewabulls-
```

### 2. Backend Setup
```bash
cd src
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Unix/macOS: source .venv/bin/activate

pip install -r requirements.txt
python -m uvicorn backend.main:app --reload --port 8000
```
Backend API docs will be live at `http://127.0.0.1:8000/docs`.

### 3. Frontend Setup
In a new terminal:
```bash
cd src/frontend
npm install
npm run dev
```
Open `http://localhost:3000` to access the GridPulse operations dashboard.

### 4. MCP Server Setup (Optional for AI Assistants)
In a third terminal:
```bash
cd src/mcp-server
npm install
npm test
```

---

## 🧪 Verification & Automated Tests

### Backend Test Suite
```bash
cd src
pytest tests -v
# 165 passed in ~12 seconds
```

### Frontend Production Build
```bash
cd src/frontend
npm run build
# Built cleanly with zero errors
```

### MCP Integration Smoke Tests
```bash
cd src/mcp-server
npm test
# 32 passed, 0 failed
```

---

## 🖥️ Demo Artifacts

- **Demo Video**: [demo/demo-video-link.txt](demo/demo-video-link.txt)
- **Live Demo Status**: [demo/live-demo-url.txt](demo/live-demo-url.txt) (Configured as `NOT DEPLOYED — run locally`)
- **Screenshots & Walkthrough**: [demo/screenshots/](demo/screenshots/)
- **Slide Deck**: [presentation/](presentation/) (`slides.pdf` and `slides.md`)

---

## ⚠️ Known Limitations & Non-Claims

1. **Decision Support, Not Physical Grid Control**: GridPulse is an operator decision-support advisory tool. It does NOT claim to directly operate physical high-voltage switchgear.
2. **Synthetic Telemetry**: The dataset is a mathematically sound, continuous 6-month synthetic microgrid time-series designed to represent real solar, wind, load, and grid events.
3. **Linearized Balancing Model**: The simulator focuses on active power balance (MW/MWh), intertie capacity, and battery SOC constraints; it does not model reactive power (VARs) or transmission line bus impedance matrices.
4. **Cloud AI Credentials**: watsonx.ai foundation models require IBM Cloud credentials. When running offline or unconfigured, robust deterministic statistical and template generators take over automatically.
