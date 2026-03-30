import pytest
import asyncio
from thermal_orchestrator import ThermalNode, CoolingZone, CoolingMode, CORETHINKPiston

def test_compute_thermals_empty():
    zone = CoolingZone(zone_id="ZONE-EMPTY", zone_name="Empty Zone")
    zone.compute_thermals()
    assert zone.avg_temp == 0.0
    assert zone.peak_temp == 0.0

def test_compute_thermals_single_node():
    node = ThermalNode(
        node_id="NODE-1", rack_id="RACK-1", zone_id="ZONE-1",
        temp_celsius=75.0, gpu_utilization=0.5, power_watts=500.0
    )
    zone = CoolingZone(zone_id="ZONE-1", zone_name="Single Node Zone", nodes=[node])
    zone.compute_thermals()
    assert zone.avg_temp == 75.0
    assert zone.peak_temp == 75.0
    assert node.alert_level == 1  # 75 >= 70

def test_compute_thermals_multiple_nodes():
    nodes = [
        ThermalNode(node_id="N1", rack_id="R1", zone_id="Z1", temp_celsius=60.0, gpu_utilization=0.4, power_watts=400.0),
        ThermalNode(node_id="N2", rack_id="R1", zone_id="Z1", temp_celsius=80.0, gpu_utilization=0.6, power_watts=600.0),
    ]
    zone = CoolingZone(zone_id="Z1", zone_name="Multi Node Zone", nodes=nodes)
    zone.compute_thermals()
    assert zone.avg_temp == 70.0  # (60 + 80) / 2
    assert zone.peak_temp == 80.0
    assert nodes[0].alert_level == 0  # 60 < 70
    assert nodes[1].alert_level == 2  # 80 >= 78

def test_compute_thermals_alerts():
    # Thresholds: 70 -> 1, 78 -> 2, 85 -> 3
    test_cases = [
        (65.0, 0),
        (70.0, 1),
        (75.0, 1),
        (78.0, 2),
        (82.0, 2),
        (85.0, 3),
        (90.0, 3),
    ]
    for temp, expected_alert in test_cases:
        node = ThermalNode(
            node_id=f"N-{temp}", rack_id="R1", zone_id="Z1",
            temp_celsius=temp, gpu_utilization=0.5, power_watts=500.0
        )
        zone = CoolingZone(zone_id="Z1", zone_name="Alert Test Zone", nodes=[node])
        zone.compute_thermals()
        assert node.alert_level == expected_alert, f"Failed for temp {temp}"

def test_compute_thermals_invalid_readings():
    nodes = [
        ThermalNode(node_id="N1", rack_id="R1", zone_id="Z1", temp_celsius=60.0, gpu_utilization=0.4, power_watts=400.0),
        ThermalNode(node_id="N2", rack_id="R1", zone_id="Z1", temp_celsius=200.0, gpu_utilization=0.6, power_watts=600.0), # Invalid > 150
        ThermalNode(node_id="N3", rack_id="R1", zone_id="Z1", temp_celsius=-100.0, gpu_utilization=0.6, power_watts=600.0), # Invalid < -50
    ]
    zone = CoolingZone(zone_id="Z1", zone_name="Invalid Readings Zone", nodes=nodes)
    zone.compute_thermals()
    assert zone.avg_temp == 60.0  # Only N1 is valid
    assert zone.peak_temp == 60.0
    assert nodes[0].alert_level == 0
    assert nodes[1].alert_level == 3  # Still classified even if invalid for zone computation
    assert nodes[2].alert_level == 0

def test_compute_thermals_all_invalid():
    # Setup zone with stale data
    nodes = [
        ThermalNode(node_id="N1", rack_id="R1", zone_id="Z1", temp_celsius=200.0, gpu_utilization=0.4, power_watts=400.0),
    ]
    zone = CoolingZone(zone_id="Z1", zone_name="All Invalid Zone", nodes=nodes, avg_temp=75.0, peak_temp=75.0)
    zone.compute_thermals()
    assert zone.avg_temp == 0.0 # Should be reset
    assert zone.peak_temp == 0.0

def test_core_think_forecast():
    async def run():
        piston = CORETHINKPiston()
        nodes = [
            ThermalNode(node_id="N1", rack_id="R1", zone_id="Z1", temp_celsius=65.0, gpu_utilization=0.5, power_watts=500.0),
            ThermalNode(node_id="N2", rack_id="R1", zone_id="Z1", temp_celsius=75.0, gpu_utilization=0.5, power_watts=500.0),
        ]
        zone = CoolingZone(zone_id="Z1", zone_name="Z1", nodes=nodes)

        context = {'zones': [zone]}
        result = await piston.execute(context)

        forecast = result['forecast']['Z1']
        # Mean = 70. Entropy = ((65-70)^2 + (75-70)^2)/2 = (25+25)/2 = 25.0
        assert forecast['entropy'] == 25.0
        assert forecast['status'] == 'unstable'

        # N1 Prediction: 65 + (500 * 0.01) - (65 - 65) * 0.05 = 65 + 5 - 0 = 70.0
        # N2 Prediction: 75 + (500 * 0.01) - (75 - 65) * 0.05 = 75 + 5 - (10 * 0.05) = 80 - 0.5 = 79.5
        preds = {p['node']: p['t_future'] for p in forecast['nodes']}
        assert preds['N1'] == 70.0
        assert preds['N2'] == 79.5

    asyncio.run(run())
