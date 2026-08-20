"""Deterministic full-system fixture for Cooling–Servers–Security composition."""

from __future__ import annotations

from pathlib import Path

import pytest

from apex_core.thermal_orchestrator import CoolingZone, ThermalNode
from compose import compose


ROOT = Path(__file__).resolve().parents[1]
WAVE_ROOT = ROOT.parent
SERVERS_ROOT = WAVE_ROOT / "xai-colossus-servers"
SECURITY_ROOT = WAVE_ROOT / "xai-colossus-security"

FIXTURE_REVISIONS = {
    "cooling": "8a8842b0d02a88d9bec880d96757fc5e420a7f02",
    "servers": "6f23efc0bf3fa39aa7f7c0668682ca4efae53db2",
    "security": "dd5e9c010aa26eb4662bcba35b99e0c16d395625",
}

FIXTURE_MANIFEST = {
    "version": "1.2.0-COLOSSUS",
    "rack_count": 2,
    "rack_capacity_kw": 10.0,
    "thermal_thresholds": {
        "critical_c": 85,
        "gpu_throttle_c": 90,
        "zone_crac_boost_c": 75,
        "zone_liquid_boost_c": 80,
        "shadow_anomaly_delta_c": 8,
        "shadow_ema_alpha": 0.05,
        "cascade_limits": {"delta_t_max_c": 15, "power_surge_mw_threshold": 0.85},
    },
    "tick_config": {
        "connector_refresh_every_n_ticks": 99,
        "fabric_diagnostic_every_n_ticks": 1,
        "microwave_sweep_every_n_ticks": 99,
        "max_crac_units": 8,
        "liquid_boost_lpm": 10.0,
    },
    "fusion_modes": [],
}


def _fixture_zone() -> CoolingZone:
    zone = CoolingZone(zone_id="ZONE-A", zone_name="Synthetic Composition Zone")
    zone.nodes = [
        ThermalNode(
            node_id="NODE-A1",
            rack_id="RACK-001",
            zone_id="ZONE-A",
            temp_celsius=82.0,
            gpu_utilization=0.90,
            power_watts=6_000.0,
        ),
        ThermalNode(
            node_id="NODE-A2",
            rack_id="RACK-002",
            zone_id="ZONE-A",
            temp_celsius=68.0,
            gpu_utilization=0.40,
            power_watts=3_000.0,
        ),
    ]
    return zone


@pytest.mark.asyncio
async def test_full_versioned_composition_receipt(tmp_path: Path) -> None:
    receipt = await compose(
        composition_id="CSS-COMPOSITION-FIXTURE-001",
        component_revisions=FIXTURE_REVISIONS,
        servers_checkout=SERVERS_ROOT,
        security_checkout=SECURITY_ROOT,
        manifest=FIXTURE_MANIFEST,
        zones=[_fixture_zone()],
        traffic_patterns=[
            {
                "node_id": "NODE-A1",
                "zone_id": "ZONE-A",
                "entropy": 0.94,
                "suspicious_activity": True,
            },
            {
                "node_id": "NODE-A2",
                "zone_id": "ZONE-A",
                "entropy": 0.22,
            },
        ],
        router_requests=[
            {
                "request_type": "request_zone_snapshot",
                "request_id": "550e8400-e29b-41d4-a716-446655440001",
                "source_agent": "full-composition-fixture",
                "severity": "INFO",
                "timestamp": "2026-08-20T00:00:00Z",
            }
        ],
        audit_log_path=tmp_path / "composition_audit.ndjson",
    )

    assert receipt["composition_id"] == "CSS-COMPOSITION-FIXTURE-001"
    assert receipt["component_revisions"] == FIXTURE_REVISIONS
    assert receipt["thermal"]["tick"] == {
        "tick": 1,
        "zones": 1,
        "nodes": 2,
        "critical": 0,
        "anomalies": 1,
    }
    assert receipt["servers"]["placement"]["ok"] is True
    assert receipt["servers"]["placement"]["rack_usage"]["RACK-001"]["used_kw"] == 6.0
    assert receipt["servers"]["diagnostic"]["status"] == "DECLARED_CAPACITY_CHECK"
    assert receipt["servers"]["diagnostic"]["placement_ok"] is True
    assert receipt["security"]["active_threats"] == 1
    assert receipt["security"]["declared_suspicious_nodes"] == ["NODE-A1"]
    assert receipt["security"]["external_actions_executed"] == 0
    assert receipt["router"]["response_count"] == 1
    assert receipt["router"]["responses"][0]["result"]["status"] == "SUCCESS"
    assert receipt["router"]["responses"][0]["result"]["total_nodes"] == 2
    assert [event["event"] for event in receipt["audit"]["events"]] == [
        "MCP_DISPATCH",
        "COMPOSITION_COMPLETED",
    ]
    assert receipt["audit"]["overflow_count"] == 0
    assert receipt["limits"] == {
        "external_actions_executed": 0,
        "security_incidents_inferred_from_entropy": 0,
        "live_infrastructure_discovery": False,
    }
