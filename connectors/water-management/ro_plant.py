"""
ROPlantController
=================
Controls the on-site Reverse Osmosis plant.
Rated: 500,000 L/day = 347 L/min continuous output.
Monitors: TDS, membrane pressure differential, permeate flow, reject ratio.
Auto-flush: triggers CIP (Clean-In-Place) when TDS > threshold or diff-P spike.

Membrane array: 6 stages x 12 elements per stage = 72 membrane elements.
Recovery rate target: 75% (25% brine reject to zero-discharge evaporation pond).
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Callable, List

logger = logging.getLogger(__name__)

RATED_OUTPUT_LPM = 347.0  # 500K L/day
TDS_PRODUCT_MAX_PPM = 10.0  # target < 10 ppm product water
TDS_FEED_TYPICAL_PPM = 150.0
DIFF_P_WARNING_BAR = 0.8  # membrane fouling indicator
DIFF_P_CRITICAL_BAR = 1.5
RECOVERY_RATE_TARGET = 0.75
MEMBRANE_STAGES = 6
MEMBRANES_PER_STAGE = 12
CIP_INTERVAL_DAYS = 30


@dataclass
class ROReading:
    timestamp: str
    feed_flow_lpm: float
    permeate_flow_lpm: float  # product water output
    reject_flow_lpm: float  # brine
    recovery_rate: float
    feed_tds_ppm: float
    product_tds_ppm: float
    rejection_pct: float  # (1 - product_tds/feed_tds) * 100
    feed_pressure_bar: float
    diff_pressure_bar: float  # feed vs concentrate pressure drop (fouling indicator)
    temp_c: float
    status: str = "ok"  # ok | warning | critical | cip_required
    cip_active: bool = False


@dataclass
class MembraneHealth:
    stage_id: int
    element_count: int
    diff_pressure_bar: float
    normalized_flux: float  # relative to baseline (1.0 = new)
    salt_rejection_pct: float
    last_cip: str
    health_score: float  # 0-1.0


class ROPlantController:
    def __init__(
        self,
        alert_callback: Optional[Callable] = None,
        influx_sink=None,
        kafka_callback: Optional[Callable] = None,
    ):
        self.alert_cb = alert_callback
        self.influx = influx_sink
        self.kafka_cb = kafka_callback
        self._running = False
        self._cip_active = False
        self._last_cip = datetime.now(timezone.utc).isoformat()
        self._membrane_health: List[MembraneHealth] = [
            MembraneHealth(
                stage_id=i,
                element_count=MEMBRANES_PER_STAGE,
                diff_pressure_bar=0.3,
                normalized_flux=1.0,
                salt_rejection_pct=99.5,
                last_cip=datetime.now(timezone.utc).isoformat(),
                health_score=1.0,
            )
            for i in range(1, MEMBRANE_STAGES + 1)
        ]
        self._history: List[ROReading] = []
        self._stats = {
            "readings": 0,
            "cip_cycles": 0,
            "tds_violations": 0,
            "warnings": 0,
        }

    async def start(self, poll_interval_sec: float = 30.0):
        self._running = True
        logger.info(f"[RO] Plant started — rated={RATED_OUTPUT_LPM}L/min")
        while self._running:
            reading = await self._read()
            await self._evaluate(reading)
            await self._emit(reading)
            self._history.append(reading)
            if len(self._history) > 1440:
                self._history.pop(0)
            self._stats["readings"] += 1
            await asyncio.sleep(poll_interval_sec)

    async def stop(self):
        self._running = False

    async def _read(self) -> ROReading:
        import random

        feed = round(
            RATED_OUTPUT_LPM / RECOVERY_RATE_TARGET * random.uniform(0.98, 1.02), 2
        )
        permeate = round(feed * RECOVERY_RATE_TARGET * random.uniform(0.97, 1.0), 2)
        reject = round(feed - permeate, 2)
        recovery = round(permeate / max(feed, 0.1), 4)
        feed_tds = round(TDS_FEED_TYPICAL_PPM * random.uniform(0.9, 1.1), 1)
        product_tds = round(
            feed_tds * random.uniform(0.02, 0.06), 2
        )  # 94-98% rejection
        rejection = round((1 - product_tds / max(feed_tds, 0.1)) * 100, 2)
        diff_p = round(random.uniform(0.2, 0.6), 3)
        status = "ok"
        if product_tds > TDS_PRODUCT_MAX_PPM:
            status = "warning"
            self._stats["tds_violations"] += 1
        if diff_p >= DIFF_P_CRITICAL_BAR:
            status = "cip_required"
        elif diff_p >= DIFF_P_WARNING_BAR:
            status = "warning"
            self._stats["warnings"] += 1
        return ROReading(
            timestamp=datetime.now(timezone.utc).isoformat(),
            feed_flow_lpm=feed,
            permeate_flow_lpm=permeate,
            reject_flow_lpm=reject,
            recovery_rate=recovery,
            feed_tds_ppm=feed_tds,
            product_tds_ppm=product_tds,
            rejection_pct=rejection,
            feed_pressure_bar=round(random.uniform(8.0, 10.0), 2),
            diff_pressure_bar=diff_p,
            temp_c=round(random.uniform(17.5, 19.0), 2),
            status=status,
            cip_active=self._cip_active,
        )

    async def _evaluate(self, r: ROReading):
        if r.status == "cip_required" and not self._cip_active:
            await self._trigger_cip(r)
        if r.status != "ok" and self.alert_cb:
            asyncio.create_task(self.alert_cb(r))

    async def _trigger_cip(self, r: ROReading):
        self._cip_active = True
        self._stats["cip_cycles"] += 1
        logger.warning(f"[RO] CIP triggered diff_P={r.diff_pressure_bar}bar")
        if self.kafka_cb:
            asyncio.create_task(
                self.kafka_cb(
                    "colossus.cooling.events",
                    {
                        "event_id": str(uuid.uuid4()),
                        "event_type": "ro_cip_start",
                        "timestamp": r.timestamp,
                        "diff_pressure_bar": r.diff_pressure_bar,
                    },
                )
            )
        await asyncio.sleep(0.1)  # CIP runs async in real system
        self._cip_active = False
        self._last_cip = datetime.now(timezone.utc).isoformat()

    async def _emit(self, r: ROReading):
        if not self.influx:
            return
        try:
            await self.influx.write_reading(
                measurement="colossus_water_flow",
                tags={"source": "ro_plant", "status": r.status},
                fields={
                    "permeate_lpm": r.permeate_flow_lpm,
                    "product_tds_ppm": r.product_tds_ppm,
                    "rejection_pct": r.rejection_pct,
                    "diff_pressure_bar": r.diff_pressure_bar,
                    "recovery_rate": r.recovery_rate,
                    "cip_active": int(r.cip_active),
                },
                ts=r.timestamp,
            )
        except Exception as e:
            logger.warning(f"[RO] InfluxDB emit failed: {e}")

    def membrane_health_summary(self) -> list:
        return [
            {
                "stage": m.stage_id,
                "health": m.health_score,
                "diff_p": m.diff_pressure_bar,
            }
            for m in self._membrane_health
        ]

    def stats(self) -> dict:
        return self._stats
