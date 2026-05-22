"""
ThermalThrottleCoordinator
===========================
Zone-level thermal management for the 2M GPU cluster.
Monitors node thermals, issues throttle commands, coordinates
with water management pre-cooling for proactive intervention.

Throttle policy:
  die_temp >= 83C  -> 25% power reduction
  die_temp >= 87C  -> 50% power reduction  
  die_temp >= 90C  -> 75% power reduction + CRITICAL alert
  die_temp >= 95C  -> emergency shutdown node
"""
import asyncio, logging, time
from typing import Optional, Callable, Dict
from .node_registry import NVL72NodeRegistry, NVL72Node, THROTTLE_TEMP_C, CRITICAL_TEMP_C

logger = logging.getLogger(__name__)

THROTTLE_LEVELS = [
    (95.0, 100.0, "emergency_shutdown"),
    (90.0,  75.0, "critical"),
    (87.0,  50.0, "high"),
    (83.0,  25.0, "warning"),
]


class ThermalThrottleCoordinator:
    def __init__(self, registry: NVL72NodeRegistry,
                 kafka_callback: Optional[Callable] = None,
                 influx_sink=None,
                 precooling_engine=None):
        self.registry = registry
        self.kafka_cb = kafka_callback
        self.influx = influx_sink
        self.precooling = precooling_engine
        self._running = False
        self._zone_throttle_state: Dict[str, str] = {}
        self._stats = {"throttle_events": 0, "emergency_shutdowns": 0,
                       "precooling_requests": 0, "nodes_evaluated": 0}

    async def start(self, poll_interval_sec: float = 5.0):
        self._running = True
        logger.info("[ThermalCoord] Started — monitoring 2M GPU cluster")
        while self._running:
            await self._evaluate_all_zones()
            await asyncio.sleep(poll_interval_sec)

    async def stop(self): self._running = False

    async def _evaluate_all_zones(self):
        import asyncio
        tasks = [self._evaluate_zone(z) for z in self.registry._zone_index]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _evaluate_zone(self, zone_id: str):
        nodes = self.registry.zone_nodes(zone_id)
        if not nodes: return
        for node in nodes:
            await self._evaluate_node(node)
            self._stats["nodes_evaluated"] += 1

    async def _evaluate_node(self, node: NVL72Node):
        import random
        # Simulate live thermal reads — in production: NVMe/NVML API calls
        for gpu in node.gpus:
            gpu.die_temp_c    = round(TARGET_DIE_TEMP_C + random.gauss(0, 1.5), 2)
            gpu.memory_temp_c = round(gpu.die_temp_c - 7.0 + random.gauss(0, 0.5), 2)
            gpu.power_w       = round(700.0 * random.uniform(0.85, 1.0), 1)
            gpu.thermal_alert = gpu.die_temp_c >= THROTTLE_TEMP_C
            gpu.throttle_pct  = self._throttle_pct(gpu.die_temp_c)
        node.update_thermals()

        if node.status in ("throttling", "critical"):
            await self._handle_throttle(node)

    def _throttle_pct(self, temp_c: float) -> float:
        for threshold, reduction, _ in THROTTLE_LEVELS:
            if temp_c >= threshold:
                return reduction
        return 0.0

    async def _handle_throttle(self, node: NVL72Node):
        self._stats["throttle_events"] += 1
        level = next((name for thresh, _, name in THROTTLE_LEVELS
                      if node.max_die_temp_c >= thresh), "warning")
        if level == "emergency_shutdown":
            self._stats["emergency_shutdowns"] += 1
            logger.critical(f"[Thermal] EMERGENCY SHUTDOWN {node.node_id} max_temp={node.max_die_temp_c}C")
        else:
            logger.warning(f"[Thermal] THROTTLE {node.node_id} level={level} max={node.max_die_temp_c}C throttled={node.throttled_gpus}")

        if self.precooling and node.max_die_temp_c >= 87.0:
            self._stats["precooling_requests"] += 1
            asyncio.create_task(self.precooling.forecast_15min())

        if self.kafka_cb:
            import uuid
            from datetime import datetime, timezone
            asyncio.create_task(self.kafka_cb("colossus.gpu.thermal", {
                "event_id": str(uuid.uuid4()), "node_id": node.node_id,
                "zone_id": node.zone_id, "level": level,
                "max_die_temp_c": node.max_die_temp_c,
                "throttled_gpus": node.throttled_gpus,
                "timestamp": datetime.now(timezone.utc).isoformat()}))

    def stats(self) -> dict: return self._stats


from .node_registry import TARGET_DIE_TEMP_C
