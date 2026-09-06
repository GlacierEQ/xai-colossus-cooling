"""
Cooling Tower Controller — Phase 5D
Forced-draft ZLD towers, Legionella protocol, fan speed modulation.
Zero Liquid Discharge: all blowdown treated and recycled.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Optional

logger = logging.getLogger(__name__)

NUM_TOWERS = 8
TOWER_CAPACITY_KW = 180_000  # 8 × 180 MW = 1.44 GW total rejection


@dataclass
class CoolingTower:
    unit_id: str
    online: bool = True
    fan_speed_pct: float = 70.0
    condenser_water_supply_c: float = 29.0
    condenser_water_return_c: float = 35.0
    cycles_of_concentration: float = 6.0
    blowdown_active: bool = False
    legionella_risk_score: float = 0.0  # 0-10; >7 triggers thermal shock


class CoolingTowerController:
    def __init__(self, kafka_callback: Optional[Callable] = None):
        self.kafka_cb = kafka_callback
        self.towers = {
            f"CT-{i + 1:02d}": CoolingTower(f"CT-{i + 1:02d}")
            for i in range(NUM_TOWERS)
        }
        self.stats = {"legionella_shocks": 0, "blowdown_cycles": 0}

    async def modulate_fans(self, target_cws_temp_c: float = 29.0):
        """Adjust fan speed on all towers to hit condenser water supply setpoint."""
        for t in self.towers.values():
            delta = t.condenser_water_supply_c - target_cws_temp_c
            t.fan_speed_pct = max(20.0, min(100.0, t.fan_speed_pct + delta * 5))
            t.condenser_water_supply_c = max(
                target_cws_temp_c, t.condenser_water_supply_c - (delta * 0.8)
            )

    async def legionella_check(self):
        """Weekly ATP test sim — score >7 triggers 70°C thermal shock."""
        for t in self.towers.values():
            if t.legionella_risk_score > 7.0:
                logger.critical(
                    "LEGIONELLA RISK CT %s — initiating thermal shock", t.unit_id
                )
                await self._emit("legionella_thermal_shock", {"unit": t.unit_id})
                t.legionella_risk_score = 0.0
                self.stats["legionella_shocks"] += 1

    async def zld_blowdown(self, tower_id: str):
        """Trigger ZLD blowdown cycle — all reject water to treatment, not drain."""
        t = self.towers[tower_id]
        t.blowdown_active = True
        self.stats["blowdown_cycles"] += 1
        await self._emit(
            "zld_blowdown_start", {"unit": tower_id, "coc": t.cycles_of_concentration}
        )
        await asyncio.sleep(0.1)  # In production: await treatment system confirmation
        t.blowdown_active = False
        await self._emit("zld_blowdown_complete", {"unit": tower_id})

    def snapshot(self):
        return {
            "towers_online": sum(1 for t in self.towers.values() if t.online),
            "avg_fan_speed_pct": round(
                sum(t.fan_speed_pct for t in self.towers.values()) / NUM_TOWERS, 1
            ),
            "avg_cws_temp_c": round(
                sum(t.condenser_water_supply_c for t in self.towers.values())
                / NUM_TOWERS,
                2,
            ),
            "stats": self.stats,
        }

    async def _emit(self, event: str, extra: dict = {}):
        if self.kafka_cb:
            await self.kafka_cb(
                "colossus.cooling.tower",
                {
                    "event_id": str(uuid.uuid4()),
                    "event_type": event,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    **extra,
                },
            )
