"""
BundleAggregator — async concurrent dispatch, rank scoring, Aspen Grove + InfluxDB emit.
Rank formula: rank_score = 0.7 * confidence + 0.3 * (1 - latency_ms / max_latency)
"""
import asyncio, time, uuid, logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from .registry import NodeEntry, NodeRegistry

logger = logging.getLogger(__name__)


class BundleAggregator:
    def __init__(self, registry: NodeRegistry, aspen_grove_client=None, influx_client=None):
        self.registry = registry
        self.aspen_grove = aspen_grove_client
        self.influx = influx_client

    async def collect(self, request: Dict, selected_nodes: List[NodeEntry], suppressed_count: int, dispatch_fn) -> Dict:
        sla = request.get("sla", {})
        timeout_ms = sla.get("timeout_ms", 2000)
        min_responses = sla.get("min_responses", 1)
        t0 = time.monotonic()

        tasks = {n.node_id: asyncio.create_task(self._dispatch(n, request, dispatch_fn)) for n in selected_nodes}
        responses, deadline = [], asyncio.get_event_loop().time() + timeout_ms / 1000.0
        pending = set(tasks.values())

        while pending:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                break
            done, pending = await asyncio.wait(pending, timeout=remaining, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                r = task.result()
                if r:
                    responses.append(r)

        for t in pending:
            t.cancel()

        elapsed_ms = (time.monotonic() - t0) * 1000
        ranked = self._rank(responses)
        status = self._status(ranked, min_responses, len(selected_nodes), timeout_ms, elapsed_ms)
        bundle = self._build(request["request_id"], ranked, status,
                             len(selected_nodes) + suppressed_count, suppressed_count,
                             len(ranked), elapsed_ms, len(ranked) >= min_responses)
        await self._emit_ag(bundle, request)
        await self._emit_influx(bundle)
        return bundle

    async def _dispatch(self, node: NodeEntry, request: dict, dispatch_fn) -> Optional[dict]:
        self.registry.increment_active(node.node_id)
        t0 = time.monotonic()
        try:
            payload = await dispatch_fn(node, request)
            return {"response_id": str(uuid.uuid4()), "responder": {"node_id": node.node_id, "node_type": node.node_type, "pillar": node.pillar},
                    "received_at": datetime.now(timezone.utc).isoformat(), "latency_ms": round((time.monotonic() - t0) * 1000, 2),
                    "rank_score": 0.0, "confidence": payload.get("confidence", 1.0) if payload else 0.0,
                    "payload": payload or {}, "error": None}
        except Exception as e:
            return {"response_id": str(uuid.uuid4()), "responder": {"node_id": node.node_id, "node_type": node.node_type, "pillar": node.pillar},
                    "received_at": datetime.now(timezone.utc).isoformat(), "latency_ms": round((time.monotonic() - t0) * 1000, 2),
                    "rank_score": 0.0, "confidence": 0.0, "payload": {}, "error": {"code": type(e).__name__, "message": str(e)}}
        finally:
            self.registry.decrement_active(node.node_id)

    def _rank(self, responses: List[dict]) -> List[dict]:
        if not responses:
            return []
        max_lat = max(r["latency_ms"] for r in responses) or 1.0
        for r in responses:
            r["rank_score"] = round(0.7 * r["confidence"] + 0.3 * (1.0 - r["latency_ms"] / max_lat), 4)
        return sorted(responses, key=lambda r: -r["rank_score"])

    def _status(self, responses, min_r, total_sel, timeout_ms, elapsed_ms) -> str:
        if not total_sel: return "no_responders"
        if not responses: return "timeout"
        if len(responses) >= min_r: return "complete" if elapsed_ms < timeout_ms * 0.95 else "partial"
        return "partial"

    def _build(self, req_id, responses, status, total_elig, total_supp, total_resp, elapsed_ms, sla_met) -> dict:
        return {"bundle_id": str(uuid.uuid4()), "request_id": req_id,
                "bundled_at": datetime.now(timezone.utc).isoformat(), "status": status, "responses": responses,
                "metadata": {"total_eligible": total_elig, "total_suppressed": total_supp, "total_responded": total_resp,
                             "elapsed_ms": round(elapsed_ms, 2), "sla_met": sla_met,
                             "aspen_grove_event_id": None, "influx_series": "m2a_bundles"}}

    async def _emit_ag(self, bundle: dict, request: dict):
        if not self.aspen_grove: return
        try:
            eid = await self.aspen_grove.log_event({"event_type": "m2a_bundle_closed",
                "request_type": request.get("request_type"), "bundle_id": bundle["bundle_id"],
                "status": bundle["status"], "metadata": bundle["metadata"]})
            bundle["metadata"]["aspen_grove_event_id"] = eid
        except Exception as e:
            logger.warning(f"[Aggregator] Aspen Grove emit failed: {e}")

    async def _emit_influx(self, bundle: dict):
        if not self.influx: return
        try:
            await self.influx.write(measurement="m2a_bundles", tags={"status": bundle["status"]},
                fields={"total_eligible": bundle["metadata"]["total_eligible"],
                        "total_suppressed": bundle["metadata"]["total_suppressed"],
                        "total_responded": bundle["metadata"]["total_responded"],
                        "elapsed_ms": bundle["metadata"]["elapsed_ms"],
                        "sla_met": int(bundle["metadata"]["sla_met"])})
        except Exception as e:
            logger.warning(f"[Aggregator] InfluxDB emit failed: {e}")
