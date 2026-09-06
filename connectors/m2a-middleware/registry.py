"""
NodeRegistry — thread-safe node capability store with heartbeat TTL.
Nodes self-register on startup; middleware prunes dead nodes every 30s.
"""

import threading
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)
HEARTBEAT_TTL = 90


@dataclass
class NodeEntry:
    node_id: str
    node_type: str
    pillar: str
    capabilities: List[str]
    domains: List[str]
    latency_class: str
    priority: int = 50
    max_concurrent_requests: int = 10
    status: str = "healthy"
    load_pct: float = 0.0
    last_heartbeat: float = field(default_factory=time.time)
    registered_at: float = field(default_factory=time.time)
    version: str = "1.0.0"
    zone_ids: List[str] = field(default_factory=list)
    thermal_load_mw: float = 0.0
    sensor_count: int = 0
    active_requests: int = 0

    def is_alive(self) -> bool:
        return (time.time() - self.last_heartbeat) < HEARTBEAT_TTL

    def is_available(self) -> bool:
        return self.is_alive() and self.status != "unavailable"

    def effective_load(self) -> float:
        return max(
            self.load_pct,
            (self.active_requests / max(self.max_concurrent_requests, 1)) * 100,
        )


class NodeRegistry:
    def __init__(self, prune_interval: int = 30):
        self._nodes: Dict[str, NodeEntry] = {}
        self._lock = threading.RLock()
        threading.Thread(
            target=self._prune_loop, args=(prune_interval,), daemon=True
        ).start()

    def register(self, entry: NodeEntry) -> None:
        with self._lock:
            entry.registered_at = entry.last_heartbeat = time.time()
            self._nodes[entry.node_id] = entry
            logger.info(
                f"[Registry] + {entry.node_id} pillar={entry.pillar} caps={entry.capabilities}"
            )

    def heartbeat(
        self, node_id: str, status: str = "healthy", load_pct: float = 0.0
    ) -> bool:
        with self._lock:
            if node_id not in self._nodes:
                return False
            n = self._nodes[node_id]
            n.last_heartbeat, n.status, n.load_pct = time.time(), status, load_pct
            return True

    def deregister(self, node_id: str) -> None:
        with self._lock:
            self._nodes.pop(node_id, None)

    def get(self, node_id: str) -> Optional[NodeEntry]:
        with self._lock:
            return self._nodes.get(node_id)

    def all_available(self) -> List[NodeEntry]:
        with self._lock:
            return [n for n in self._nodes.values() if n.is_available()]

    def by_pillar(self, pillar: str) -> List[NodeEntry]:
        with self._lock:
            return [
                n
                for n in self._nodes.values()
                if n.is_available() and (pillar == "all" or n.pillar == pillar)
            ]

    def increment_active(self, node_id: str):
        with self._lock:
            if node_id in self._nodes:
                self._nodes[node_id].active_requests += 1

    def decrement_active(self, node_id: str):
        with self._lock:
            if node_id in self._nodes:
                self._nodes[node_id].active_requests = max(
                    0, self._nodes[node_id].active_requests - 1
                )

    def stats(self) -> dict:
        with self._lock:
            alive = sum(1 for n in self._nodes.values() if n.is_alive())
            pillars = {}
            for n in self._nodes.values():
                pillars[n.pillar] = pillars.get(n.pillar, 0) + 1
            return {
                "total": len(self._nodes),
                "alive": alive,
                "dead": len(self._nodes) - alive,
                "by_pillar": pillars,
            }

    def _prune_loop(self, interval: int):
        while True:
            time.sleep(interval)
            with self._lock:
                dead = [nid for nid, n in self._nodes.items() if not n.is_alive()]
                for nid in dead:
                    logger.warning(f"[Registry] Pruning dead node: {nid}")
                    del self._nodes[nid]
