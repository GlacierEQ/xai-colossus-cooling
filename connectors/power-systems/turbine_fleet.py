"""
Turbine Fleet Model — Phase 6 Power Hardening
Models 8× gas turbines: dispatch, health, black-start sequencing.
Design basis: Colossus 2 site requires 400 MW on-site generation backup.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional, Callable

logger = logging.getLogger(__name__)


class TurbineState(Enum):
    STANDBY = "standby"  # Hot standby — can synchronise in < 60 s
    STARTING = "starting"  # Black-start / warm-start sequence in progress
    ONLINE = "online"  # Generating, synchronised to bus
    TRIPPED = "tripped"  # Protection relay operated — requires reset
    OFFLINE = "offline"  # Planned maintenance / cold state


@dataclass
class Turbine:
    unit_id: str
    rated_mw: float = 50.0  # 8 × 50 MW = 400 MW total on-site
    min_mw: float = 15.0  # Technical minimum stable output
    ramp_rate_mw_per_min: float = 10.0
    heat_rate_mmbtu_per_mwh: float = 8.5
    state: TurbineState = TurbineState.STANDBY
    active_mw: float = 0.0
    exhaust_temp_c: float = 450.0
    vibration_mm_s: float = 1.2
    hours_since_major_service: int = 0
    trip_count_30d: int = 0

    @property
    def healthy(self) -> bool:
        return (
            self.state not in (TurbineState.TRIPPED, TurbineState.OFFLINE)
            and self.vibration_mm_s < 4.5
            and self.exhaust_temp_c < 560
        )

    @property
    def available_mw(self) -> float:
        return self.rated_mw if self.healthy else 0.0


BLACK_START_SEQUENCE = [
    ("GTG-01", 0),  # First unit — self-excited diesel crank
    ("GTG-02", 45),  # Parallel after 45 s once bus is live
    ("GTG-03", 90),
    ("GTG-04", 135),
    ("GTG-05", 180),
    ("GTG-06", 225),
    ("GTG-07", 270),
    ("GTG-08", 315),  # Full fleet online in < 6 min
]


class TurbineFleetController:
    def __init__(self, kafka_callback: Optional[Callable] = None):
        self.kafka_cb = kafka_callback
        self.fleet: Dict[str, Turbine] = {
            f"GTG-0{i + 1}": Turbine(unit_id=f"GTG-0{i + 1}") for i in range(8)
        }
        self.black_start_active = False
        self.stats = {"dispatches": 0, "trips": 0, "black_starts": 0}

    # -----------------------------------------------------------------
    # Economic dispatch — load follows with lowest heat-rate units first
    # -----------------------------------------------------------------
    async def dispatch(self, required_mw: float):
        remaining = required_mw
        priority = sorted(
            [
                t
                for t in self.fleet.values()
                if t.healthy and t.state == TurbineState.STANDBY
            ],
            key=lambda t: t.heat_rate_mmbtu_per_mwh,
        )
        for t in priority:
            if remaining <= 0:
                break
            t.state = TurbineState.ONLINE
            t.active_mw = min(t.rated_mw, remaining)
            remaining -= t.active_mw
            self.stats["dispatches"] += 1
            await self._emit("turbine_dispatch", {"unit": t.unit_id, "mw": t.active_mw})
        if remaining > 0:
            logger.warning(
                "TURBINE SHORTFALL %.1f MW — load shed may be required", remaining
            )

    # -----------------------------------------------------------------
    # Black-start protocol — zero external grid voltage
    # -----------------------------------------------------------------
    async def black_start(self):
        self.black_start_active = True
        self.stats["black_starts"] += 1
        logger.critical("BLACK-START initiated — sequencing 8 GTGs")
        for unit_id, delay_s in BLACK_START_SEQUENCE:
            await asyncio.sleep(delay_s if delay_s == 0 else 45)  # 45 s inter-unit
            t = self.fleet[unit_id]
            t.state = TurbineState.STARTING
            await asyncio.sleep(2)  # Simulate crank + synchronise
            t.state = TurbineState.ONLINE
            t.active_mw = t.min_mw
            await self._emit("black_start_unit_online", {"unit": unit_id})
        self.black_start_active = False
        logger.info("BLACK-START complete — all 8 GTGs online")

    # -----------------------------------------------------------------
    # Trip handler
    # -----------------------------------------------------------------
    async def trip_unit(self, unit_id: str, reason: str = "protection_relay"):
        t = self.fleet[unit_id]
        t.state = TurbineState.TRIPPED
        t.active_mw = 0.0
        t.trip_count_30d += 1
        self.stats["trips"] += 1
        await self._emit("turbine_trip", {"unit": unit_id, "reason": reason})

    def snapshot(self):
        return {
            "fleet": {
                k: {
                    "state": v.state.value,
                    "active_mw": v.active_mw,
                    "healthy": v.healthy,
                }
                for k, v in self.fleet.items()
            },
            "total_mw": sum(t.active_mw for t in self.fleet.values()),
            "stats": self.stats,
        }

    async def _emit(self, event: str, extra: dict = {}):
        if self.kafka_cb:
            payload = {
                "event_id": str(uuid.uuid4()),
                "event_type": event,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **extra,
            }
            await self.kafka_cb("colossus.power.turbines", payload)
