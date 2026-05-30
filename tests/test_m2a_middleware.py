"""
pytest suite — M2A Middleware | xAI Colossus Cooling | GlacierEQ APEX
10 test cases: registry, router, suppression, integration, emergency SLA
"""
import asyncio, time, uuid, pytest
from connectors.m2a_middleware import M2AMiddleware
from connectors.m2a_middleware.registry import NodeEntry, NodeRegistry
from connectors.m2a_middleware.router import RelevanceRouter
from connectors.m2a_middleware.suppression import SuppressionEngine


def node(node_id="tz-01", pillar="telemetry", caps=None, domains=None, latency="realtime", priority=80, load=10.0):
    return NodeEntry(node_id=node_id, node_type="telemetry", pillar=pillar,
                     capabilities=caps or ["zone_telemetry"], domains=domains or ["cooling"],
                     latency_class=latency, priority=priority, load_pct=load)

def req(rtype="request_zone_snapshot", pillar="telemetry", caps=None, max_r=10, timeout=500):
    return {"request_id": str(uuid.uuid4()), "request_type": rtype, "issued_at": "2026-05-21T21:34:00Z",
            "issuer": {"node_id": "orch-01", "node_type": "orchestrator", "pillar": "all"},
            "target_filter": {"required_capabilities": caps or [], "pillar_scope": pillar,
                              "max_responders": max_r, "latency_class": "realtime"},
            "sla": {"timeout_ms": timeout, "min_responses": 1}}

async def dispatch(n, r): await asyncio.sleep(0.01); return {"temp_c": 22.4, "confidence": 0.95}


class TestNodeRegistry:
    def test_register(self):
        reg = NodeRegistry(); reg.register(node()); assert reg.get("tz-01") is not None

    def test_heartbeat(self):
        reg = NodeRegistry(); reg.register(node()); t = reg.get("tz-01").last_heartbeat
        time.sleep(0.05); reg.heartbeat("tz-01", "healthy", 20.0)
        assert reg.get("tz-01").last_heartbeat > t

    def test_by_pillar(self):
        reg = NodeRegistry(); reg.register(node("n1", pillar="telemetry")); reg.register(node("n2", pillar="analytics"))
        assert len(reg.by_pillar("telemetry")) == 1; assert len(reg.by_pillar("all")) == 2


class TestRelevanceRouter:
    def test_cap_match(self):
        reg = NodeRegistry(); reg.register(node(caps=["zone_telemetry"]))
        assert len(RelevanceRouter(reg).evaluate(req(caps=["zone_telemetry"]))) == 1

    def test_cap_mismatch(self):
        reg = NodeRegistry(); reg.register(node(caps=["audit_log"]))
        assert len(RelevanceRouter(reg).evaluate(req(caps=["zone_telemetry"]))) == 0

    def test_latency_filter(self):
        reg = NodeRegistry(); reg.register(node("slow", latency="batch")); reg.register(node("fast", latency="realtime"))
        eligible = RelevanceRouter(reg).evaluate(req())
        ids = [n.node_id for n in eligible]
        assert "fast" in ids; assert "slow" not in ids


class TestSuppressionEngine:
    def test_max_responders(self):
        eng = SuppressionEngine()
        nodes = [node(f"n{i}") for i in range(10)]
        sel, sup = eng.apply(nodes, req(max_r=3))
        assert len(sel) == 3; assert sup == 7

    def test_overloaded_dropped(self):
        eng = SuppressionEngine(load_cutoff=90.0)
        sel, sup = eng.apply([node("ok", load=20.0), node("bad", load=95.0)], req())
        assert any(n.node_id == "ok" for n in sel); assert sup == 1


class TestIntegration:
    def test_full_broadcast(self):
        mw = M2AMiddleware(); mw.register_node(node())
        b = asyncio.run(mw.broadcast(req(caps=["zone_telemetry"]), dispatch))
        assert b["status"] in ("complete", "partial"); assert b["metadata"]["total_responded"] >= 1
        assert 0.0 <= b["responses"][0]["rank_score"] <= 1.0

    def test_no_eligible(self):
        mw = M2AMiddleware()
        b = asyncio.run(mw.broadcast(req(caps=["nonexistent"]), dispatch))
        assert b["status"] == "no_responders"

    def test_emergency_sla(self):
        mw = M2AMiddleware()
        for i in range(5): mw.register_node(node(f"rt-{i}", pillar="runtime", caps=["emergency_response"]))
        b = asyncio.run(mw.broadcast(req(rtype="emergency_broadcast", pillar="runtime",
                                        caps=["emergency_response"], timeout=500), dispatch))
        assert b["metadata"]["sla_met"] is True; assert b["metadata"]["elapsed_ms"] < 500
