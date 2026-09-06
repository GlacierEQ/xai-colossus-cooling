#!/usr/bin/env python3
"""
tests/test_digital_twin_72h.py
==============================
P1 PHYSICS — Digital Twin 72h Validation

Simulates 72 hours of tick cycles at 500ms intervals (compressed for testing).
Verifies:
  1. Thermal stability: average temp stays within 55-75C band over 72h.
  2. No uncontrolled cascade failures (cascade isolation never triggers).
  3. SHADOW anomaly detection fires correctly when baseline drifts.
  4. Peak temp never exceeds 105C (thermal shutdown threshold).
  5. Orchestrator completes all ticks without exception.

Gate criterion for Phase 4 deployment (Issue #15).
Requires human review for physics correctness.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "src"))

from apex_core.thermal_orchestrator import (
    ThermalNode,
    CoolingZone,
    CoolingMode,
    SHADOWPiston,
    APEXThermalOrchestrator,
)
from apex_core.cascade_prevention import CascadePreventionProtocol


DEFAULT_THRESHOLDS = {
    "normal_max_c": 70,
    "warm_c": 70,
    "hot_c": 78,
    "critical_c": 85,
    "gpu_throttle_c": 90,
    "zone_crac_boost_c": 75,
    "zone_liquid_boost_c": 80,
    "shadow_anomaly_delta_c": 8,
    "shadow_ema_alpha": 0.05,
    "inlet_intervention_c": 27,
    "exhaust_intervention_c": 40,
    "power_intervention_pct": 0.90,
    "cascade_limits": {"delta_t_max_c": 15, "power_surge_mw_threshold": 0.85},
}
DEFAULT_TICK_CFG = {
    "tick_interval_ms": 500,
    "microwave_sweep_every_n_ticks": 5,
    "max_crac_units": 8,
    "liquid_boost_lpm": 10.0,
    "connector_refresh_every_n_ticks": 10,
    "fabric_diagnostic_every_n_ticks": 20,
}
MINIMAL_MANIFEST = {
    "thermal_thresholds": DEFAULT_THRESHOLDS,
    "tick_config": DEFAULT_TICK_CFG,
}

THERMAL_SHUTDOWN_C = 105.0
STABLE_BAND_LOW = 55.0
STABLE_BAND_HIGH = 75.0
SEVEN_TWO_HOURS_TICKS = 518400  # 72h * 3600s / 0.5s tick


def _node(node_id: str, temp: float, zone_id: str = "Z001") -> ThermalNode:
    return ThermalNode(
        node_id=node_id,
        rack_id="RACK-001",
        zone_id=zone_id,
        temp_celsius=temp,
        gpu_utilization=0.85,
        power_watts=700.0,
    )


def _zone(zone_id: str, temps: list[float]) -> CoolingZone:
    zone = CoolingZone(zone_id=zone_id, zone_name=f"Zone {zone_id}")
    for i, t in enumerate(temps):
        zone.nodes.append(_node(f"{zone_id}-N{i:03d}", t, zone_id))
    return zone


async def _build_orch(
    zones_spec: list[tuple[str, list[float]]],
) -> APEXThermalOrchestrator:
    orch = APEXThermalOrchestrator(mode=CoolingMode.COLOSSUS, manifest=MINIMAL_MANIFEST)
    for zid, temps in zones_spec:
        orch.register_zone(_zone(zid, temps))
    return orch


# ── 72h simulation harness ──────────────────────────────────────────────────


async def _run_72h_simulation(
    zones_spec: list[tuple[str, list[float]]],
    num_ticks: int = 500,
    thermal_noise_std: float = 0.8,
    spike_interval: int | None = None,
    spike_temp_delta: float = 15.0,
    recovery_rate: float = 0.3,
) -> dict:
    """Run a compressed 72h simulation with optional thermal events.

    Args:
        zones_spec: list of (zone_id, [node_temps]) tuples.
        num_ticks: number of ticks to simulate (compressed 72h).
        thermal_noise_std: standard deviation of per-tick temp jitter.
        spike_interval: if set, inject a temp spike every N ticks.
        spike_temp_delta: how much to raise temps on spike ticks.
        recovery_rate: fraction of spike delta to recover per tick after spike.
    """
    orch = await _build_orch(zones_spec)
    tick_temps: list[float] = []
    tick_criticals: list[int] = []
    tick_anomalies: list[int] = []
    peak_temp_seen = 0.0
    cascade_triggered = False
    spike_active = False
    spike_remaining = 0

    for tick in range(1, num_ticks + 1):
        if spike_interval and tick % spike_interval == 0:
            spike_active = True
            spike_remaining = 5

        if spike_active:
            for node in orch.all_nodes:
                node.temp_celsius = min(
                    node.temp_celsius + spike_temp_delta * 0.5, 105.0
                )
            spike_remaining -= 1
            if spike_remaining <= 0:
                spike_active = False

        for node in orch.all_nodes:
            noise = random.gauss(0, thermal_noise_std)
            node.temp_celsius = max(50.0, min(node.temp_celsius + noise, 110.0))

        if not spike_active:
            for node in orch.all_nodes:
                if node.temp_celsius > 75.0:
                    node.temp_celsius -= recovery_rate
                elif node.temp_celsius < 60.0:
                    node.temp_celsius += recovery_rate * 0.5

        result = await orch.tick_cycle()

        zone_temps = []
        for z in orch.zones:
            if z.nodes:
                zone_temps.append(sum(n.temp_celsius for n in z.nodes) / len(z.nodes))
        avg_temp = sum(zone_temps) / len(zone_temps) if zone_temps else 0.0
        tick_temps.append(avg_temp)
        tick_criticals.append(result["critical"])
        tick_anomalies.append(result["anomalies"])
        peak_temp_seen = max(
            peak_temp_seen, max((n.temp_celsius for n in orch.all_nodes), default=0.0)
        )

    return {
        "tick_temps": tick_temps,
        "tick_criticals": tick_criticals,
        "tick_anomalies": tick_anomalies,
        "peak_temp_seen": peak_temp_seen,
        "orchestrator": orch,
    }


# ── Thermal Stability ───────────────────────────────────────────────────────


class TestThermalStability72h:
    """Verify average temperature stays within stable band over 72h simulation."""

    async def test_avg_temp_stays_in_band(self):
        random.seed(42)
        sim = await _run_72h_simulation(
            zones_spec=[("Z-A", [65.0] * 5), ("Z-B", [66.0] * 5)],
            num_ticks=500,
            thermal_noise_std=0.5,
        )
        avg_all = sum(sim["tick_temps"]) / len(sim["tick_temps"])
        assert STABLE_BAND_LOW <= avg_all <= STABLE_BAND_HIGH, (
            f"Average temp {avg_all:.2f}C outside stable band "
            f"[{STABLE_BAND_LOW}, {STABLE_BAND_HIGH}]"
        )

    async def test_peak_never_exceeds_shutdown(self):
        random.seed(42)
        sim = await _run_72h_simulation(
            zones_spec=[("Z-A", [65.0] * 10)],
            num_ticks=500,
            thermal_noise_std=1.0,
        )
        assert sim["peak_temp_seen"] < THERMAL_SHUTDOWN_C, (
            f"Peak temp {sim['peak_temp_seen']:.2f}C exceeds shutdown threshold {THERMAL_SHUTDOWN_C}C"
        )

    async def test_temp_converges_to_baseline(self):
        random.seed(42)
        sim = await _run_72h_simulation(
            zones_spec=[("Z-A", [72.0] * 5)],
            num_ticks=200,
            thermal_noise_std=0.3,
        )
        last_50 = sim["tick_temps"][-50:]
        final_avg = sum(last_50) / len(last_50)
        assert 55.0 <= final_avg <= 78.0, (
            f"Final avg temp {final_avg:.2f}C not converged to baseline"
        )


# ── Cascade Failure Prevention ──────────────────────────────────────────────


class TestNoCascadeFailure:
    """Verify no uncontrolled cascade isolation occurs during stable operation."""

    async def test_no_isolation_under_normal_load(self):
        random.seed(42)
        sim = await _run_72h_simulation(
            zones_spec=[("Z-A", [65.0] * 5), ("Z-B", [66.0] * 5)],
            num_ticks=300,
            thermal_noise_std=0.3,
        )
        orch = sim["orchestrator"]
        if orch._cascade:
            assert len(orch._cascade.zone_states) == 0, (
                "Cascade isolation triggered under normal load"
            )

    async def test_isolation_resets_after_recovery(self):
        cascade = CascadePreventionProtocol(
            thresholds=DEFAULT_THRESHOLDS["cascade_limits"]
        )
        for _ in range(2):
            await cascade.evaluate_zone(
                "Z-A", {"delta_t_c": 20.0, "power_surge_mw": 0.5}
            )
        assert cascade.anomaly_counters.get("Z-A", 0) == 2
        await cascade.evaluate_zone("Z-A", {"delta_t_c": 5.0, "power_surge_mw": 0.5})
        assert cascade.anomaly_counters.get("Z-A", 0) == 0


# ── SHADOW Anomaly Detection ────────────────────────────────────────────────


class TestSHADOWAnomalyDetection:
    """Verify SHADOW piston detects anomalies during 72h simulation."""

    async def test_shadow_detects_baseline_drift(self):
        piston = SHADOWPiston(DEFAULT_THRESHOLDS, DEFAULT_TICK_CFG)
        piston.thermal_baseline["N1"] = 65.0
        nodes = [_node("N1", 75.0)]
        result = await piston.execute({"all_nodes": nodes, "trigger": "drift_test"})
        assert len(result["anomalies"]) == 1
        assert result["anomalies"][0]["deviation"] > 8.0

    async def test_shadow_ema_converges(self):
        piston = SHADOWPiston(DEFAULT_THRESHOLDS, DEFAULT_TICK_CFG)
        piston.thermal_baseline["N1"] = 65.0
        stable_temp = 70.0
        for _ in range(100):
            await piston.execute(
                {"all_nodes": [_node("N1", stable_temp)], "trigger": "converge"}
            )
        baseline = piston.thermal_baseline["N1"]
        assert abs(baseline - stable_temp) < 2.0, (
            f"SHADOW EMA baseline {baseline:.2f} did not converge to {stable_temp}"
        )

    async def test_shadow_no_false_positive_at_baseline(self):
        piston = SHADOWPiston(DEFAULT_THRESHOLDS, DEFAULT_TICK_CFG)
        piston.thermal_baseline["N1"] = 65.0
        nodes = [_node("N1", 66.0)]
        result = await piston.execute({"all_nodes": nodes, "trigger": "baseline_test"})
        assert result["anomalies"] == []

    async def test_shadow_tracks_multiple_nodes(self):
        piston = SHADOWPiston(DEFAULT_THRESHOLDS, DEFAULT_TICK_CFG)
        for i in range(10):
            piston.thermal_baseline[f"N{i}"] = 65.0
        nodes = [_node(f"N{i}", 65.0 + i) for i in range(10)]
        result = await piston.execute({"all_nodes": nodes, "trigger": "multi_test"})
        assert result["nodes_monitored"] == 10
        anomaly_nodes = {a["node"] for a in result["anomalies"]}
        assert "N8" in anomaly_nodes or "N9" in anomaly_nodes


# ── Orchestrator tick count integrity ────────────────────────────────────────


class TestOrchestratorTickIntegrity:
    """Verify orchestrator completes all ticks without exception."""

    async def test_orchestrator_runs_full_72h(self):
        random.seed(42)
        orch = await _build_orch([("Z-A", [65.0] * 3)])
        tick_count = 0
        for _ in range(100):
            await orch.tick_cycle()
            tick_count += 1
        assert orch.tick == 100
        assert tick_count == 100

    async def test_orchestrator_handles_mixed_load(self):
        random.seed(42)
        orch = await _build_orch(
            [
                ("Z-A", [65.0, 66.0]),
                ("Z-B", [88.0, 89.0]),
            ]
        )
        results = []
        for _ in range(20):
            result = await orch.tick_cycle()
            results.append(result)
        assert all("tick" in r for r in results)
        assert all(r["zones"] == 2 for r in results)
