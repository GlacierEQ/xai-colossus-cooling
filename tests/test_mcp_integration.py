"""tests/test_mcp_integration.py

MCP Router integration tests — issue #16 acceptance criteria.

Covers:
  1. Enqueue request → tick → response dequeued (round-trip)
  2. emergency_blast tool
  3. predictive_sweep tool
  4. zone_budget_override tool (happy + error paths)
  5. fusion_dispatch tool (unknown fusion)
  6. thermal_status tool (all zones + filtered)
  7. Invalid request rejection (code -32600)
  8. asyncio.Queue drain via queue_async()
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Minimal stubs so the router can be imported without full Colossus stack
# ---------------------------------------------------------------------------

class _FakeValidator:
    def validate(self, req):
        if req.get("method") == "INVALID":
            return False, "Bad method"
        return True, ""


class _FakeLogger:
    def __init__(self):
        self.events = []

    def log_event(self, event):
        self.events.append(event)

    def start(self):
        pass


def _make_node(node_id, temp_c=65.0, zone_id="ZONE-A"):
    from apex_core.thermal_orchestrator import ThermalNode
    return ThermalNode(
        node_id=node_id, rack_id="RACK-000", zone_id=zone_id,
        temp_celsius=temp_c, gpu_utilization=0.85, power_watts=700.0,
    )


def _make_zone(zone_id="ZONE-A", nodes=None):
    from apex_core.thermal_orchestrator import CoolingZone
    z = CoolingZone(zone_id=zone_id, zone_name=f"Test {zone_id}")
    z.nodes = nodes or []
    z.avg_temp = sum(n.temp_celsius for n in z.nodes) / max(len(z.nodes), 1)
    z.peak_temp = max((n.temp_celsius for n in z.nodes), default=0.0)
    z.thermal_budget_kw = 100.0
    return z


def _make_orchestrator(zones=None, nodes=None):
    """Lightweight fake orchestrator — no real __init__ invoked."""
    orch = MagicMock()
    orch.zones = zones or []
    orch.all_nodes = nodes or []
    orch.tick = 42

    # Piston stubs
    sn_piston = MagicMock()
    sn_piston.activate = AsyncMock(return_value={"piston": "SUPERNOVA", "actions": []})
    mw_piston = MagicMock()
    mw_piston.activate = AsyncMock(return_value={"piston": "MICROWAVE", "zones_swept": len(orch.zones)})
    orch.pistons = {"SUPERNOVA": sn_piston, "MICROWAVE": mw_piston}

    # Fusion stub
    orch.run_fusion_mode = AsyncMock(return_value={"fusion": "UNKNOWN", "status": "UNKNOWN"})

    return orch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_router():
    """Build MCPRouterConnector with fake deps injected."""
    import importlib, sys

    # Stub out heavy deps before import
    validator_mod = MagicMock()
    validator_mod.MCPRequestValidator = _FakeValidator
    sys.modules.setdefault("schemas.mcp_request_validator", validator_mod)

    logger_mod = MagicMock()
    logger_mod.AspenGroveLogger = _FakeLogger
    sys.modules.setdefault("memory.aspen_grove_logger", logger_mod)

    # Force re-import with stubs in place
    mod_name = "src.connectors.mcp_router"
    if mod_name in sys.modules:
        del sys.modules[mod_name]

    from src.connectors.mcp_router import MCPRouterConnector
    router = MCPRouterConnector(logger=_FakeLogger())
    return router


def _req(tool_name, args=None, req_id="test-001"):
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": args or {}},
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_round_trip_emergency_blast():
    """Enqueue → tick → response dequeued (emergency_blast)."""
    router = _make_router()
    node_hot = _make_node("N-HOT", temp_c=85.0)
    node_cold = _make_node("N-COLD", temp_c=40.0)
    orch = _make_orchestrator(nodes=[node_hot, node_cold])

    router.queue_request(_req("emergency_blast", {"threshold_c": 70.0}))
    assert len(router.pending_requests) == 1

    results = await router.process_tick(orch)
    assert len(results) == 1
    assert len(router.pending_requests) == 0  # queue drained

    r = results[0]
    assert r["jsonrpc"] == "2.0"
    assert r["result"]["status"] == "SUCCESS"
    assert r["result"]["nodes_affected"] == 1
    orch.pistons["SUPERNOVA"].activate.assert_awaited_once()


@pytest.mark.asyncio
async def test_predictive_sweep():
    router = _make_router()
    zone = _make_zone()
    orch = _make_orchestrator(zones=[zone])

    router.queue_request(_req("predictive_sweep"))
    results = await router.process_tick(orch)

    assert results[0]["result"]["status"] == "SUCCESS"
    orch.pistons["MICROWAVE"].activate.assert_awaited_once()


@pytest.mark.asyncio
async def test_zone_budget_override_happy_path():
    router = _make_router()
    zone = _make_zone("ZONE-A")
    orch = _make_orchestrator(zones=[zone])

    router.queue_request(_req("zone_budget_override", {"zone_id": "ZONE-A", "budget_kw": 200.0}))
    results = await router.process_tick(orch)

    r = results[0]["result"]
    assert r["status"] == "SUCCESS"
    assert r["budget_kw"] == 200.0
    assert zone.thermal_budget_kw == 200.0


@pytest.mark.asyncio
async def test_zone_budget_override_missing_zone():
    router = _make_router()
    orch = _make_orchestrator(zones=[])  # no zones registered

    router.queue_request(_req("zone_budget_override", {"zone_id": "ZONE-X", "budget_kw": 50.0}))
    results = await router.process_tick(orch)

    assert results[0]["result"]["status"] == "ERROR"


@pytest.mark.asyncio
async def test_zone_budget_override_missing_args():
    router = _make_router()
    orch = _make_orchestrator()

    router.queue_request(_req("zone_budget_override", {"zone_id": "ZONE-A"}))
    results = await router.process_tick(orch)

    assert results[0]["result"]["status"] == "ERROR"
    assert "budget_kw" in results[0]["result"]["details"]


@pytest.mark.asyncio
async def test_fusion_dispatch_unknown():
    router = _make_router()
    orch = _make_orchestrator()

    router.queue_request(_req("fusion_dispatch", {"fusion_name": "DOES_NOT_EXIST"}))
    results = await router.process_tick(orch)

    assert results[0]["result"]["status"] == "ERROR"
    orch.run_fusion_mode.assert_awaited_once_with("DOES_NOT_EXIST", context={})


@pytest.mark.asyncio
async def test_thermal_status_all_zones():
    router = _make_router()
    zones = [_make_zone("ZONE-A"), _make_zone("ZONE-B")]
    orch = _make_orchestrator(zones=zones, nodes=[])

    router.queue_request(_req("thermal_status"))
    results = await router.process_tick(orch)

    r = results[0]["result"]
    assert r["status"] == "SUCCESS"
    assert len(r["zones"]) == 2
    assert r["tick"] == 42


@pytest.mark.asyncio
async def test_thermal_status_zone_filter():
    router = _make_router()
    zones = [_make_zone("ZONE-A"), _make_zone("ZONE-B")]
    orch = _make_orchestrator(zones=zones, nodes=[])

    router.queue_request(_req("thermal_status", {"zone_id": "ZONE-A"}))
    results = await router.process_tick(orch)

    r = results[0]["result"]
    assert len(r["zones"]) == 1
    assert r["zones"][0]["zone_id"] == "ZONE-A"


@pytest.mark.asyncio
async def test_invalid_request_rejected():
    """Invalid requests get JSON-RPC error -32600, not dispatched."""
    router = _make_router()
    orch = _make_orchestrator()

    bad_req = {"jsonrpc": "2.0", "id": "bad-001", "method": "INVALID", "params": {}}
    router.queue_request(bad_req)
    results = await router.process_tick(orch)

    assert "error" in results[0]
    assert results[0]["error"]["code"] == -32600


@pytest.mark.asyncio
async def test_queue_async_drains_on_tick():
    """Requests pushed via queue_async() are processed on the next tick."""
    router = _make_router()
    orch = _make_orchestrator(zones=[_make_zone()])

    await router.queue_async(_req("thermal_status"))
    assert router._async_queue.qsize() == 1

    results = await router.process_tick(orch)
    assert len(results) == 1
    assert router._async_queue.empty()


@pytest.mark.asyncio
async def test_empty_queue_returns_empty_list():
    router = _make_router()
    orch = _make_orchestrator()
    results = await router.process_tick(orch)
    assert results == []
