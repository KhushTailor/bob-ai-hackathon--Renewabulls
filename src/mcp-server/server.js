#!/usr/bin/env node
/**
 * GridPulse MCP Server
 *
 * Model Context Protocol (MCP) tool integration layer for GridPulse.
 * Exposes real-time electricity grid telemetry, anomaly alerts, renewable performance,
 * 72-hour demand forecasting, what-if action simulation, and AI operator briefs
 * to IBM Bob and MCP-compatible AI assistants.
 *
 * Architecture:
 * MCP Server (Tool Interface) -> GridPulse FastAPI Backend (/api/*) -> Core Domain Services
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

const GRIDPULSE_API_URL = process.env.GRIDPULSE_API_URL || "http://127.0.0.1:8000";

/**
 * Fetch helper for GridPulse FastAPI backend
 */
export async function callBackend(endpoint, options = {}) {
  const url = `${GRIDPULSE_API_URL}${endpoint}`;
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        "Accept": "application/json",
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
    });

    if (!res.ok) {
      const errorText = await res.text().catch(() => "");
      throw new Error(`GridPulse API returned status ${res.status} ${res.statusText}: ${errorText}`);
    }

    return await res.json();
  } catch (err) {
    if (err.cause?.code === "ECONNREFUSED" || (err.message && err.message.includes("fetch failed"))) {
      throw new Error(
        `Unable to connect to GridPulse backend at ${url}. ` +
        `Ensure the FastAPI backend is running (e.g., 'uvicorn backend.main:app --port 8000'). ` +
        `Details: ${err.message}`
      );
    }
    throw err;
  }
}

/**
 * Six Required MCP Tools
 */
export const TOOLS = [
  {
    name: "get_grid_status",
    description:
      "Returns the current GridPulse grid status and real-time operational telemetry (frequency, demand, solar, wind, renewable %, battery SOC, intertie import, and overall status).",
    inputSchema: {
      type: "object",
      properties: {},
    },
  },
  {
    name: "get_active_alerts",
    description:
      "Returns active grid anomaly alerts, threshold breaches, and red-flag events detected by the GridPulse Anomaly Engine.",
    inputSchema: {
      type: "object",
      properties: {},
    },
  },
  {
    name: "get_renewable_performance",
    description:
      "Returns deterministic renewable performance monitoring KPIs for solar, wind, and combined renewable generation.",
    inputSchema: {
      type: "object",
      properties: {},
    },
  },
  {
    name: "get_demand_forecast",
    description:
      "Returns the electricity demand forecast across a specified time horizon (default 72 hours, 15-minute resolution).",
    inputSchema: {
      type: "object",
      properties: {
        horizon_hours: {
          type: "number",
          description: "Forecast horizon in hours (default: 72, corresponding to 288 15-minute intervals).",
          default: 72,
        },
      },
    },
  },
  {
    name: "simulate_grid_action",
    description:
      "Simulates a proposed grid balancing action (BATTERY_DISPATCH, LOAD_SHIFT, GRID_IMPORT, or RENEWABLE_CURTAILMENT) across a 72-hour horizon. Evaluates feasibility, applied/unmet power, grid import relief, battery SOC trajectory, constraint violations, and overall decision-support score.",
    inputSchema: {
      type: "object",
      properties: {
        action_type: {
          type: "string",
          description: "Intervention type: BATTERY_DISPATCH, LOAD_SHIFT, GRID_IMPORT, or RENEWABLE_CURTAILMENT.",
          enum: ["BATTERY_DISPATCH", "LOAD_SHIFT", "GRID_IMPORT", "RENEWABLE_CURTAILMENT"],
        },
        amount_mw: {
          type: "number",
          description: "Target power magnitude in MW.",
        },
        duration_hours: {
          type: "number",
          description: "Intervention duration in hours (default: 1.0).",
          default: 1.0,
        },
      },
      required: ["action_type", "amount_mw"],
    },
  },
  {
    name: "generate_operator_brief",
    description:
      "Returns the current AI Operator Brief synthesizing live grid status, active alerts, renewable performance, demand forecast, and what-if simulation into an actionable decision-support summary answering six key operational questions.",
    inputSchema: {
      type: "object",
      properties: {},
    },
  },
];

/**
 * Creates and configures an MCP Server instance
 */
export function createServer() {
  const server = new Server(
    {
      name: "gridpulse-mcp-server",
      version: "0.1.0",
    },
    {
      capabilities: {
        tools: {},
      },
    }
  );

  server.setRequestHandler(ListToolsRequestSchema, async () => {
    return { tools: TOOLS };
  });

  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args = {} } = request.params;

    try {
      let result;

      switch (name) {
        case "get_grid_status": {
          result = await callBackend("/api/status");
          break;
        }

        case "get_active_alerts": {
          result = await callBackend("/api/alerts");
          break;
        }

        case "get_renewable_performance": {
          result = await callBackend("/api/renewables");
          break;
        }

        case "get_demand_forecast": {
          const horizon = args.horizon_hours !== undefined ? Number(args.horizon_hours) : 72;
          result = await callBackend(`/api/forecast?horizon_hours=${encodeURIComponent(horizon)}`);
          break;
        }

        case "simulate_grid_action": {
          const action = args.action_type || args.action;
          if (!action) {
            throw new Error("Missing required parameter 'action_type'.");
          }
          if (args.amount_mw === undefined || args.amount_mw === null) {
            throw new Error("Missing required parameter 'amount_mw'.");
          }

          const amount_mw = Number(args.amount_mw);
          const duration_hours = args.duration_hours !== undefined ? Number(args.duration_hours) : 1.0;

          const simData = await callBackend("/api/simulate", {
            method: "POST",
            body: JSON.stringify({
              action,
              amount_mw,
              duration_hours,
            }),
          });

          result = {
            scenario_id: simData.scenario_id,
            action: simData.action,
            amount_mw: simData.amount_mw,
            duration_hours: simData.duration_hours,
            is_feasible: simData.is_feasible,
            explanation: simData.explanation,
            applied_action_mw: simData.applied_action_mw,
            unmet_action_mw: simData.unmet_action_mw,
            grid_import_change: {
              original_mw: simData.original_grid_import_mw,
              adjusted_mw: simData.adjusted_grid_import_mw,
              relief_mw: +(simData.original_grid_import_mw - simData.adjusted_grid_import_mw).toFixed(2),
            },
            battery_soc_change: {
              before_pct: simData.battery_soc_before_pct,
              after_pct: simData.battery_soc_after_pct,
              delta_pct: +(simData.battery_soc_before_pct - simData.battery_soc_after_pct).toFixed(2),
            },
            constraint_violations: simData.constraint_violations,
            score: simData.score,
            risk_severity: simData.risk_severity,
          };
          break;
        }

        case "generate_operator_brief": {
          result = await callBackend("/api/operator-brief");
          break;
        }

        default:
          throw new Error(`Unknown tool requested: ${name}`);
      }

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(result, null, 2),
          },
        ],
      };
    } catch (error) {
      return {
        isError: true,
        content: [
          {
            type: "text",
            text: `Error executing tool '${name}': ${error.message}`,
          },
        ],
      };
    }
  });

  return server;
}

export async function runServer() {
  const server = createServer();
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("GridPulse MCP Server running via stdio transport (PID: " + process.pid + ")");
}

const isMain = process.argv[1] && (
  process.argv[1].endsWith("server.js") ||
  import.meta.url === `file://${process.argv[1].replace(/\\/g, "/")}`
);

if (isMain) {
  runServer().catch((error) => {
    console.error("Fatal error running GridPulse MCP Server:", error);
    process.exit(1);
  });
}
