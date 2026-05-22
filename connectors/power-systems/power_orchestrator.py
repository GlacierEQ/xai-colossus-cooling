"""
PowerOrchestrator
==================
Top-level power system coordinator for xAI Colossus Phase 6.

Total capacity model:
  Utility (SUB-A + SUB-B):  1,000 MW
  Gas turbines (8x GT):       440 MW
  UPS bridge (T1):             50 MW / 8 min
  -----------------------------------------------
  TOTAL FIRM:               1,440 MW
  Design load:              1,435 MW (GPU 1.4GW + facility 35MW)
  Headroom:                     5 MW (tightest margin; triggers turbine pre-spin at 1,380 MW)

Automation:
  - Substation overload >95% -> pre-spin 2 turbines (10-min lead)
  - Grid frequency deviation >0.1 Hz -> immediate ATS alert
  - Any substation offline -> immediate turbine ISLAND mode
  - UPS SOC < 40% -> alert + pause non-critical loads
"""
import asyncio, logging, uuid
from datetime import datetime, timezone
from typing import Optional, Callable
from .substation import SubstationController
from .turbine_array import GasTurbineArrayController, TurbineMode
from .ups_manager import UPSManager
from .transfer_switch import AutomaticTransferSwitch

logger = logging.getLogger(__name__)

DESIGN_LOAD_MW         = 1_435.0
PRESPIN_THRESHOLD_MW   = 1_380.0
TOTAL_FIRM_MW          = 1_440.0


class PowerOrchestrator:
    def __init__(self, kafka_callback: Optional[Callable] = None, influx_sink=None):
        self.kafka_cb  = kafka_callback
        self.influx    = influx_sink
        self.substation = SubstationController(kafka_callback, influx_sink)
        self.turbines   = GasTurbineArrayController(kafka_callback, influx_sink)
        self.ups        = UPSManager(kafka_callback, influx_sink)
        self.ats        = AutomaticTransferSwitch(
            turbine_array=self.turbines, ups_manager=self.ups,
            kafka_callback=kafka_callback, influx_sink=influx_sink
        )
        self._running  = False
        self._stats    = {"snapshots": 0, "prespin_events": 0, "grid_loss_events": 0}

    async def start(self):
        self._running = True
        logger.info("[PowerOrch] Phase 6 Power Systems starting")
        logger.info(f"[PowerOrch] Firm capacity: {TOTAL_FIRM_MW}MW | Design load: {DESIGN_LOAD_MW}MW")
        await asyncio.gather(
            self.substation.start(),
            self.turbines.start(),
            self.ups.start(),
            self.ats.start(),
            self._supervision_loop(),
        )

    async def stop(self):
        self._running = False
        await asyncio.gather(
            self.substation.stop(),
            self.turbines.stop(),
            self.ups.stop(),
            self.ats.stop(),
        )

    async def _supervision_loop(self):
        while self._running:
            await asyncio.sleep(10.0)
            cluster = self.substation.cluster_load()
            total_load = cluster.get("total_load_mw", 0.0)
            # Pre-spin trigger
            if total_load >= PRESPIN_THRESHOLD_MW:
                self._stats["prespin_events"] += 1
                logger.warning(f"[PowerOrch] Load {total_load}MW >= prespin threshold {PRESPIN_THRESHOLD_MW}MW")
            # Grid loss detection — any substation offline
            for sid, sub in cluster.get("substations", {}).items():
                if sub["status"] == "offline":
                    self._stats["grid_loss_events"] += 1
                    logger.critical(f"[PowerOrch] GRID LOSS: {sid} offline — executing ATS transfer")
                    await self.ats.execute_transfer(reason=f"{sid}_offline")
                    break
            # Snapshot
            self._stats["snapshots"] += 1
            if self.kafka_cb:
                asyncio.create_task(self.kafka_cb("colossus.power.status", {
                    "event_id": str(uuid.uuid4()),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "total_load_mw": total_load,
                    "firm_capacity_mw": TOTAL_FIRM_MW,
                    "headroom_mw": round(TOTAL_FIRM_MW - total_load, 2),
                    "substation_status": cluster,
                    "turbine_status": self.turbines.array_status(),
                    "ats_status": self.ats.status(),
                }))

    def status(self) -> dict:
        return {"firm_capacity_mw": TOTAL_FIRM_MW, "design_load_mw": DESIGN_LOAD_MW,
                "substation": self.substation.cluster_load(),
                "turbines": self.turbines.array_status(),
                "ats": self.ats.status(), "stats": self._stats}
