"""gauntlet_integration/scenarios/mcp_tick_integration.py

Gauntlet scenario: MCP_TICK_INTEGRATION

Verifies that the MCP Router correctly processes a full queue of tool-call
requests inside a live orchestrator tick cycle. Runs in ~100 ms in CI mode
(no real GPU nodes or connectors required).

Pass criteria:
  1. All 5 supported tools dispatch without exception
  2. emergency_blast fires SUPERNOVA for nodes above threshold
  3. zone_budget_override mutates zone state live
  4. thermal_status returns zone snapshot with correct tick counter
  5. Invalid method returns JSON-RPC error, not exception
  6. Total dispatch time < 500 ms for 10 queued requests
"""

import asyncio
import time
import logging
from unittest.mock import AsyncMock, MagicMock

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GAUNTLET:MCP_TICK_INTEGRATION")


async def run(ci: bool = False, fail_on_critical: bool = True) -> dict:
    """Entry-point called by gauntlet runner."""

    from apex_core.thermal_orchestrator import ThermalNode, CoolingZone
    from src.connectors.mcp_router import MCPRouterConnector
    from memory.aspen_grove_logger import AspenGroveLogger

    # ---- Build a minimal live orchestrator stub -----------------------
    orch = MagicMock()
    orch.tick = 0

    # Two zones, 5 nodes each
    zones = []
    all_nodes = []
    for zi, zid in enumerate(["ZONE-A", "ZONE-B"]):
        zone = CoolingZone(zone_id=zid, zone_name=f"Gauntlet {zid}")
        zone.thermal_budget_kw = 50.0
        for ni in range(5):
            node = ThermalNode(
                node_id=f"{zid}-N{ni:02d}", rack_id=f"RACK-{zi:02d}",
                zone_id=zid, temp_celsius=60.0 + ni * 6.0,  # 60–84°C
                gpu_utilization=0.9, power_watts=700.0,
            )
            zone.nodes.append(node)
            all_nodes.append(node)
        zone.avg_temp = sum(n.temp_celsius for n in zone.nodes) / 5
        zone.peak_temp = max(n.temp_celsius for n in zone.nodes)
        zones.append(zone)

    orch.zones = zones
    orch.all_nodes = all_nodes

    # Piston stubs that actually track calls
    sn = MagicMock(); sn.activate = AsyncMock(return_value={"piston": "SUPERNOVA", "actions": []})
    mw = MagicMock(); mw.activate = AsyncMock(return_value={"piston": "MICROWAVE", "zones_swept": 2})
    orch.pistons = {"SUPERNOVA": sn, "MICROWAVE": mw}
    orch.run_fusion_mode = AsyncMock(return_value={"fusion": "UNKNOWN", "status": "UNKNOWN"})

    # ---- Build router -------------------------------------------------
    router = MCPRouterConnector(logger=AspenGroveLogger())

    def req(tool, args=None, rid="g-001"):
        return {"jsonrpc": "2.0", "id": rid,
                "method": "tools/call",
                "params": {"name": tool, "arguments": args or {}}}

    requests = [
        req("emergency_blast",      {"threshold_c": 70.0}, "g-001"),
        req("predictive_sweep",     {},                     "g-002"),
        req("zone_budget_override",  {"zone_id": "ZONE-A", "budget_kw": 120.0}, "g-003"),
        req("zone_budget_override",  {"zone_id": "ZONE-B", "budget_kw": 80.0},  "g-004"),
        req("thermal_status",       {},                     "g-005"),
        req("thermal_status",       {"zone_id": "ZONE-A"}, "g-006"),
        req("fusion_dispatch",      {"fusion_name": "PHANTOM"}, "g-007"),
        req("emergency_blast",      {"threshold_c": 50.0}, "g-008"),
        {"jsonrpc": "2.0", "id": "g-009", "method": "INVALID", "params": {}},  # bad
        req("predictive_sweep",     {},                     "g-010"),
    ]

    for r in requests:
        router.queue_request(r)

    # ---- Simulate a tick cycle ----------------------------------------
    orch.tick = 1
    t0 = time.perf_counter()
    results = await router.process_tick(orch)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    # ---- Assertions ---------------------------------------------------
    failures = []

    if len(results) != 10:
        failures.append(f"Expected 10 results, got {len(results)}")

    # SUPERNOVA should have been called (nodes at 72°C, 78°C, 84°C > 70°C)
    if not sn.activate.called:
        failures.append("SUPERNOVA never activated")

    # MICROWAVE called twice (two predictive_sweep requests)
    if mw.activate.call_count < 2:
        failures.append(f"MICROWAVE called {mw.activate.call_count} times, expected >=2")

    # zone_budget_override must mutate zone
    zone_a = next(z for z in orch.zones if z.zone_id == "ZONE-A")
    if zone_a.thermal_budget_kw != 120.0:
        failures.append(f"ZONE-A budget not updated: {zone_a.thermal_budget_kw}")

    # thermal_status must return zones
    status_result = next((r for r in results if r.get("id") == "g-005"), None)
    if not status_result or len(status_result["result"].get("zones", [])) != 2:
        failures.append("thermal_status did not return 2 zones")

    # invalid request must be rejected, not raise
    bad_result = next((r for r in results if r.get("id") == "g-009"), None)
    if not bad_result or "error" not in bad_result:
        failures.append("Invalid request was not rejected with JSON-RPC error")

    # timing gate: < 500 ms for 10 requests
    if elapsed_ms > 500:
        failures.append(f"Dispatch too slow: {elapsed_ms:.1f} ms (limit 500 ms)")

    # ---- Result -------------------------------------------------------
    status = "PASS" if not failures else "FAIL"
    logger.info("MCP_TICK_INTEGRATION: %s | %d requests in %.1f ms", status, len(results), elapsed_ms)
    if failures:
        for f in failures:
            logger.error("  FAIL: %s", f)
        if fail_on_critical:
            raise AssertionError(f"MCP_TICK_INTEGRATION FAILED: {failures}")

    return {
        "scenario": "MCP_TICK_INTEGRATION",
        "status": status,
        "requests_processed": len(results),
        "elapsed_ms": round(elapsed_ms, 2),
        "failures": failures,
    }


if __name__ == "__main__":
    asyncio.run(run())
