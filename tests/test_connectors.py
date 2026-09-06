"""
tests/test_connectors.py
Unit tests for connectors/nanosphere_ingest.py and connectors/power_state_bridge.py.
Run: pytest tests/test_connectors.py -v
"""

import json
import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

CIRCUIT_MANIFEST = {
    "schema_version": "1.0",
    "exported_at": "2026-05-28T00:00:00Z",
    "circuits": [
        {
            "circuit_id": "CIRCUIT-01",
            "nanoparticle": "Al2O3",
            "volume_fraction_pct": 2.5,
            "effective_conductivity_w_mk": 0.72,
            "degradation_pct": 5.0,
            "status": "active",
            "replacement_due": False,
        },
        {
            "circuit_id": "CIRCUIT-02",
            "nanoparticle": "TiO2",
            "volume_fraction_pct": 3.0,
            "effective_conductivity_w_mk": 0.75,
            "degradation_pct": 17.0,
            "status": "degraded",
            "replacement_due": True,
        },
        {
            "circuit_id": "CIRCUIT-03",
            "nanoparticle": "CuO",
            "volume_fraction_pct": 1.5,
            "effective_conductivity_w_mk": 0.68,
            "degradation_pct": 3.0,
            "status": "active",
            "replacement_due": False,
        },
        {
            "circuit_id": "CIRCUIT-05",
            "nanoparticle": "graphene",
            "volume_fraction_pct": 0.5,
            "effective_conductivity_w_mk": 0.90,
            "degradation_pct": 1.0,
            "status": "active",
            "replacement_due": False,
        },
    ],
}

POWER_STATE_SNAPSHOT = {
    "snapshot_id": "snap-001",
    "timestamp": "2026-05-28T00:00:00Z",
    "total_draw_kw": 950000.0,
    "pue": 1.38,
    "megapack_net_kw": 45000.0,
    "grid_price_usd_per_mwh": 52.10,
    "zones": [
        {
            "zone_id": "ZONE-A",
            "draw_kw": 240000,
            "compute_kw": 210000,
            "cooling_kw": 30000,
            "rack_count": 512,
            "avg_inlet_temp_c": 20.5,
            "avg_outlet_temp_c": 38.2,
        },
        {
            "zone_id": "ZONE-B",
            "draw_kw": 235000,
            "compute_kw": 205000,
            "cooling_kw": 30000,
            "rack_count": 512,
            "avg_inlet_temp_c": 21.0,
            "avg_outlet_temp_c": 39.5,
        },
        {
            "zone_id": "ZONE-C",
            "draw_kw": 245000,
            "compute_kw": 215000,
            "cooling_kw": 30000,
            "rack_count": 512,
            "avg_inlet_temp_c": 20.0,
            "avg_outlet_temp_c": 41.1,
        },
        {
            "zone_id": "ZONE-D",
            "draw_kw": 230000,
            "compute_kw": 200000,
            "cooling_kw": 30000,
            "rack_count": 512,
            "avg_inlet_temp_c": 20.3,
            "avg_outlet_temp_c": 37.8,
        },
    ],
}


# ---------------------------------------------------------------------------
# NanosphereIngest tests
# ---------------------------------------------------------------------------


class TestNanosphereIngest:
    def _make_ingest(self, tmp_path):
        from connectors.nanosphere_ingest import NanosphereIngest

        manifest_file = tmp_path / "circuit_manifest.json"
        manifest_file.write_text(json.dumps(CIRCUIT_MANIFEST))
        alert_file = tmp_path / "alerts.ndjson"
        return NanosphereIngest(
            manifest_path=str(manifest_file), alert_log_path=str(alert_file)
        ), alert_file

    def test_load_returns_all_circuits(self, tmp_path):
        ingest, _ = self._make_ingest(tmp_path)
        states = ingest.load()
        assert len(states) == 4

    def test_zone_mapping(self, tmp_path):
        ingest, _ = self._make_ingest(tmp_path)
        ingest.load()
        zones = ingest.by_zone()
        assert "ZONE-A" in zones
        assert len(zones["ZONE-A"]) == 2  # CIRCUIT-01, CIRCUIT-02
        assert "ZONE-B" in zones

    def test_replacement_alert_emitted(self, tmp_path):
        ingest, alert_file = self._make_ingest(tmp_path)
        ingest.load()
        assert alert_file.exists(), "Alert file should be created for degraded circuit"
        lines = alert_file.read_text().strip().split("\n")
        alerts = [json.loads(l) for l in lines if l]
        assert any(a["circuit_id"] == "CIRCUIT-02" for a in alerts)

    def test_no_alert_for_healthy_circuit(self, tmp_path):
        ingest, alert_file = self._make_ingest(tmp_path)
        ingest.load()
        lines = (
            alert_file.read_text().strip().split("\n") if alert_file.exists() else []
        )
        alerts = [json.loads(l) for l in lines if l]
        assert not any(a.get("circuit_id") == "CIRCUIT-01" for a in alerts)

    def test_conductivity_factor_above_pure_water(self, tmp_path):
        ingest, _ = self._make_ingest(tmp_path)
        ingest.load()
        mean_cond = ingest.mean_conductivity_by_zone()
        # All test circuits have conductivity > 0.613 (pure water)
        for zone, k in mean_cond.items():
            assert k > 0.613, f"{zone} conductivity {k} <= pure water 0.613"

    def test_worst_degradation_by_zone(self, tmp_path):
        ingest, _ = self._make_ingest(tmp_path)
        ingest.load()
        worst = ingest.worst_degradation_by_zone()
        # ZONE-A worst should be CIRCUIT-02's 17%
        assert worst["ZONE-A"] == pytest.approx(17.0)

    def test_missing_manifest_returns_empty(self, tmp_path):
        from connectors.nanosphere_ingest import NanosphereIngest

        ingest = NanosphereIngest(manifest_path=str(tmp_path / "nonexistent.json"))
        result = ingest.load()
        assert result == {}


# ---------------------------------------------------------------------------
# PowerStateBridge tests
# ---------------------------------------------------------------------------


class TestPowerStateBridge:
    def _make_bridge(self):
        from connectors.power_state_bridge import PowerStateBridge

        return PowerStateBridge()

    def test_load_from_dict_all_zones(self):
        bridge = self._make_bridge()
        budgets = bridge.load_from_dict(POWER_STATE_SNAPSHOT)
        assert set(budgets.keys()) == {"ZONE-A", "ZONE-B", "ZONE-C", "ZONE-D"}

    def test_zone_thermal_budget_kw(self):
        bridge = self._make_bridge()
        budgets = bridge.load_from_dict(POWER_STATE_SNAPSHOT)
        assert budgets["ZONE-A"].total_draw_kw == 240000

    def test_delta_t_calculation(self):
        bridge = self._make_bridge()
        budgets = bridge.load_from_dict(POWER_STATE_SNAPSHOT)
        dt = budgets["ZONE-C"].delta_t
        assert dt == pytest.approx(41.1 - 20.0)

    def test_hottest_zone(self):
        bridge = self._make_bridge()
        bridge.load_from_dict(POWER_STATE_SNAPSHOT)
        assert bridge.hottest_zone() == "ZONE-C"  # outlet 41.1

    def test_pue_warning_logged(self, caplog):
        import logging

        bridge = self._make_bridge()
        high_pue_snapshot = {**POWER_STATE_SNAPSHOT, "pue": 1.60}
        with caplog.at_level(logging.WARNING, logger="connectors.power_state_bridge"):
            bridge.load_from_dict(high_pue_snapshot)
        assert any("PUE" in r.message for r in caplog.records)

    def test_unknown_zone_skipped(self):
        bridge = self._make_bridge()
        bad_snapshot = {
            **POWER_STATE_SNAPSHOT,
            "zones": POWER_STATE_SNAPSHOT["zones"]
            + [{"zone_id": "ZONE-Z", "draw_kw": 100, "rack_count": 1}],
        }
        budgets = bridge.load_from_dict(bad_snapshot)
        assert "ZONE-Z" not in budgets

    def test_kw_per_rack(self):
        bridge = self._make_bridge()
        budgets = bridge.load_from_dict(POWER_STATE_SNAPSHOT)
        # ZONE-A: 240000 kW / 512 racks = 468.75 kW/rack
        assert budgets["ZONE-A"].kw_per_rack == pytest.approx(240000 / 512)


# ---------------------------------------------------------------------------
# MCP Router tests
# ---------------------------------------------------------------------------


class TestMCPRouter:
    @pytest.mark.asyncio
    async def test_zone_snapshot_offline(self):
        from mastermind_fusion.mcp_router import (
            MCPRouter,
            MCPRequest,
            RequestType,
            ResponseStatus,
        )

        router = MCPRouter(orchestrator=None)
        req = MCPRequest(request_type=RequestType.ZONE_SNAPSHOT, source_agent="test")
        resp = await router.dispatch(req)
        assert resp.status == ResponseStatus.OK
        assert resp.data.get("status") == "offline"

    @pytest.mark.asyncio
    async def test_unknown_request_type_returns_error(self):
        from mastermind_fusion.mcp_router import MCPRouter, MCPRequest, ResponseStatus

        router = MCPRouter(orchestrator=None)
        req = MCPRequest.__new__(MCPRequest)
        object.__setattr__(req, "request_type", "INVALID_TYPE")
        object.__setattr__(req, "request_id", "test-id")
        object.__setattr__(req, "source_agent", "test")
        object.__setattr__(req, "timestamp", "2026-01-01T00:00:00")
        object.__setattr__(req, "zone_id", None)
        object.__setattr__(req, "piston_name", None)
        object.__setattr__(req, "horizon_ticks", 12)
        object.__setattr__(req, "severity", "INFO")
        object.__setattr__(req, "message", None)
        object.__setattr__(req, "payload", {})
        resp = await router.dispatch(req)
        assert resp.status == ResponseStatus.ERROR

    @pytest.mark.asyncio
    async def test_emergency_broadcast_fans_out(self, tmp_path, monkeypatch):
        from mastermind_fusion import mcp_router as mcp_mod

        monkeypatch.setattr(mcp_mod, "ASPEN_LOG_PATH", tmp_path / "aspen.ndjson")
        from mastermind_fusion.mcp_router import (
            MCPRouter,
            MCPRequest,
            RequestType,
            ResponseStatus,
        )

        router = MCPRouter()
        req = MCPRequest(
            request_type=RequestType.EMERGENCY,
            source_agent="test",
            severity="CRITICAL",
            message="THERMAL RUNAWAY ZONE-C",
            zone_id="ZONE-C",
        )
        resp = await router.dispatch(req)
        assert resp.status == ResponseStatus.EMITTED
        assert resp.data["fanned_out"] is True
        log_path = tmp_path / "aspen.ndjson"
        assert log_path.exists()
