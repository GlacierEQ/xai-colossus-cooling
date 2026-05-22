"""
Chiller Plant Controller — Phase 5D
Magnetic-bearing centrifugal chillers, R-1234ze refrigerant, COP 7.8 target.
Staging logic: load-based chiller sequencing for optimal COP across partial loads.
"""
import asyncio, logging, uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Callable

logger = logging.getLogger(__name__)

NUM_CHILLERS = 12          # 12 × 120 MW cooling = 1.44 GW total
CHILLER_CAPACITY_KW = 120_000
COP_RATED = 7.8
CHW_SUPPLY_SETPOINT_C = 7.0
CHW_RETURN_DESIGN_C = 13.0


class ChillerState(Enum):
    STANDBY  = "standby"
    STARTING = "starting"
    ONLINE   = "online"
    TRIPPED  = "tripped"
    MAINT    = "maintenance"


@dataclass
class Chiller:
    unit_id: str
    capacity_kw: float = CHILLER_CAPACITY_KW
    state: ChillerState = ChillerState.STANDBY
    load_pct: float = 0.0
    chw_supply_c: float = CHW_SUPPLY_SETPOINT_C
    chw_return_c: float = CHW_RETURN_DESIGN_C
    refrigerant: str = "R-1234ze"
    bearing_type: str = "magnetic"
    cop: float = 0.0

    @property
    def kw_cooling(self) -> float:
        return self.capacity_kw * (self.load_pct / 100) if self.state == ChillerState.ONLINE else 0.0

    @property
    def kw_power(self) -> float:
        if self.state != ChillerState.ONLINE or self.load_pct == 0:
            return 0.0
        # COP degrades slightly at partial load (IPLV model)
        iplv_factor = 1.0 + 0.15 * (1 - self.load_pct / 100)
        effective_cop = COP_RATED / iplv_factor
        self.cop = round(effective_cop, 2)
        return self.kw_cooling / effective_cop


class ChillerPlantController:
    def __init__(self, kafka_callback: Optional[Callable] = None, influx_sink=None):
        self.kafka_cb = kafka_callback
        self.influx = influx_sink
        self.chillers: Dict[str, Chiller] = {
            f"CH-{i+1:02d}": Chiller(unit_id=f"CH-{i+1:02d}") for i in range(NUM_CHILLERS)
        }
        self.running = False
        self.stats = {"stagings": 0, "trips": 0}

    async def set_load(self, total_kw_cooling: float):
        """Distribute cooling load across available chillers."""
        available = [c for c in self.chillers.values()
                     if c.state in (ChillerState.STANDBY, ChillerState.ONLINE)]
        capacity = len(available) * CHILLER_CAPACITY_KW
        if total_kw_cooling > capacity:
            logger.error("COOLING OVERLOAD: %.0f kW requested, %.0f kW available",
                         total_kw_cooling, capacity)
        # Stage on chillers as needed
        needed = total_kw_cooling
        for ch in available:
            if needed <= 0:
                if ch.state == ChillerState.ONLINE:
                    ch.state = ChillerState.STANDBY
                    ch.load_pct = 0.0
                continue
            if ch.state == ChillerState.STANDBY:
                ch.state = ChillerState.ONLINE
                self.stats["stagings"] += 1
                await self._emit("chiller_staged_on", {"unit": ch.unit_id})
            ch.load_pct = min(100.0, (min(needed, ch.capacity_kw) / ch.capacity_kw) * 100)
            needed -= ch.kw_cooling

    def snapshot(self):
        total_kw = sum(c.kw_cooling for c in self.chillers.values())
        total_power = sum(c.kw_power for c in self.chillers.values())
        avg_cop = (total_kw / total_power) if total_power > 0 else 0.0
        return {
            "chillers_online": sum(1 for c in self.chillers.values() if c.state == ChillerState.ONLINE),
            "total_kw_cooling": round(total_kw, 1),
            "total_kw_power": round(total_power, 1),
            "avg_cop": round(avg_cop, 3),
            "stats": self.stats,
        }

    async def _emit(self, event: str, extra: dict = {}):
        if self.kafka_cb:
            await self.kafka_cb("colossus.cooling.chiller", {
                "event_id": str(uuid.uuid4()), "event_type": event,
                "timestamp": datetime.now(timezone.utc).isoformat(), **extra,
            })
