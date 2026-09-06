"""
NVL72NodeRegistry
==================
Registry for the 2M GPU cluster hierarchy.

Hierarchy:
  Cluster (2M GPUs total)
    Zone (14 zones x ~143K GPUs)
      Row  (24 rows per zone)
        Rack (24 racks per row)
          NVL72 Node (72 GPUs per node)

Total nodes: 2,000,000 / 72 = ~27,778 NVL72 nodes
GPUs per zone: 2,000,000 / 14 = ~142,857
NVL72 nodes per zone: ~1,984
"""

import threading
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

GPUS_PER_NODE = 72
TOTAL_GPU_TARGET = 2_000_000
NODES_TOTAL = TOTAL_GPU_TARGET // GPUS_PER_NODE  # 27,778
NODES_PER_ZONE = NODES_TOTAL // 14  # 1,984
ZONES = [f"zone-{i:02d}" for i in range(1, 15)]
GPU_MODELS = ["H200", "GB200", "B200"]

THROTTLE_TEMP_C = 83.0
CRITICAL_TEMP_C = 90.0
TARGET_DIE_TEMP_C = 72.0


@dataclass
class GPUState:
    gpu_id: str
    slot: int  # 0-71 within node
    model: str
    die_temp_c: float = 72.0
    memory_temp_c: float = 65.0
    power_w: float = 700.0  # H200 TDP = 700W
    throttle_pct: float = 0.0
    thermal_alert: bool = False
    in_cooldown: bool = False


@dataclass
class NVL72Node:
    node_id: str
    zone_id: str
    rack_id: str
    row_id: str
    gpu_model: str = "H200"
    gpus: List[GPUState] = field(default_factory=list)
    node_power_kw: float = 0.0
    mean_die_temp_c: float = 72.0
    max_die_temp_c: float = 72.0
    throttled_gpus: int = 0
    alert_gpus: int = 0
    status: str = "healthy"  # healthy | degraded | throttling | critical
    last_updated: float = field(default_factory=time.time)
    nvlink_fabric_id: str = ""
    infiniband_port: str = ""

    def __post_init__(self):
        if not self.gpus:
            self.gpus = [
                GPUState(
                    gpu_id=f"{self.node_id}-gpu-{i:02d}", slot=i, model=self.gpu_model
                )
                for i in range(GPUS_PER_NODE)
            ]

    def update_thermals(self):
        if not self.gpus:
            return
        self.mean_die_temp_c = round(
            sum(g.die_temp_c for g in self.gpus) / len(self.gpus), 2
        )
        self.max_die_temp_c = max(g.die_temp_c for g in self.gpus)
        self.throttled_gpus = sum(1 for g in self.gpus if g.throttle_pct > 0)
        self.alert_gpus = sum(1 for g in self.gpus if g.thermal_alert)
        self.node_power_kw = round(sum(g.power_w for g in self.gpus) / 1000, 3)
        if self.alert_gpus > 0:
            self.status = (
                "critical" if self.max_die_temp_c >= CRITICAL_TEMP_C else "throttling"
            )
        elif self.throttled_gpus > 0:
            self.status = "throttling"
        else:
            self.status = "healthy"


class NVL72NodeRegistry:
    def __init__(self):
        self._nodes: Dict[str, NVL72Node] = {}
        self._zone_index: Dict[str, List[str]] = {z: [] for z in ZONES}
        self._lock = threading.RLock()

    def register(self, node: NVL72Node):
        with self._lock:
            self._nodes[node.node_id] = node
            self._zone_index.setdefault(node.zone_id, []).append(node.node_id)

    def get(self, node_id: str) -> Optional[NVL72Node]:
        with self._lock:
            return self._nodes.get(node_id)

    def zone_nodes(self, zone_id: str) -> List[NVL72Node]:
        with self._lock:
            return [
                self._nodes[nid]
                for nid in self._zone_index.get(zone_id, [])
                if nid in self._nodes
            ]

    def all_nodes(self) -> List[NVL72Node]:
        with self._lock:
            return list(self._nodes.values())

    def cluster_snapshot(self) -> dict:
        with self._lock:
            nodes = list(self._nodes.values())
            if not nodes:
                return {}
            total_gpus = len(nodes) * GPUS_PER_NODE
            total_power = round(sum(n.node_power_kw for n in nodes), 2)
            throttled = sum(n.throttled_gpus for n in nodes)
            alerts = sum(n.alert_gpus for n in nodes)
            mean_temp = round(sum(n.mean_die_temp_c for n in nodes) / len(nodes), 2)
            max_temp = max(n.max_die_temp_c for n in nodes)
            return {
                "total_nodes": len(nodes),
                "total_gpus": total_gpus,
                "total_power_kw": total_power,
                "throttled_gpus": throttled,
                "alert_gpus": alerts,
                "mean_die_temp_c": mean_temp,
                "max_die_temp_c": max_temp,
                "healthy_nodes": sum(1 for n in nodes if n.status == "healthy"),
            }

    def build_zone(self, zone_id: str, gpu_model: str = "H200"):
        """Populate a zone with NODES_PER_ZONE NVL72 nodes."""
        for row in range(1, 25):  # 24 rows
            row_id = f"{zone_id}-row-{row:02d}"
            for rack in range(1, 84):  # ~83 racks per row to hit 1984 nodes
                if len(self._zone_index[zone_id]) >= NODES_PER_ZONE:
                    break
                rack_id = f"{zone_id}-rack-{row:02d}{rack:02d}"
                node_id = f"{zone_id}-nvl72-{row:02d}{rack:02d}"
                node = NVL72Node(
                    node_id=node_id,
                    zone_id=zone_id,
                    rack_id=rack_id,
                    row_id=row_id,
                    gpu_model=gpu_model,
                    nvlink_fabric_id=f"nvl-fabric-{zone_id}",
                    infiniband_port=f"ib-{zone_id}-{row:02d}{rack:02d}",
                )
                self.register(node)

    def total_registered(self) -> int:
        with self._lock:
            return len(self._nodes)
