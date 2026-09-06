#!/usr/bin/env python3
"""
Cell Adapter — RackCell → ThermalNode / CoolingZone Bridge
GlacierEQ APEX Architecture
Author: Casey Barton

Converts the physical hardware model (RackCell) into the
orchestrator's logical model (ThermalNode, CoolingZone).

This is the bridge between the sensor/hardware layer and the
APEX piston execution layer.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import List, Dict
from cells.rack_cell import RackCell
from apex_core.thermal_orchestrator import ThermalNode, CoolingZone


def rack_to_thermal_node(rack: RackCell) -> ThermalNode:
    """
    Map a RackCell to a ThermalNode.
    Uses exhaust temp as the primary thermal signal (worst-case view).
    """
    return ThermalNode(
        node_id=rack.rack_id,
        rack_id=rack.rack_id,
        zone_id=rack.zone_id,
        temp_celsius=rack.exhaust_temp_c,
        gpu_utilization=rack.utilization_pct / 100.0,
        power_watts=rack.power_draw_kw * 1000.0,
    )


def build_zones_from_racks(racks: List[RackCell]) -> List[CoolingZone]:
    """
    Group RackCells by zone_id and build CoolingZone objects.
    Returns a list of CoolingZones ready to register with the orchestrator.
    """
    zone_map: Dict[str, CoolingZone] = {}
    for rack in racks:
        if rack.zone_id not in zone_map:
            zone_map[rack.zone_id] = CoolingZone(
                zone_id=rack.zone_id, zone_name=f"Zone {rack.zone_id}"
            )
        node = rack_to_thermal_node(rack)
        zone_map[rack.zone_id].nodes.append(node)
    return list(zone_map.values())


def update_nodes_from_racks(
    racks: List[RackCell], zone_list: List[CoolingZone]
) -> None:
    """
    Update existing ThermalNode temps/power from freshly-polled RackCells.
    Mutates zone_list nodes in-place — call this each sensor poll cycle.
    """
    node_lookup: Dict[str, ThermalNode] = {}
    for zone in zone_list:
        for node in zone.nodes:
            node_lookup[node.node_id] = node

    for rack in racks:
        node = node_lookup.get(rack.rack_id)
        if node:
            node.temp_celsius = rack.exhaust_temp_c
            node.gpu_utilization = rack.utilization_pct / 100.0
            node.power_watts = rack.power_draw_kw * 1000.0
