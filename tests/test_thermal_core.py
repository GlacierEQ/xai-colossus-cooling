#!/usr/bin/env python3
"""
APEX Thermal Core — Unit Test Suite
GlacierEQ Sovereign Stack

Covers:
  - ThermalNode alert classification
  - CoolingZone thermal computation
  - MICROWAVEPiston zone sweeps
  - SUPERNOVAPiston emergency actions
  - SHADOWPiston anomaly detection and EMA baseline
  - GHOSTPiston micro-optimization sign/magnitude
  - APEXThermalOrchestrator tick cycle integration
  - RackCell intervention thresholds
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from apex_core.thermal_orchestrator import (
    ThermalNode, CoolingZone, CoolingMode,
    MICROWAVEPiston, SUPERNOVAPiston, SHADOWPiston, GHOSTPiston,
    APEXThermalOrchestrator
)
from cells.rack_cell import RackCell


DEFAULT_THRESHOLDS = {
    'normal_max_c': 70, 'warm_c': 70, 'hot_c': 78, 'critical_c': 85,
    'gpu_throttle_c': 90, 'zone_crac_boost_c': 75, 'zone_liquid_boost_c': 80,
    'shadow_anomaly_delta_c': 8, 'shadow_ema_alpha': 0.05,
    'inlet_intervention_c': 27, 'exhaust_intervention_c': 40,
    'power_intervention_pct': 0.90
}
DEFAULT_TICK_CFG = {
    'tick_interval_ms': 500, 'microwave_sweep_every_n_ticks': 5,
    'max_crac_units': 8, 'liquid_boost_lpm': 10.0
}
MINIMAL_MANIFEST = {
    'thermal_thresholds': DEFAULT_THRESHOLDS,
    'tick_config': DEFAULT_TICK_CFG
}


def make_node(node_id='N001', temp=65.0, zone_id='Z001') -> ThermalNode:
    return ThermalNode(
        node_id=node_id, rack_id='RACK-001', zone_id=zone_id,
        temp_celsius=temp, gpu_utilization=0.8, power_watts=700.0
    )


def make_zone(zone_id='Z001', temps=None) -> CoolingZone:
    temps = temps or [65.0, 70.0, 75.0]
    zone = CoolingZone(zone_id=zone_id, zone_name=f'Zone {zone_id}')
    zone.nodes = [make_node(f'N{i}', t, zone_id) for i, t in enumerate(temps)]
    return zone


# ── ThermalNode ──────────────────────────────────────────────────────────────

class TestThermalNode:
    def test_normal_alert(self):
        node = make_node(temp=60.0)
        assert node.classify_alert(DEFAULT_THRESHOLDS) == 0

    def test_warm_alert(self):
        node = make_node(temp=72.0)
        assert node.classify_alert(DEFAULT_THRESHOLDS) == 1

    def test_hot_alert(self):
        node = make_node(temp=80.0)
        assert node.classify_alert(DEFAULT_THRESHOLDS) == 2

    def test_critical_alert(self):
        node = make_node(temp=86.0)
        assert node.classify_alert(DEFAULT_THRESHOLDS) == 3

    def test_boundary_warm(self):
        node = make_node(temp=70.0)
        assert node.classify_alert(DEFAULT_THRESHOLDS) == 1

    def test_boundary_critical(self):
        node = make_node(temp=85.0)
        assert node.classify_alert(DEFAULT_THRESHOLDS) == 3


# ── CoolingZone ───────────────────────────────────────────────────────────────

class TestCoolingZone:
    def test_avg_temp(self):
        zone = make_zone(temps=[60.0, 70.0, 80.0])
        zone.compute_thermals(DEFAULT_THRESHOLDS)
        assert abs(zone.avg_temp - 70.0) < 0.01

    def test_peak_temp(self):
        zone = make_zone(temps=[60.0, 70.0, 80.0])
        zone.compute_thermals(DEFAULT_THRESHOLDS)
        assert zone.peak_temp == 80.0

    def test_empty_zone(self):
        zone = CoolingZone(zone_id='EMPTY', zone_name='Empty')
        zone.compute_thermals(DEFAULT_THRESHOLDS)   # Should not raise
        assert zone.avg_temp == 0.0

    def test_classifies_nodes(self):
        zone = make_zone(temps=[60.0, 86.0])
        zone.compute_thermals(DEFAULT_THRESHOLDS)
        assert zone.nodes[0].alert_level == 0
        assert zone.nodes[1].alert_level == 3


# ── MICROWAVEPiston ───────────────────────────────────────────────────────────

class TestMICROWAVEPiston:
    def test_nominal_no_action(self):
        piston = MICROWAVEPiston(DEFAULT_THRESHOLDS, DEFAULT_TICK_CFG)
        zone = make_zone(temps=[60.0, 65.0, 68.0])
        result = asyncio.get_event_loop().run_until_complete(
            piston.execute({'zones': [zone], 'trigger': 'test'})
        )
        assert result['zones_swept'] == 1
        assert result['results'][0]['action'] == 'nominal'

    def test_crac_boost_above_threshold(self):
        piston = MICROWAVEPiston(DEFAULT_THRESHOLDS, DEFAULT_TICK_CFG)
        zone = make_zone(temps=[76.0, 77.0, 76.5])
        asyncio.get_event_loop().run_until_complete(
            piston.execute({'zones': [zone], 'trigger': 'test'})
        )
        assert zone.crac_units_active == 2

    def test_liquid_boost_above_threshold(self):
        piston = MICROWAVEPiston(DEFAULT_THRESHOLDS, DEFAULT_TICK_CFG)
        zone = make_zone(temps=[82.0, 81.0, 83.0])
        asyncio.get_event_loop().run_until_complete(
            piston.execute({'zones': [zone], 'trigger': 'test'})
        )
        assert zone.liquid_cooling_flow_lpm == 10.0

    def test_max_crac_cap(self):
        piston = MICROWAVEPiston(DEFAULT_THRESHOLDS, DEFAULT_TICK_CFG)
        zone = make_zone(temps=[76.0])
        zone.crac_units_active = 7
        asyncio.get_event_loop().run_until_complete(
            piston.execute({'zones': [zone], 'trigger': 'test'})
        )
        assert zone.crac_units_active == 8  # capped at max_crac_units=8


# ── SUPERNOVAPiston ───────────────────────────────────────────────────────────

class TestSUPERNOVAPiston:
    def test_emergency_actions_generated(self):
        piston = SUPERNOVAPiston(DEFAULT_THRESHOLDS, DEFAULT_TICK_CFG)
        nodes  = [make_node('N1', 87.0), make_node('N2', 88.0)]
        result = asyncio.get_event_loop().run_until_complete(
            piston.execute({'critical_nodes': nodes, 'trigger': 'test'})
        )
        assert result['emergency_actions'] == 2
        assert all(a['action'] == 'EMERGENCY_FULL_BLAST' for a in result['actions'])

    def test_gpu_throttle_at_90c(self):
        piston = SUPERNOVAPiston(DEFAULT_THRESHOLDS, DEFAULT_TICK_CFG)
        nodes  = [make_node('N1', 91.0)]
        result = asyncio.get_event_loop().run_until_complete(
            piston.execute({'critical_nodes': nodes, 'trigger': 'test'})
        )
        assert result['actions'][0]['throttle_gpu'] is True

    def test_no_throttle_below_90c(self):
        piston = SUPERNOVAPiston(DEFAULT_THRESHOLDS, DEFAULT_TICK_CFG)
        nodes  = [make_node('N1', 86.0)]
        result = asyncio.get_event_loop().run_until_complete(
            piston.execute({'critical_nodes': nodes, 'trigger': 'test'})
        )
        assert result['actions'][0]['throttle_gpu'] is False

    def test_no_critical_nodes(self):
        piston = SUPERNOVAPiston(DEFAULT_THRESHOLDS, DEFAULT_TICK_CFG)
        result = asyncio.get_event_loop().run_until_complete(
            piston.execute({'critical_nodes': [], 'trigger': 'test'})
        )
        assert result['emergency_actions'] == 0


# ── SHADOWPiston ─────────────────────────────────────────────────────────────

class TestSHADOWPiston:
    def test_no_anomaly_at_baseline(self):
        piston = SHADOWPiston(DEFAULT_THRESHOLDS, DEFAULT_TICK_CFG)
        nodes  = [make_node('N1', 65.0)]
        result = asyncio.get_event_loop().run_until_complete(
            piston.execute({'all_nodes': nodes, 'trigger': 'test'})
        )
        assert result['anomalies'] == []

    def test_anomaly_detected_above_delta(self):
        piston = SHADOWPiston(DEFAULT_THRESHOLDS, DEFAULT_TICK_CFG)
        piston.thermal_baseline['N1'] = 65.0
        nodes = [make_node('N1', 75.0)]  # 10C above baseline
        result = asyncio.get_event_loop().run_until_complete(
            piston.execute({'all_nodes': nodes, 'trigger': 'test'})
        )
        assert len(result['anomalies']) == 1
        assert result['anomalies'][0]['node'] == 'N1'

    def test_ema_baseline_updates(self):
        piston = SHADOWPiston(DEFAULT_THRESHOLDS, DEFAULT_TICK_CFG)
        piston.thermal_baseline['N1'] = 65.0
        nodes = [make_node('N1', 67.0)]
        asyncio.get_event_loop().run_until_complete(
            piston.execute({'all_nodes': nodes, 'trigger': 'test'})
        )
        new_baseline = piston.thermal_baseline['N1']
        # EMA: 65*0.95 + 67*0.05 = 61.75 + 3.35 = 65.10
        assert abs(new_baseline - 65.10) < 0.01

    def test_just_below_anomaly_threshold(self):
        piston = SHADOWPiston(DEFAULT_THRESHOLDS, DEFAULT_TICK_CFG)
        piston.thermal_baseline['N1'] = 65.0
        nodes = [make_node('N1', 72.9)]  # delta=7.9, threshold=8
        result = asyncio.get_event_loop().run_until_complete(
            piston.execute({'all_nodes': nodes, 'trigger': 'test'})
        )
        assert result['anomalies'] == []


# ── GHOSTPiston ───────────────────────────────────────────────────────────────

class TestGHOSTPiston:
    def test_positive_delta_above_65c(self):
        piston = GHOSTPiston(DEFAULT_THRESHOLDS, DEFAULT_TICK_CFG)
        zone = make_zone(temps=[70.0, 70.0])
        zone.compute_thermals(DEFAULT_THRESHOLDS)
        result = asyncio.get_event_loop().run_until_complete(
            piston.execute({'zones': [zone], 'trigger': 'test'})
        )
        assert result['ops'][0]['micro_flow_delta'] > 0

    def test_negative_delta_below_65c(self):
        piston = GHOSTPiston(DEFAULT_THRESHOLDS, DEFAULT_TICK_CFG)
        zone = make_zone(temps=[60.0, 60.0])
        zone.compute_thermals(DEFAULT_THRESHOLDS)
        result = asyncio.get_event_loop().run_until_complete(
            piston.execute({'zones': [zone], 'trigger': 'test'})
        )
        assert result['ops'][0]['micro_flow_delta'] < 0

    def test_trace_none(self):
        piston = GHOSTPiston(DEFAULT_THRESHOLDS, DEFAULT_TICK_CFG)
        zone = make_zone(temps=[65.0])
        zone.compute_thermals(DEFAULT_THRESHOLDS)
        result = asyncio.get_event_loop().run_until_complete(
            piston.execute({'zones': [zone], 'trigger': 'test'})
        )
        assert result['ops'][0]['trace'] == 'none'


# ── RackCell ──────────────────────────────────────────────────────────────────

class TestRackCell:
    def make_rack(self, inlet=22.0, exhaust=35.0, power_kw=50.0) -> RackCell:
        return RackCell(
            rack_id='RACK-001', zone_id='Z001', row=0, position=0,
            inlet_temp_c=inlet, exhaust_temp_c=exhaust,
            power_draw_kw=power_kw, power_cap_kw=80.0
        )

    def test_no_intervention_nominal(self):
        rack = self.make_rack(inlet=22.0, exhaust=35.0, power_kw=50.0)
        assert rack.needs_cooling_intervention() is False

    def test_intervention_on_high_exhaust(self):
        rack = self.make_rack(exhaust=41.0)
        assert rack.needs_cooling_intervention() is True

    def test_intervention_on_high_inlet(self):
        rack = self.make_rack(inlet=28.0)
        assert rack.needs_cooling_intervention() is True

    def test_intervention_on_power_cap(self):
        rack = self.make_rack(power_kw=73.0)  # 73/80 = 91.25% > 90%
        assert rack.needs_cooling_intervention() is True

    def test_delta_t_computed(self):
        rack = self.make_rack(inlet=22.0, exhaust=37.0)
        assert abs(rack.delta_t - 15.0) < 0.01


# ── Orchestrator integration ──────────────────────────────────────────────────

class TestOrchestratorIntegration:
    def build_orch(self, temps=None) -> APEXThermalOrchestrator:
        orch = APEXThermalOrchestrator(
            mode=CoolingMode.COLOSSUS,
            manifest=MINIMAL_MANIFEST
        )
        zone = CoolingZone(zone_id='Z001', zone_name='Test Zone')
        for i, t in enumerate(temps or [60.0, 65.0, 70.0]):
            zone.nodes.append(make_node(f'N{i}', t))
        orch.register_zone(zone)
        return orch

    def test_tick_returns_valid_structure(self):
        orch = self.build_orch()
        result = asyncio.get_event_loop().run_until_complete(orch.tick_cycle())
        assert 'tick' in result
        assert 'zones' in result
        assert 'nodes' in result
        assert result['zones'] == 1
        assert result['nodes'] == 3

    def test_critical_count_correct(self):
        orch = self.build_orch(temps=[86.0, 87.0, 60.0])
        result = asyncio.get_event_loop().run_until_complete(orch.tick_cycle())
        assert result['critical'] == 2

    def test_no_critical_below_threshold(self):
        orch = self.build_orch(temps=[60.0, 70.0, 80.0])
        result = asyncio.get_event_loop().run_until_complete(orch.tick_cycle())
        assert result['critical'] == 0

    def test_multiple_ticks_increment(self):
        orch = self.build_orch()
        asyncio.get_event_loop().run_until_complete(orch.tick_cycle())
        asyncio.get_event_loop().run_until_complete(orch.tick_cycle())
        assert orch.tick == 2
