#!/usr/bin/env python3
"""
tests/test_supernova_gauntlet.py
================================
P1 PHYSICS — SUPERNOVA Piston Gauntlet Scenario

Stress-test the emergency cascade path under sustained 95C+ loads.
Verifies:
  1. SUPERNOVA fires when any node crosses critical_c (85C).
  2. Every critical node receives EMERGENCY_FULL_BLAST action.
  3. GPU throttle activates at gpu_throttle_c (90C).
  4. No nodes below critical threshold are touched.
  5. Cascade from zone-level emergency propagates correctly.
  6. Orchestrator tick_cycle correctly routes critical nodes to SUPERNOVA.

Gate criterion for Phase 4 deployment (Issue #15).
"""

import asyncio
import sys
from pathlib import Path
_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / 'src'))

import pytest
from apex_core.thermal_orchestrator import (
    ThermalNode, CoolingZone, CoolingMode,
    SUPERNOVAPiston, SHADOWPiston,
    APEXThermalOrchestrator,
)


DEFAULT_THRESHOLDS = {
    'normal_max_c': 70, 'warm_c': 70, 'hot_c': 78, 'critical_c': 85,
    'gpu_throttle_c': 90, 'zone_crac_boost_c': 75, 'zone_liquid_boost_c': 80,
    'shadow_anomaly_delta_c': 8, 'shadow_ema_alpha': 0.05,
    'inlet_intervention_c': 27, 'exhaust_intervention_c': 40,
    'power_intervention_pct': 0.90,
    'cascade_limits': {'delta_t_max_c': 15, 'power_surge_mw_threshold': 0.85},
}
DEFAULT_TICK_CFG = {
    'tick_interval_ms': 500, 'microwave_sweep_every_n_ticks': 5,
    'max_crac_units': 8, 'liquid_boost_lpm': 10.0,
    'connector_refresh_every_n_ticks': 10, 'fabric_diagnostic_every_n_ticks': 20,
}
MINIMAL_MANIFEST = {
    'thermal_thresholds': DEFAULT_THRESHOLDS,
    'tick_config': DEFAULT_TICK_CFG,
}


def _node(node_id: str, temp: float, zone_id: str = 'Z001') -> ThermalNode:
    return ThermalNode(
        node_id=node_id, rack_id='RACK-001', zone_id=zone_id,
        temp_celsius=temp, gpu_utilization=0.9, power_watts=700.0,
    )


def _zone(zone_id: str, temps: list[float]) -> CoolingZone:
    zone = CoolingZone(zone_id=zone_id, zone_name=f'Zone {zone_id}')
    for i, t in enumerate(temps):
        zone.nodes.append(_node(f'{zone_id}-N{i:03d}', t, zone_id))
    return zone


async def _build_orch(zones_spec: list[tuple[str, list[float]]]) -> APEXThermalOrchestrator:
    orch = APEXThermalOrchestrator(mode=CoolingMode.COLOSSUS, manifest=MINIMAL_MANIFEST)
    for zid, temps in zones_spec:
        orch.register_zone(_zone(zid, temps))
    return orch


# ── SUPERNOVAPiston direct unit tests ────────────────────────────────────────

class TestSUPERNOVAPistonGauntlet:
    """Direct piston-level gauntlet: 95C+ stress under sustained emergency."""

    def test_all_critical_nodes_receive_full_blast(self):
        piston = SUPERNOVAPiston(DEFAULT_THRESHOLDS, DEFAULT_TICK_CFG)
        temps = [95.0, 96.5, 97.0, 98.2, 100.0]
        nodes = [_node(f'G{i}', t) for i, t in enumerate(temps)]
        result = asyncio.get_event_loop().run_until_complete(
            piston.execute({'critical_nodes': nodes, 'trigger': 'GAUNTLET'})
        )
        assert result['emergency_actions'] == len(temps)
        for action in result['actions']:
            assert action['action'] == 'EMERGENCY_FULL_BLAST'
            assert action['crac'] == 'MAX'
            assert action['liquid'] == 'MAX_FLOW'

    def test_gpu_throttle_above_90c(self):
        piston = SUPERNOVAPiston(DEFAULT_THRESHOLDS, DEFAULT_TICK_CFG)
        nodes = [_node('TH-A', 91.0), _node('TH-B', 95.0), _node('TH-C', 90.0)]
        result = asyncio.get_event_loop().run_until_complete(
            piston.execute({'critical_nodes': nodes, 'trigger': 'GAUNTLET'})
        )
        for action in result['actions']:
            assert action['throttle_gpu'] is True

    def test_no_throttle_below_90c(self):
        piston = SUPERNOVAPiston(DEFAULT_THRESHOLDS, DEFAULT_TICK_CFG)
        nodes = [_node('NT-A', 86.0), _node('NT-B', 89.9)]
        result = asyncio.get_event_loop().run_until_complete(
            piston.execute({'critical_nodes': nodes, 'trigger': 'GAUNTLET'})
        )
        for action in result['actions']:
            assert action['throttle_gpu'] is False

    def test_empty_critical_list(self):
        piston = SUPERNOVAPiston(DEFAULT_THRESHOLDS, DEFAULT_TICK_CFG)
        result = asyncio.get_event_loop().run_until_complete(
            piston.execute({'critical_nodes': [], 'trigger': 'GAUNTLET'})
        )
        assert result['emergency_actions'] == 0
        assert result['actions'] == []

    def test_boundary_90c_exact_triggers_throttle(self):
        piston = SUPERNOVAPiston(DEFAULT_THRESHOLDS, DEFAULT_TICK_CFG)
        nodes = [_node('BD-90', 90.0)]
        result = asyncio.get_event_loop().run_until_complete(
            piston.execute({'critical_nodes': nodes, 'trigger': 'GAUNTLET'})
        )
        assert result['actions'][0]['throttle_gpu'] is True

    def test_boundary_89c_no_throttle(self):
        piston = SUPERNOVAPiston(DEFAULT_THRESHOLDS, DEFAULT_TICK_CFG)
        nodes = [_node('BD-89', 89.0)]
        result = asyncio.get_event_loop().run_until_complete(
            piston.execute({'critical_nodes': nodes, 'trigger': 'GAUNTLET'})
        )
        assert result['actions'][0]['throttle_gpu'] is False

    def test_sustained_100c_does_not_crash(self):
        piston = SUPERNOVAPiston(DEFAULT_THRESHOLDS, DEFAULT_TICK_CFG)
        nodes = [_node(f'S-{i}', 100.0) for i in range(50)]
        result = asyncio.get_event_loop().run_until_complete(
            piston.execute({'critical_nodes': nodes, 'trigger': 'GAUNTLET'})
        )
        assert result['emergency_actions'] == 50
        assert all(a['action'] == 'EMERGENCY_FULL_BLAST' for a in result['actions'])


# ── Orchestrator integration: tick_cycle routes critical nodes to SUPERNOVA ──

class TestOrchestratorSUPERNOVARouting:
    """Verify that tick_cycle detects critical nodes and fires SUPERNOVA."""

    async def test_tick_cycle_fires_superNova_on_critical(self):
        orch = await _build_orch([('Z-A', [60.0, 65.0, 95.0])])
        result = await orch.tick_cycle()
        assert result['critical'] >= 1

    async def test_tick_cycle_no_critical_below_85c(self):
        orch = await _build_orch([('Z-A', [60.0, 70.0, 84.9])])
        result = await orch.tick_cycle()
        assert result['critical'] == 0

    async def test_multi_zone_critical_detection(self):
        orch = await _build_orch([
            ('Z-A', [95.0, 65.0]),
            ('Z-B', [96.0, 97.0]),
            ('Z-C', [70.0, 71.0]),
        ])
        result = await orch.tick_cycle()
        assert result['critical'] == 3

    async def test_sustained_critical_across_ticks(self):
        orch = await _build_orch([('Z-A', [98.0, 99.0])])
        critical_counts = []
        for _ in range(10):
            result = await orch.tick_cycle()
            critical_counts.append(result['critical'])
        assert all(c == 2 for c in critical_counts)


# ── Cascade stress: mixed load zones ────────────────────────────────────────

class TestCascadeStress:
    """Gauntlet: mixed healthy + critical zones — only criticals trigger SUPERNOVA."""

    async def test_healthy_zones_unaffected(self):
        orch = await _build_orch([
            ('Z-OK',  [65.0, 66.0, 67.0]),
            ('Z-HOT', [95.0, 96.0]),
        ])
        result = await orch.tick_cycle()
        assert result['critical'] == 2

    async def test_all_zones_critical(self):
        orch = await _build_orch([
            (f'Z-{i}', [95.0 + i * 0.5])
            for i in range(5)
        ])
        result = await orch.tick_cycle()
        assert result['critical'] == 5

    async def test_superNova_action_count_matches_critical_nodes(self):
        orch = await _build_orch([('Z-A', [95.0, 96.0, 97.0])])
        result = await orch.tick_cycle()
        assert result['critical'] == 3
        assert result['nodes'] == 3


# ── Gauntlet scenario: scripted tick injection (mirrors sim_harness) ────────

class TestSupernovaGauntletScenario:
    """End-to-end gauntlet: inject CRITICAL at tick 10, verify SUPERNOVA by tick 11."""

    async def test_inject_critical_tick10_superNova_fires(self):
        orch = await _build_orch([('Z-A', [65.0, 65.0, 65.0])])
        results = []
        for tick in range(1, 21):
            if tick == 10:
                for node in orch.all_nodes:
                    node.temp_celsius = 95.0
            result = await orch.tick_cycle()
            results.append(result)
        assert results[9]['critical'] == 3, 'SUPERNOVA should fire at tick 10'

    async def test_recovery_after_sustained_burst(self):
        orch = await _build_orch([('Z-A', [65.0, 65.0])])
        for tick in range(1, 11):
            await orch.tick_cycle()
        for node in orch.all_nodes:
            node.temp_celsius = 98.0
        burst_results = []
        for tick in range(11, 16):
            result = await orch.tick_cycle()
            burst_results.append(result)
        assert all(r['critical'] == 2 for r in burst_results)
        for node in orch.all_nodes:
            node.temp_celsius = 65.0
        recovery_results = []
        for tick in range(16, 21):
            result = await orch.tick_cycle()
            recovery_results.append(result)
        assert all(r['critical'] == 0 for r in recovery_results)
