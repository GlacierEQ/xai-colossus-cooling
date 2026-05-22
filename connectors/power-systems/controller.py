"""
Power Systems Controller — Phase 6
Controls substations, gas turbines, UPS strings, and transfer switching.
"""
import asyncio, logging, uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional, Callable

logger = logging.getLogger(__name__)


class PowerSource(Enum):
    GRID_A = "grid_a"
    GRID_B = "grid_b"
    TURBINE = "turbine"
    UPS = "ups"


@dataclass
class SourceMetrics:
    source: str
    mw_available: float
    mw_active: float
    healthy: bool = True


class PowerSystemsController:
    def __init__(self, kafka_callback: Optional[Callable] = None, influx_sink=None):
        self.kafka_cb = kafka_callback
        self.influx = influx_sink
        self.sources: Dict[str, SourceMetrics] = {
            "grid_a": SourceMetrics("grid_a", 500.0, 420.0),
            "grid_b": SourceMetrics("grid_b", 500.0, 390.0),
            "turbine": SourceMetrics("turbine", 400.0, 0.0),
            "ups": SourceMetrics("ups", 120.0, 0.0),
        }
        self.running = False
        self.stats = {"failovers": 0, "load_shed_events": 0, "black_starts": 0}

    async def start(self):
        self.running = True
        while self.running:
            await self._evaluate_capacity()
            await asyncio.sleep(5)

    async def stop(self):
        self.running = False

    async def _evaluate_capacity(self):
        total_active = sum(s.mw_active for s in self.sources.values())
        total_avail = sum(s.mw_available for s in self.sources.values() if s.healthy)
        if total_active > total_avail * 0.9:
            await self._dispatch_turbines()
        if self.influx:
            await self.influx.write_reading(
                measurement="colossus_power",
                tags={"scope": "facility"},
                fields={"mw_active": total_active, "mw_available": total_avail},
            )

    async def _dispatch_turbines(self):
        self.sources["turbine"].mw_active = min(self.sources["turbine"].mw_available, 320.0)
        self.stats["failovers"] += 1
        payload = {
            "event_id": str(uuid.uuid4()),
            "event_type": "turbine_dispatch",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mw_active": self.sources["turbine"].mw_active,
        }
        if self.kafka_cb:
            await self.kafka_cb("colossus.power.events", payload)

    def snapshot(self):
        return {"sources": {k: vars(v) for k, v in self.sources.items()}, "stats": self.stats}
