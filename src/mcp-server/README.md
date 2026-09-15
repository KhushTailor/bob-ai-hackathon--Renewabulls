# GridPulse MCP Server

The **GridPulse MCP Server** is a Model Context Protocol (MCP) tool interface that exposes GridPulse's decision-support capabilities to AI assistants, including **IBM Bob**, **Antigravity**, and other MCP-compatible environments.

---

## Architectural Distinctions

It is essential to distinguish the roles of the various components across the stack:

| Component | Nature / Scope | Role in GridPulse |
| :--- | :--- | :--- |
| **IBM Bob / Antigravity** | AI-Assisted Development Environment | Used to develop, scaffold, test, and refine the codebase. Can also query the running system via MCP tools. |
| **Model Context Protocol (MCP)** | Open Tool Interface Layer | Standardized JSON-RPC/stdio protocol allowing AI assistants to discover and invoke tools. Not an IBM service. |
| **GridPulse Backend** | Application Runtime | Python FastAPI server hosting the deterministic physics, telemetry models, and REST endpoints (`/api/*`). |
| **watsonx.ai** | Runtime AI Capability (Optional) | Cloud foundation models (`granite-3-3-8b-instruct` / `granite-ttm`) utilized only when explicitly configured via environment credentials. |

> **Note:** The presence of an MCP server does **not** indicate that IBM Bob is running the application backend. The backend runs independently on FastAPI; the MCP server acts solely as a standard tool bridge.

---

## Architecture Flow

```
[ IBM Bob / AI Assistant ]
         │
         ▼ (stdio / JSON-RPC via Model Context Protocol)
[ GridPulse MCP Server ] (src/mcp-server/server.js)
         │
         ▼ (HTTP JSON fetch)
[ GridPulse Backend API ] (http://127.0.0.1:8000/api/*)
         │
   ┌─────┴─────────────────────────┐
   ▼                               ▼
[ Core Domain Services ]     [ Dataset / State ]
(forecaster, renewables,      (grid_data.csv)
 anomaly engine, simulator,
 operator brief)
```

The MCP server adheres strictly to the rule: **No business logic or physics calculations are duplicated inside MCP**. All calls delegate directly to the GridPulse FastAPI backend endpoints.

---

## The Six Registered MCP Tools

### 1. `get_grid_status`
- **Description:** Returns the current grid status and real-time operational telemetry (frequency, demand, solar, wind, renewable %, battery SOC, intertie import, and overall status).
- **Backend Endpoint:** `GET /api/status`
- **Parameters:** None.

### 2. `get_active_alerts`
- **Description:** Returns active anomaly detection alerts, threshold breaches, and red-flag events detected by the 12-rule Anomaly Engine.
- **Backend Endpoint:** `GET /api/alerts`
- **Parameters:** None.

### 3. `get_renewable_performance`
- **Description:** Returns deterministic renewable performance monitoring KPIs for solar, wind, and combined renewable generation (actual generation, capacity factors, expected output, performance ratios, and underperformance flags).
- **Backend Endpoint:** `GET /api/renewables`
- **Parameters:** None.

### 4. `get_demand_forecast`
- **Description:** Returns the 72-hour electricity demand forecast (288 15-minute intervals) using seasonal naive or Granite TTM.
- **Backend Endpoint:** `GET /api/forecast?horizon_hours={horizon_hours}`
- **Parameters:**
  - `horizon_hours` *(number, optional, default: 72)*: Forecast horizon in hours.

### 5. `simulate_grid_action`
- **Description:** Runs a deterministic 72-hour what-if simulation for a proposed grid balancing intervention (`BATTERY_DISPATCH`, `LOAD_SHIFT`, `GRID_IMPORT`, or `RENEWABLE_CURTAILMENT`). Evaluates physical feasibility, unmet power, grid import relief, battery SOC trajectory, constraint violations, and overall decision-support score.
- **Backend Endpoint:** `POST /api/simulate`
- **Parameters:**
  - `action_type` *(string, required)*: `BATTERY_DISPATCH` | `LOAD_SHIFT` | `GRID_IMPORT` | `RENEWABLE_CURTAILMENT`
  - `amount_mw` *(number, required)*: Magnitude in MW
  - `duration_hours` *(number, optional, default: 1.0)*: Action duration in hours

### 6. `generate_operator_brief`
- **Description:** Retrieves the AI Operator Brief synthesizing grid status, alerts, forecast, renewables, and simulations into an actionable decision-support summary answering six core operational questions.
- **Backend Endpoint:** `GET /api/operator-brief`
- **Parameters:** None.

---

## Prerequisites & Installation

1. **Node.js**: Version 18.0+ (Tested on Node v24.20.0).
2. **FastAPI Backend**: Ensure the GridPulse backend is running:
   ```bash
   cd src
   uvicorn backend.main:app --port 8000
   ```

3. **Install Dependencies**:
   ```bash
   cd src/mcp-server
   npm install
   ```

---

## Verification & Smoke Tests

The repository includes an in-memory client test suite that validates server startup, tool registration, and live tool invocations:

```bash
cd src/mcp-server
npm test
```

Expected output:
```
=================================================
  GridPulse MCP Server — Smoke & Integration Test
=================================================

Step 1: Initializing MCP Server & Client via InMemoryTransport...
  ✓ Server and Client connected successfully.

Step 2: Verifying Tool Registration...
  ✓ PASS: Registered tool count is 6 (got 6)
  ✓ PASS: Tool registered: get_grid_status 
  ✓ PASS: Tool registered: get_active_alerts 
  ✓ PASS: Tool registered: get_renewable_performance 
  ✓ PASS: Tool registered: get_demand_forecast 
  ✓ PASS: Tool registered: simulate_grid_action 
  ✓ PASS: Tool registered: generate_operator_brief 

Step 3: Testing Tool Executions against GridPulse Backend...
  ✓ PASS: Tool 1: get_grid_status executes without error
  ...
=================================================
  Test Results: 20 Passed, 0 Failed
=================================================
```

---

## Configuration for IBM Bob & AI Assistants

To connect IBM Bob, Antigravity, or Claude Desktop to GridPulse via MCP, add the server to your tool configuration:

```json
{
  "mcpServers": {
    "gridpulse": {
      "command": "node",
      "args": ["c:/Users/khush/.bob/playground/src/mcp-server/server.js"],
      "env": {
        "GRIDPULSE_API_URL": "http://127.0.0.1:8000"
      }
    }
  }
}
```
