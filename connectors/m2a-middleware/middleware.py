"""
M2AMiddleware — top-level broadcast orchestrator.
Route → Suppress → Dispatch → Aggregate → Emit
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Callable
from .registry import NodeRegistry, NodeEntry
from .router import RelevanceRouter
from .suppression import SuppressionEngine
from .aggregator import BundleAggregator

logger = logging.getLogger(__name__)


class M2AMiddleware:
    """
    Primary entrypoint. Usage:
        mw = M2AMiddleware()
        mw.register_node(NodeEntry(...))
        bundle = await mw.broadcast(request_envelope, dispatch_fn)
    """

    def __init__(
        self, aspen_grove_client=None, influx_client=None, load_cutoff: float = 90.0
    ):
        self.registry = NodeRegistry()
        self.router = RelevanceRouter(self.registry)
        self.suppression = SuppressionEngine(load_cutoff=load_cutoff)
        self.aggregator = BundleAggregator(
            self.registry, aspen_grove_client, influx_client
        )
        logger.info(
            "[M2AMiddleware] Initialized — APEX Colossus Cooling Swarm Fabric v0.1.0"
        )

    async def broadcast(
        self, request: Dict[str, Any], dispatch_fn: Callable
    ) -> Dict[str, Any]:
        rid = request.get("request_id", str(uuid.uuid4()))
        rtype = request.get("request_type", "unknown")
        logger.info(f"[M2A] ► broadcast START {rid} type={rtype}")

        eligible = self.router.evaluate(request)
        if not eligible:
            logger.warning(f"[M2A] No eligible nodes for {rtype}")
            return self._empty_bundle(rid, "no_responders")

        selected, suppressed = self.suppression.apply(eligible, request)
        logger.info(
            f"[M2A] eligible={len(eligible)} selected={len(selected)} suppressed={suppressed}"
        )

        bundle = await self.aggregator.collect(
            request, selected, suppressed, dispatch_fn
        )
        logger.info(
            f"[M2A] ■ bundle DONE {rid} status={bundle['status']} "
            f"responded={bundle['metadata']['total_responded']} elapsed={bundle['metadata']['elapsed_ms']:.1f}ms"
        )
        return bundle

    def register_node(self, entry: NodeEntry):
        self.registry.register(entry)

    def heartbeat(self, node_id: str, status: str = "healthy", load_pct: float = 0.0):
        return self.registry.heartbeat(node_id, status, load_pct)

    def stats(self) -> dict:
        return self.registry.stats()

    @staticmethod
    def _empty_bundle(request_id: str, status: str) -> dict:
        return {
            "bundle_id": str(uuid.uuid4()),
            "request_id": request_id,
            "bundled_at": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "responses": [],
            "metadata": {
                "total_eligible": 0,
                "total_suppressed": 0,
                "total_responded": 0,
                "elapsed_ms": 0.0,
                "sla_met": False,
                "aspen_grove_event_id": None,
                "influx_series": "m2a_bundles",
            },
        }
