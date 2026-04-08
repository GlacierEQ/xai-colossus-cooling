import asyncio
import logging
from typing import List, Optional
from apex_core.models import CoolingMode, CoolingZone, ThermalNode
from apex_core.pistons import (
    CORETHINKPiston, MICROWAVEPiston, SUPERNOVAPiston, SHADOWPiston, GHOSTPiston,
    SONICPiston, BODYBUILDERPiston
)

class APEXThermalOrchestrator:
    """
    Main APEX Orchestrator for xAI Colossus Cooling.
    Coordinates all 12 stealth pistons across the Mitochondria tier.
    """

    VERSION = '1.0.0-COLOSSUS'
    CODENAME = 'GLACIER-THERMAL'

    def __init__(self, mode: CoolingMode = CoolingMode.COLOSSUS):
        self.mode = mode
        self.zones: List[CoolingZone] = []
        self.all_nodes: List[ThermalNode] = []
        self.tick = 0
        self.logger = logging.getLogger('APEX-ORCHESTRATOR')

        self.pistons = {
            'CORE-THINK':  CORETHINKPiston(),
            'MICROWAVE':   MICROWAVEPiston(),
            'SUPERNOVA':   SUPERNOVAPiston(),
            'SHADOW':      SHADOWPiston(),
            'GHOST':       GHOSTPiston(),
            'SONIC':       SONICPiston(),
            'BODYBUILDER': BODYBUILDERPiston(),
        }

        self.logger.info(f'APEX Thermal Orchestrator v{self.VERSION} [{self.CODENAME}] INITIALIZED')

    def register_zone(self, zone: CoolingZone):
        self.zones.append(zone)
        self.all_nodes.extend(zone.all_nodes)
        self.logger.info(f'Zone registered: {zone.zone_id} ({len(zone.all_nodes)} nodes)')

    async def tick_cycle(self):
        """One full orchestration tick — runs every 500ms in production."""
        self.tick += 1

        # 1. Predictive Reasoning
        core_think_ctx = {'zones': self.zones, 'trigger': f'tick_{self.tick}'}
        core_think_res = await self.pistons['CORE-THINK'].activate(core_think_ctx)

        # 1a. BODYBUILDER rebalancing if entropy is high
        unstable_zones = [z for z, data in core_think_res.get('forecast', {}).items() if data.get('status') == 'unstable']
        if unstable_zones:
            await self.pistons['BODYBUILDER'].activate({'unstable_zones': unstable_zones})

        # 2. Silent Monitoring
        shadow_ctx = {'all_nodes': self.all_nodes, 'trigger': f'tick_{self.tick}'}
        shadow_result = await self.pistons['SHADOW'].activate(shadow_ctx)

        # 3. Background Optimization
        ghost_ctx = {'zones': self.zones, 'trigger': f'tick_{self.tick}'}
        await self.pistons['GHOST'].activate(ghost_ctx)

        # 4. Emergency Response
        critical_nodes = [n for n in self.all_nodes if n.temp_celsius >= 85]
        if critical_nodes:
            supernova_ctx = {'critical_nodes': critical_nodes, 'trigger': 'THERMAL_CRITICAL'}
            await self.pistons['SUPERNOVA'].activate(supernova_ctx)

            # 4a. SONIC direct hardware reflex
            await self.pistons['SONIC'].activate({'target_nodes': critical_nodes})

        # 5. Scheduled Sweeps
        if self.tick % 5 == 0:
            microwave_ctx = {'zones': self.zones, 'trigger': 'SCHEDULED_SWEEP'}
            await self.pistons['MICROWAVE'].activate(microwave_ctx)

        return {
            'tick': self.tick,
            'zones': len(self.zones),
            'nodes': len(self.all_nodes),
            'critical': len(critical_nodes),
            'anomalies': len(shadow_result.get('anomalies', []))
        }

    async def run(self, duration_ticks: Optional[int] = None):
        tick_count = 0
        while True:
            await self.tick_cycle()
            tick_count += 1
            if duration_ticks and tick_count >= duration_ticks:
                break
            await asyncio.sleep(0.5)
