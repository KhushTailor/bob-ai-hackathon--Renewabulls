# IBM Bob Integration

This document describes exactly how IBM Bob is used in GridPulse — both as a development environment and as a runtime interface.

---

## 1. IBM Bob as Development Environment

IBM Bob was the primary AI development tool used to build GridPulse. Every source file in this repository was authored, reviewed, and refined through Bob's agent mode.

### What Bob Did

| Component | Bob's role |
|---|---|
| `src/data/generate_dataset.py` | Scaffolded and refined the synthetic data generator |
| `src/backend/services/` (all 6 services) | Implemented all service modules from scratch |
| `src/backend/routers/` (all 6 routers) | Generated FastAPI router files with Pydantic schemas |
| `src/backend/models/schemas.py` | Designed all Pydantic v2 response models |
| `src/frontend/` (all components) | Scaffolded React components and Recharts integrations |
| `src/mcp-server/index.ts` | Built the MCP server that connects Bob to GridPulse |
| `src/tests/` (all test files) | Generated test suites for all service modules |
| `docs/` (all documents) | Authored all documentation files |
| `.bob/skills/gridpulse/SKILL.md` | This skill itself — encodes domain knowledge for all sessions |

### The GridPulse Skill

The file `.bob/skills/gridpulse/SKILL.md` is a project-scoped Bob skill containing GridPulse domain knowledge:
- All 18 CSV column definitions
- All 12 anomaly rules with thresholds and severities
- Simulation action definitions and scoring weights
- IBM technology integration patterns (verified SDK imports, model IDs)
- Coding conventions enforced across the project

**Why this matters:** Bob did not approach GridPulse generically. The skill was activated at the start of every development session, ensuring that Bob's suggestions were consistent with the approved architecture, used the correct IBM model IDs, and respected all project constraints. This is a real, committed artifact that shaped every implementation decision.

---

## 2. IBM Bob & AI Assistants Tool Interface (MCP Server)

GridPulse includes a Model Context Protocol (MCP) server at `src/mcp-server/server.js` that exposes six GridPulse decision-support tools to IBM Bob, Antigravity, and other MCP-compatible AI assistants.

### What This Enables

Once the MCP server is started and registered, operators, developers, and AI agents can query live telemetry and run simulations directly:

```
User:  "What is the current grid status?"
Agent: [calls get_grid_status tool → GET /api/status]
Agent: "Grid frequency is 49.97 Hz (Nominal), demand is 204.5 MW,
        battery SOC is 50.2%, renewable generation is 47.18 MW (23.1% of demand)."

User:  "Simulate discharging the battery by 20 MW for 1 hour."
Agent: [calls simulate_grid_action tool → POST /api/simulate]
Agent: "Simulation complete: Action is FEASIBLE. Intertie import is relieved
        from 136.34 MW to 116.34 MW (-20.0 MW). Battery SOC declines from 50.2%
        to 25.2% (leaving 20.2% buffer above reserve). Strategy score is 80.0/100 (MEDIUM risk)."
```

### The Six Registered MCP Tools

| Tool | Backend Endpoint | Parameters | Description |
|---|---|---|---|
| `get_grid_status` | `GET /api/status` | None | Returns real-time grid telemetry: frequency, demand, solar, wind, renewable %, battery SOC, import |
| `get_active_alerts` | `GET /api/alerts` | None | Returns active anomaly alerts and red-flag breaches detected by the Anomaly Engine |
| `get_renewable_performance` | `GET /api/renewables` | None | Returns deterministic renewable KPIs: actual MW, capacity factors, performance ratios, underperformance |
| `get_demand_forecast` | `GET /api/forecast` | `horizon_hours` (def: 72) | Returns demand forecast points (288 steps for 72h at 15-minute resolution) |
| `simulate_grid_action` | `POST /api/simulate` | `action_type`, `amount_mw`, `duration_hours` | Evaluates feasibility, applied power, import relief, battery SOC trajectory, violations, score, risk |
| `generate_operator_brief` | `GET /api/operator-brief` | None | Returns the 6-question AI Operator Brief synthesizing live status, forecast, renewables, and simulations |

### MCP Server Registration

Add the server to your assistant's MCP configuration (e.g. Bob settings or `mcp_config.json`):

```json
{
  "mcpServers": {
    "gridpulse": {
      "command": "node",
      "args": ["[PATH_TO_REPO]/src/mcp-server/server.js"],
      "env": {
        "GRIDPULSE_API_URL": "http://127.0.0.1:8000"
      }
    }
  }
}
```

---

## 3. Strict Architectural Distinctions & What IBM Bob is NOT

To maintain technical honesty and accuracy:

- **IBM Bob / Antigravity is an AI-assisted development environment**, not an application runtime. Bob was used to architect, scaffold, write, test, and refine the codebase. Bob can also interact with the running system through MCP tools.
- **MCP is an open standard tool interface layer**, not an IBM service or proprietary technology. It acts strictly as a communication bridge between an AI assistant and the GridPulse backend.
- **GridPulse Backend is the independent application runtime.** Built in Python FastAPI, it runs standalone and executes all physics, telemetry calculations, and deterministic simulations. MCP does NOT prove IBM Bob is running the application.
- **watsonx.ai is an optional runtime AI inference capability.** Foundation models (`ibm/granite-3-3-8b-instruct` and `ibm/granite-ttm-512-96-r2`) are queried directly via the IBM watsonx REST API only when environment credentials are configured. In offline mode, deterministic statistical and template fallbacks operate seamlessly.
- **Bob is NOT the forecasting engine.** Demand forecasting uses `ibm/granite-ttm-512-96-r2` via the watsonx.ai time-series forecast API — again a separate service.

---

## 4. IBM Technology Summary

| IBM Technology | Role | Load-bearing? | Evidence |
|---|---|---|---|
| IBM Bob | Development environment + MCP runtime interface | Yes | This document; SKILL.md; MCP server source code |
| watsonx.ai Granite TTM (`ibm/granite-ttm-512-96-r2`) | Zero-shot 72-hour demand forecast (Feature 1) | Yes (with fallback) | `src/backend/services/forecaster.py` |
| watsonx.ai Granite Instruct (`ibm/granite-3-3-8b-instruct`) | Natural-language Operator Brief (Feature 5) | Yes (with fallback) | `src/backend/services/brief_generator.py` |
