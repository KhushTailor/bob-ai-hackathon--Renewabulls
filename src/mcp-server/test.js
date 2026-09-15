#!/usr/bin/env node
/**
 * GridPulse MCP Server — Smoke Test & Verification Suite
 *
 * Connects an MCP Client directly to the GridPulse MCP Server using InMemoryTransport.
 * Verifies:
 * 1. Server initialization and tool registration (all 6 tools)
 * 2. Execution of get_grid_status
 * 3. Execution of get_active_alerts
 * 4. Execution of get_renewable_performance
 * 5. Execution of get_demand_forecast
 * 6. Execution of simulate_grid_action
 * 7. Execution of generate_operator_brief
 */

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { createServer, TOOLS } from "./server.js";

async function runSmokeTests() {
  console.log("=================================================");
  console.log("  GridPulse MCP Server — Smoke & Integration Test");
  console.log("=================================================\n");

  let passed = 0;
  let failed = 0;

  function assert(condition, testName, detail = "") {
    if (condition) {
      console.log(`  ✓ PASS: ${testName} ${detail ? `(${detail})` : ""}`);
      passed++;
    } else {
      console.error(`  ✗ FAIL: ${testName} ${detail ? `(${detail})` : ""}`);
      failed++;
    }
  }

  // 1. Initialize Server and Client
  console.log("Step 1: Initializing MCP Server & Client via InMemoryTransport...");
  const server = createServer();
  const client = new Client(
    { name: "gridpulse-test-client", version: "0.1.0" },
    { capabilities: {} }
  );

  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();

  await Promise.all([
    server.connect(serverTransport),
    client.connect(clientTransport),
  ]);
  console.log("  ✓ Server and Client connected successfully.\n");

  // 2. Verify Tool Registration
  console.log("Step 2: Verifying Tool Registration...");
  const { tools } = await client.listTools();
  const registeredNames = tools.map((t) => t.name);

  const EXPECTED_TOOLS = [
    "get_grid_status",
    "get_active_alerts",
    "get_renewable_performance",
    "get_demand_forecast",
    "simulate_grid_action",
    "generate_operator_brief",
  ];

  assert(tools.length === 6, "Registered tool count is 6", `got ${tools.length}`);

  for (const expected of EXPECTED_TOOLS) {
    assert(registeredNames.includes(expected), `Tool registered: ${expected}`);
  }
  console.log();

  // 3. Test Tool Invocations
  console.log("Step 3: Testing Tool Executions against GridPulse Backend...");

  // Tool 1: get_grid_status
  try {
    const res1 = await client.callTool({ name: "get_grid_status", arguments: {} });
    assert(!res1.isError, "Tool 1: get_grid_status executes without error");
    const data1 = JSON.parse(res1.content[0].text);
    assert(typeof data1.frequency_hz === "number", "get_grid_status returns frequency_hz", `${data1.frequency_hz} Hz`);
    assert(typeof data1.demand_mw === "number", "get_grid_status returns demand_mw", `${data1.demand_mw} MW`);
    assert(typeof data1.battery_soc_pct === "number", "get_grid_status returns battery_soc_pct", `${data1.battery_soc_pct}%`);
  } catch (err) {
    assert(false, "Tool 1: get_grid_status threw exception", err.message);
  }

  // Tool 2: get_active_alerts
  try {
    const res2 = await client.callTool({ name: "get_active_alerts", arguments: {} });
    assert(!res2.isError, "Tool 2: get_active_alerts executes without error");
    const data2 = JSON.parse(res2.content[0].text);
    assert(Array.isArray(data2.alerts), "get_active_alerts returns alerts array", `${data2.alerts?.length} alerts`);
  } catch (err) {
    assert(false, "Tool 2: get_active_alerts threw exception", err.message);
  }

  // Tool 3: get_renewable_performance
  try {
    const res3 = await client.callTool({ name: "get_renewable_performance", arguments: {} });
    assert(!res3.isError, "Tool 3: get_renewable_performance executes without error");
    const data3 = JSON.parse(res3.content[0].text);
    assert(data3.solar && typeof data3.solar.actual_generation_mw === "number", "get_renewable_performance returns solar actual MW", `${data3.solar?.actual_generation_mw} MW`);
    assert(data3.wind && typeof data3.wind.actual_generation_mw === "number", "get_renewable_performance returns wind actual MW", `${data3.wind?.actual_generation_mw} MW`);
    assert(data3.combined && typeof data3.combined.total_renewable_mw === "number", "get_renewable_performance returns combined total MW", `${data3.combined?.total_renewable_mw} MW`);
  } catch (err) {
    assert(false, "Tool 3: get_renewable_performance threw exception", err.message);
  }

  // Tool 4: get_demand_forecast
  try {
    const res4 = await client.callTool({
      name: "get_demand_forecast",
      arguments: { horizon_hours: 72 },
    });
    assert(!res4.isError, "Tool 4: get_demand_forecast executes without error");
    const data4 = JSON.parse(res4.content[0].text);
    assert(data4.horizon_hours === 72, "get_demand_forecast horizon_hours is 72");
    assert(Array.isArray(data4.points) && data4.points.length === 288, "get_demand_forecast returns 288 points", `${data4.points?.length} points`);
  } catch (err) {
    assert(false, "Tool 4: get_demand_forecast threw exception", err.message);
  }

  // Tool 5: simulate_grid_action
  try {
    const res5 = await client.callTool({
      name: "simulate_grid_action",
      arguments: {
        action_type: "BATTERY_DISPATCH",
        amount_mw: 20.0,
        duration_hours: 1.0,
      },
    });
    assert(!res5.isError, "Tool 5: simulate_grid_action executes without error");
    const data5 = JSON.parse(res5.content[0].text);
    assert(data5.is_feasible === true, "simulate_grid_action reports is_feasible=true");
    assert(data5.applied_action_mw === 20.0, "simulate_grid_action applied_action_mw=20.0");
    assert(data5.unmet_action_mw === 0.0, "simulate_grid_action unmet_action_mw=0.0");
    assert(data5.battery_soc_change && data5.battery_soc_change.after_pct === 25.2, "simulate_grid_action ending SOC=25.2%", `${data5.battery_soc_change?.after_pct}%`);
    assert(data5.grid_import_change && data5.grid_import_change.relief_mw === 20.0, "simulate_grid_action relief_mw=20.0", `${data5.grid_import_change?.relief_mw} MW`);
    assert(data5.score === 80.0, "simulate_grid_action score=80.0", `${data5.score}`);
    assert(data5.risk_severity === "MEDIUM", "simulate_grid_action risk_severity=MEDIUM", `${data5.risk_severity}`);
  } catch (err) {
    assert(false, "Tool 5: simulate_grid_action threw exception", err.message);
  }

  // Tool 6: generate_operator_brief
  try {
    const res6 = await client.callTool({ name: "generate_operator_brief", arguments: {} });
    assert(!res6.isError, "Tool 6: generate_operator_brief executes without error");
    const data6 = JSON.parse(res6.content[0].text);
    assert(typeof data6.situation === "string" && data6.situation.length > 0, "generate_operator_brief returns situation");
    assert(typeof data6.recommended_action === "string" && data6.recommended_action.length > 0, "generate_operator_brief returns recommended_action");
    assert(typeof data6.severity === "string", "generate_operator_brief returns severity", data6.severity);
  } catch (err) {
    assert(false, "Tool 6: generate_operator_brief threw exception", err.message);
  }

  console.log("\n=================================================");
  console.log(`  Test Results: ${passed} Passed, ${failed} Failed`);
  console.log("=================================================\n");

  await client.close();
  await server.close();

  if (failed > 0) {
    process.exit(1);
  }
}

runSmokeTests().catch((err) => {
  console.error("Fatal error during smoke tests:", err);
  process.exit(1);
});
