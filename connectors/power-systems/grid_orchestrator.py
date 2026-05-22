"""
Grid Orchestrator — Phase 6
Handles ATS/STS transfer logic, grid islanding, and load shed tiers.
"""
import asyncio, logging, uuid
from datetime import datetime, timezone
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class GridOrchestrator:
    def __init__(self, power_controller, kafka_callback: Optional[Callable] = None):
        self.power = power_controller
        self.kafka_cb = kafka_callback
        self.is_islanded = False

    async def fail_grid_a(self):
        self.power.sources["grid_a"].healthy = False
        await self._emit("grid_a_failure")
        await self._rebalance()

    async def fail_grid_b(self):
        self.power.sources["grid_b"].healthy = False
        await self._emit("grid_b_failure")
        await self._rebalance()

    async def island_mode(self):
        self.is_islanded = True
        self.power.sources["grid_a"].healthy = False
        self.power.sources["grid_b"].healthy = False
        await self._emit("facility_islanded")
        await self.power._dispatch_turbines()

    async def _rebalance(self):
        healthy_grid = any(self.power.sources[s].healthy for s in ("grid_a", "grid_b"))
        if not healthy_grid:
            await self.island_mode()
        else:
            await self.power._dispatch_turbines()

    async def _emit(self, event_type: str):
        if self.kafka_cb:
            await self.kafka_cb("colossus.power.events", {
                "event_id": str(uuid.uuid4()),
                "event_type": event_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
