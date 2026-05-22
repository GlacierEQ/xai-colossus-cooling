# M2A — Model-to-Agent Swarm Fabric Schemas

This directory contains the three core JSON Schema contracts for the **M2A + MCP-to-All selective broadcast fabric** on the xAI Colossus cooling system.

## Schema Files

| File | Purpose |
|------|---------|
| `request-envelope.schema.json` | Typed broadcast request issued by any node to the fabric |
| `response-bundle.schema.json` | Ranked aggregation of all eligible responder replies |
| `capability-registry.schema.json` | Node self-registration contract for routing eligibility |

## How It Works

```
Issuer (orchestrator/dashboard/agent)
  ↓
  POST request-envelope → MCP-to-All Middleware
    ↓
    Middleware reads capability-registry → evaluates eligibility
    Middleware suppresses irrelevant nodes (max_responders cap)
    Eligible nodes respond with typed payloads
    ↓
    Middleware ranks by rank_score (capability match + latency + confidence)
    Middleware closes bundle at timeout_ms or min_responses reached
    ↓
    response-bundle → Issuer
    response-bundle → Aspen Grove audit event
    response-bundle → InfluxDB (digital twin telemetry)
```

## Cooling-Specific Request Types

| Request Type | Target Pillar | SLA |
|---|---|---|
| `request_forecast` | analytics + memory | 2,000ms |
| `request_zone_snapshot` | telemetry + runtime | 500ms |
| `request_piston_status` | orchestrator + audit | 1,000ms |
| `emergency_broadcast` | runtime only | **500ms** |
| `export_document` | document | 5,000ms |

## Integration Points

- **Aspen Grove:** Every bundle emits an audit event via `GlacierEQ/aspen-grove-operator`
- **InfluxDB:** Bundles written to `m2a_bundles` measurement for Grafana dashboard
- **Digital Twin:** `metadata.total_suppressed` / `total_responded` feeds swarm health KPIs
- **colossus-build-blueprint Phase 5:** Cooling zone IDs map to 48 zones × 25 MW = 1,200 MW thermal load

## Related

- Issue [#11](https://github.com/GlacierEQ/xai-colossus-cooling/issues/11) — M2A implementation tracking
- [colossus-build-blueprint](https://github.com/GlacierEQ/colossus-build-blueprint) — Phase 5 cooling specs
- `connectors/` — MCP connector implementations
- `apex_core/` — APEX orchestrator integration
