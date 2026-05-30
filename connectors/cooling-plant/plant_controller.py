"""
Cooling Plant Controller — Phase 5D (Unified)
Orchestrates chillers, cooling towers, free cooling, and AI pre-cooling.
Computes real-time PUE contribution and publishes to digital twin.
"""
import asyncio, logging
from datetime import datetime, timezone
from typing import Callable, Optional

from .chiller_plant import ChillerPlantController
from .cooling_tower import CoolingTowerController
from .free_cooling import FreeCoolingController

logger = logging.getLogger(__name__)

PUE_TARGET = 1.03


class CoolingPlantController:
    def __init__(
        self,
        kafka_callback: Optional[Callable] = None,
        influx_sink=None,
    ):
        self.kafka_cb = kafka_callback
        self.influx = influx_sink
        self.chillers = ChillerPlantController(kafka_callback, influx_sink)
        self.towers = CoolingTowerController(kafka_callback)
        self.economiser = FreeCoolingController()
        self.running = False
        self._it_load_kw: float = 0.0
        self._ambient_c: float = 20.0

    # ------------------------------------------------------------------
    # Main control loop — runs every 30 seconds
    # ------------------------------------------------------------------
    async def run(self, interval_s: float = 30.0):
        self.running = True
        while self.running:
            try:
                await self._control_cycle()
            except Exception as exc:
                logger.error("CoolingPlantController error: %s", exc)
            await asyncio.sleep(interval_s)

    async def stop(self):
        self.running = False

    async def _control_cycle(self):
        # 1. Evaluate economiser
        eco = self.economiser.evaluate(self._ambient_c, self._it_load_kw)
        reduction = eco.chiller_load_reduction_pct / 100.0
        chiller_load_kw = self._it_load_kw * (1.0 - reduction)

        # 2. Set chiller load
        await self.chillers.set_load(chiller_load_kw)

        # 3. Modulate cooling towers to hit 29°C CWS
        await self.towers.modulate_fans(target_cws_temp_c=29.0)

        # 4. Legionella check (weekly in production — every cycle in sim)
        await self.towers.legionella_check()

        # 5. Compute + publish PUE contribution
        snap = self.snapshot()
        pue_cooling = snap["pue_cooling_contribution"]
        if pue_cooling > PUE_TARGET:
            logger.warning("PUE cooling contribution %.3f exceeds target %.3f",
                           pue_cooling, PUE_TARGET)

        if self.influx:
            await self.influx.write_reading(
                measurement="colossus_cooling_plant",
                tags={"scope": "facility"},
                fields=snap,
            )

    def update_conditions(self, it_load_kw: float, ambient_c: float):
        """Called by digital twin or SCADA with live conditions."""
        self._it_load_kw = it_load_kw
        self._ambient_c = ambient_c

    def snapshot(self):
        chiller_snap = self.chillers.snapshot()
        tower_snap = self.towers.snapshot()
        eco_snap = self.economiser.snapshot()
        cooling_power_kw = chiller_snap["total_kw_power"]
        it_kw = self._it_load_kw if self._it_load_kw > 0 else 1.0
        pue_cooling = round(1.0 + (cooling_power_kw / it_kw), 4)
        return {
            **chiller_snap,
            **{f"tower_{k}": v for k, v in tower_snap.items()},
            **{f"eco_{k}": v for k, v in eco_snap.items()},
            "pue_cooling_contribution": pue_cooling,
            "ambient_c": self._ambient_c,
            "it_load_kw": self._it_load_kw,
        }
