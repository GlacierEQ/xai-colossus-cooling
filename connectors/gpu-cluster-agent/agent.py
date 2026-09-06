"""
GPUClusterAgent
===============
Top-level orchestrator for the 2M GPU cluster.
Registers with M2A as pillar='gpu_thermal'.
Coordinates: NVL72NodeRegistry + ThermalThrottleCoordinator.
Publishes cluster snapshots to Kafka colossus.gpu.thermal every 30s.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Callable
from .node_registry import NVL72NodeRegistry, ZONES
from .thermal_coordinator import ThermalThrottleCoordinator

logger = logging.getLogger(__name__)


class GPUClusterAgent:
    def __init__(
        self,
        kafka_callback: Optional[Callable] = None,
        influx_sink=None,
        precooling_engine=None,
        gpu_model: str = "H200",
    ):
        self.kafka_cb = kafka_callback
        self.influx = influx_sink
        self.gpu_model = gpu_model
        self.registry = NVL72NodeRegistry()
        self.thermal_coordinator = ThermalThrottleCoordinator(
            registry=self.registry,
            kafka_callback=kafka_callback,
            influx_sink=influx_sink,
            precooling_engine=precooling_engine,
        )
        self._running = False
        self._stats = {"snapshots_published": 0, "zones_active": 0}

    async def initialize(self):
        """Build full 2M GPU cluster topology in memory."""
        logger.info("[GPUAgent] Initializing 2M GPU cluster topology...")
        for zone_id in ZONES:
            self.registry.build_zone(zone_id, gpu_model=self.gpu_model)
        total = self.registry.total_registered()
        self._stats["zones_active"] = len(ZONES)
        logger.info(
            f"[GPUAgent] Ready — {total} NVL72 nodes / {total * 72:,} GPUs registered"
        )

    async def start(self):
        self._running = True
        await asyncio.gather(
            self.thermal_coordinator.start(),
            self._snapshot_loop(),
        )

    async def stop(self):
        self._running = False
        await self.thermal_coordinator.stop()

    async def _snapshot_loop(self):
        while self._running:
            await asyncio.sleep(30.0)
            snapshot = self.registry.cluster_snapshot()
            if snapshot:
                await self._publish_snapshot(snapshot)

    async def _publish_snapshot(self, snapshot: dict):
        self._stats["snapshots_published"] += 1
        if self.kafka_cb:
            asyncio.create_task(
                self.kafka_cb(
                    "colossus.gpu.thermal",
                    {
                        "event_id": str(uuid.uuid4()),
                        "snapshot_type": "cluster_summary",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        **snapshot,
                    },
                )
            )
        if self.influx:
            try:
                await self.influx.write_reading(
                    measurement="colossus_gpu_thermal",
                    tags={"scope": "cluster"},
                    fields={
                        "total_nodes": snapshot["total_nodes"],
                        "total_power_kw": snapshot["total_power_kw"],
                        "throttled_gpus": snapshot["throttled_gpus"],
                        "alert_gpus": snapshot["alert_gpus"],
                        "mean_die_temp_c": snapshot["mean_die_temp_c"],
                        "max_die_temp_c": snapshot["max_die_temp_c"],
                    },
                )
            except Exception as e:
                logger.warning(f"[GPUAgent] InfluxDB snapshot failed: {e}")

    def stats(self) -> dict:
        return {
            **self._stats,
            "registry": self.registry.cluster_snapshot(),
            "thermal": self.thermal_coordinator.stats(),
        }
