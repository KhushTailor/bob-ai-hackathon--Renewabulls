# Solution Overview

## What We Built

GridPulse is an AI-assisted grid optimisation dashboard that consolidates demand forecasting, renewable performance monitoring, anomaly detection, what-if simulation, and natural-language operator briefing into a single decision-ready interface. It is built for distribution system operators managing renewable-heavy microgrids who need to move from raw telemetry to a clear recommended action in under 60 seconds.

## How It Works

1. **Data ingestion:** A synthetic dataset (6 months, 15-minute intervals) simulates a realistic grid with solar, wind, battery storage, and grid interconnection. A generation script can extend or replay this data for demonstrations.

2. **Demand forecasting:** The FastAPI backend calls the IBM Granite time-series model (`ibm/granite-ttm-512-96-r2`) via the watsonx.ai API, passing the last 512 data points of demand history. The model returns a 96-point (24-hour) zero-shot forecast. Three sequential calls produce the 72-hour horizon. A statsmodels STL decomposition fallback is always available for offline use.

3. **Renewable performance monitoring:** For each 15-minute interval, the backend computes the expected solar and wind generation from irradiance and wind-speed data using physics-based models (efficiency factor and IEC Class II power curve). Actual vs. expected ratios, curtailment estimates, and underperformance flags are calculated in Pandas and served via the API.

4. **Anomaly detection:** Twelve deterministic threshold rules are applied to each incoming data row, covering grid frequency, voltage, demand surges, battery state, renewable underperformance, and curtailment events. Each triggered rule produces a structured alert with severity (CRITICAL/WARNING/INFO), value, threshold, and a recommended action category.

5. **What-if simulation:** When an imbalance is detected, the simulator evaluates four balancing actions (battery dispatch, load shift, grid import, renewable curtailment) over the 72-hour forecast window. Each action is scored on grid stability, renewable utilisation, cost, and risk using deterministic formulas. The highest composite score becomes the recommended action with a plain-English explanation.

6. **AI Operator Brief:** The structured simulation result is passed as a prompt to IBM Granite (`ibm/granite-3-3-8b-instruct`) via the watsonx.ai text generation API. The model returns a 150–200 word brief covering all six decision-critical questions. A Jinja2 template provides an equivalent brief when watsonx.ai credentials are not available.

7. **Dashboard:** The React frontend polls all API endpoints every 30 seconds and renders the complete picture: four KPI cards, a 72-hour forecast chart with confidence band, a renewable performance chart, an alert panel, a simulation action-score chart, the recommended action card, and the Operator Brief text panel.

## Architecture Diagram

See [`architecture.md`](architecture.md) for the detailed component diagram.

```
CSV Data (6 months, 17,520 rows)
       |
       +-- Granite TTM (watsonx.ai) ----> [Feature 1: Demand Forecast + 72h horizon]
       |   OR STL statistical fallback
       |
       +-- Pandas rules (physics) ------> [Feature 2: Renewable Performance Monitor]
       |
       +-- 12 threshold rules ----------> [Feature 3: Anomaly & Red-Flag Engine]
       |
       +-- Deterministic scorer --------> [Feature 4: 72-Hour What-If Simulation]
       |
       +-- Granite Instruct (watsonx.ai)> [Feature 5: AI Operator Brief]
           OR Jinja2 template fallback

FastAPI (8 endpoints) ---> React 18 + Recharts (single-page dashboard)

IBM Bob MCP server (3 tools) ---> Bob chat can query live GridPulse data
```

## Key Design Decisions

| Decision | Rationale |
|---|---|
| IBM Granite TTM for forecasting | Purpose-built IBM foundation model trained on electricity data; zero-shot inference removes the training-time risk from the demo |
| Rule-based anomaly detection | Safety-critical domain demands explainability; 12 deterministic rules are auditable and produce zero false positives on nominal data |
| Deterministic simulation scoring | Every score is traceable to a formula; operators and judges can verify the recommendation logic |
| CSV + Pandas (no database) | Eliminates the most common demo failure point (database connection); all features work from a single file |
| Dual watsonx.ai toggle flags | `WATSONX_GRANITE_TTM_ENABLED` and `WATSONX_BRIEF_ENABLED` are independent — the demo never fails due to missing credentials |
| IBM Bob MCP server | Moves IBM Bob from a background dev tool to a visible runtime interface; judges can interact with GridPulse through Bob's chat during the demo |

## IBM Technologies Used

- **IBM Bob:** Used as the AI development environment for the entire project. Every source file was authored, reviewed, and refined through Bob. The project includes a custom GridPulse skill (`.bob/skills/gridpulse/SKILL.md`) that encodes domain knowledge, and an MCP server (`src/mcp-server/`) that exposes three GridPulse tools to Bob for live runtime queries.

- **watsonx.ai — IBM Granite TTM (`ibm/granite-ttm-512-96-r2`):** Used for zero-shot demand forecasting. The model was trained on electricity, traffic, and manufacturing time-series data. GridPulse passes 512 historical demand data points and receives a 96-point forecast. Three sequential calls produce the full 72-hour horizon displayed on the dashboard.

- **watsonx.ai — IBM Granite Instruct (`ibm/granite-3-3-8b-instruct`):** Used to generate the natural-language AI Operator Brief. A structured prompt containing grid status, active alerts, simulation recommendation, and context variables is sent to the model, which returns a 150–200 word brief answering the six decision-critical questions.
