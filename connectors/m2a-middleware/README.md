# M2A Middleware — Relevance Router

Selective broadcast fabric for xAI Colossus cooling swarm.

## Flow
```
broadcast(request)
  ├─ NodeRegistry     — registered nodes + 90s heartbeat TTL
  ├─ RelevanceRouter  — cap / domain / pillar / latency match
  ├─ SuppressionEngine — 90% load cutoff + max_responders
  └─ BundleAggregator — async dispatch + rank + emit
          ├─ Aspen Grove audit
          └─ InfluxDB m2a_bundles
```

## Quick Start
```python
from connectors.m2a_middleware import M2AMiddleware
from connectors.m2a_middleware.registry import NodeEntry

mw = M2AMiddleware()
mw.register_node(NodeEntry(
    node_id="telemetry-zone-01", node_type="telemetry", pillar="telemetry",
    capabilities=["zone_telemetry"], domains=["cooling"], latency_class="realtime",
    priority=90, zone_ids=["zone-01","zone-02"], thermal_load_mw=50.0, sensor_count=142
))

async def dispatch(node, req):
    return {"temp_c": 22.4, "confidence": 0.99}

bundle = asyncio.run(mw.broadcast({
    "request_id": "...", "request_type": "request_zone_snapshot",
    "issued_at": "2026-05-21T21:34:00Z",
    "issuer": {"node_id": "orchestrator-01", "node_type": "orchestrator", "pillar": "all"},
    "target_filter": {"required_capabilities": ["zone_telemetry"], "pillar_scope": "telemetry", "max_responders": 5},
    "sla": {"timeout_ms": 500, "min_responses": 1}
}, dispatch))
print(bundle["status"], bundle["metadata"]["total_responded"])
```

## Rank Scoring
`rank_score = 0.7 × confidence + 0.3 × (1 − latency_ms / max_latency)`

## Cooling SLA Reference
| Request Type | Pillar | timeout_ms |
|---|---|---|
| `request_zone_snapshot` | telemetry | 500 |
| `request_forecast` | analytics | 2000 |
| `emergency_broadcast` | runtime | **500** |
| `request_piston_status` | audit | 1000 |
| `export_document` | document | 5000 |
