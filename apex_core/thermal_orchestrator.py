#!/usr/bin/env python3
"""
APEX Thermal Orchestrator — xAI Colossus Cooling
GlacierEQ Sovereign Stack
Author: Casey Barton

Backward-compatible entry point for the modular APEX architecture.
"""

import asyncio
from apex_core.models import CoolingMode, CoolingZone, ThermalNode
from apex_core.pistons import (
    APEXPiston, CORETHINKPiston, MICROWAVEPiston,
    SUPERNOVAPiston, SHADOWPiston, GHOSTPiston
)
from apex_core.orchestrator import APEXThermalOrchestrator

async def main():
    orchestrator = APEXThermalOrchestrator(mode=CoolingMode.COLOSSUS)

    # Example: Register 3 cooling zones with 10 nodes each
    for zone_idx in range(3):
        zone = CoolingZone(
            zone_id=f'ZONE-{zone_idx:03d}',
            zone_name=f'Colossus Zone {zone_idx}'
        )
        for node_idx in range(10):
            node = ThermalNode(
                node_id=f'NODE-{zone_idx:03d}-{node_idx:04d}',
                rack_id=f'RACK-{zone_idx:03d}',
                zone_id=zone.zone_id,
                temp_celsius=65.0 + (node_idx * 0.5),
                gpu_utilization=0.85,
                power_watts=700.0
            )
            zone.nodes.append(node)
        orchestrator.register_zone(zone)

    # Run 10 ticks for demo
    await orchestrator.run(duration_ticks=10)


if __name__ == '__main__':
    asyncio.run(main())
