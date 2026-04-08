import pytest
import asyncio
from apex_core.models import ThermalNode, RackCell, CoolingZone, CoolingMode
from apex_core.pistons import CORETHINKPiston, SONICPiston, BODYBUILDERPiston

def test_compute_thermals_empty():
    zone = CoolingZone(zone_id="ZONE-EMPTY", zone_name="Empty Zone")
    zone.compute_thermals()
    assert zone.avg_temp == 0.0
    assert zone.peak_temp == 0.0

def test_compute_thermals_cellular():
    node = ThermalNode(
        node_id="NODE-1", rack_id="RACK-1", zone_id="ZONE-1",
        temp_celsius=75.0, gpu_utilization=0.5, power_watts=500.0
    )
    cell = RackCell(rack_id="RACK-1", zone_id="ZONE-1", nodes=[node])
    zone = CoolingZone(zone_id="ZONE-1", zone_name="Cellular Zone", cells=[cell])

    zone.compute_thermals()
    assert zone.avg_temp == 75.0
    assert zone.peak_temp == 75.0
    assert node.alert_level == 1
    assert cell.exhaust_temp_c == 75.0
    assert cell.power_draw_kw == 0.5

def test_compute_thermals_multiple_cells():
    nodes1 = [ThermalNode(node_id="N1", rack_id="R1", zone_id="Z1", temp_celsius=60.0, gpu_utilization=0.4, power_watts=400.0)]
    nodes2 = [ThermalNode(node_id="N2", rack_id="R2", zone_id="Z1", temp_celsius=80.0, gpu_utilization=0.6, power_watts=600.0)]

    cells = [
        RackCell(rack_id="R1", zone_id="Z1", nodes=nodes1),
        RackCell(rack_id="R2", zone_id="Z1", nodes=nodes2)
    ]
    zone = CoolingZone(zone_id="Z1", zone_name="Multi Cell Zone", cells=cells)

    zone.compute_thermals()
    assert zone.avg_temp == 70.0  # (60 + 80) / 2
    assert zone.peak_temp == 80.0
    assert cells[0].exhaust_temp_c == 60.0
    assert cells[1].exhaust_temp_c == 80.0

def test_compute_thermals_invalid_readings():
    node1 = ThermalNode(node_id="N1", rack_id="R1", zone_id="Z1", temp_celsius=60.0, gpu_utilization=0.4, power_watts=400.0)
    node2 = ThermalNode(node_id="N2", rack_id="R1", zone_id="Z1", temp_celsius=200.0, gpu_utilization=0.6, power_watts=600.0)

    cell = RackCell(rack_id="R1", zone_id="Z1", nodes=[node1, node2])
    zone = CoolingZone(zone_id="Z1", zone_name="Invalid Readings Zone", cells=[cell])

    zone.compute_thermals()
    assert zone.avg_temp == 60.0
    assert zone.peak_temp == 60.0

def test_tactical_pistons():
    async def run():
        sonic = SONICPiston()
        bodybuilder = BODYBUILDERPiston()

        node = ThermalNode(node_id="N1", rack_id="R1", zone_id="Z1", temp_celsius=90.0, gpu_utilization=0.9, power_watts=800.0)

        # Test SONIC
        res_sonic = await sonic.execute({'target_nodes': [node]})
        assert len(res_sonic['hardware_overrides']) == 1
        assert res_sonic['hardware_overrides'][0]['bypass'] == 'OS_KERNEL'

        # Test BODYBUILDER
        res_bb = await bodybuilder.execute({'unstable_zones': ['ZONE-1']})
        assert len(res_bb['rebalancing_ops']) == 1
        assert res_bb['rebalancing_ops'][0]['reason'] == 'HIGH_ENTROPY'

    asyncio.run(run())
