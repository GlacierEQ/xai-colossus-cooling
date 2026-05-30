# M2A + MCP-to-All Swarm Protocol
## xAI Colossus Cooling | APEX HYPERION-THERMAL-NEXUS

---

## What Is M2A?

**Model-to-Agent (M2A)** is the typed communication contract that governs how orchestrators, specialists, and sensor nodes broadcast requests across the Colossus cooling swarm.

**MCP-to-All** is the selective broadcast transport layer that:
- Receives a typed M2A Request Envelope
- Matches it against the Responder Registry by `intent`, `domain`, `pillar`, and `capabilities`
- Suppresses irrelevant responders (keeps the network quiet)
- Ranks and bundles useful responses into a Response Bundle
- Routes the bundle to Aspen Grove v7 for audit

---

## Schema Files

| File | Purpose |
|---|---|
| `schemas/m2a/request_envelope.json` | Typed broadcast request — intent, domain, pillar, payload |
| `schemas/m2a/response_bundle.json` | Aggregated ranked response from selected responders |
| `schemas/m2a/responder_registry.json` | Node registration — capabilities, domains, pillar, latency class |

---

## Cooling-Specific Intent Map

| Intent | Pillar Scope | Latency SLA | Piston Mode |
|---|---|---|---|
| `request_forecast` | analytics + memory | < 500ms | MICROWAVE + CORE-THINK |
| `request_zone_snapshot` | telemetry + runtime | < 200ms | SHADOW |
| `request_piston_status` | orchestrator + audit | < 200ms | Any |
| `emergency_coordination` | runtime only | **< 50ms** | SUPERNOVA + SONIC |
| `run_export_workflow` | memory + analytics | < 2s | GHOST |
| `sensor_calibration` | telemetry | < 1s | SHADOW |
| `anomaly_investigation` | all pillars | < 1s | MICROWAVE |

---

## Message Flow

```
Orchestrator / Agent
        │
        │  M2A Request Envelope (UUID, intent, domain, pillar, payload)
        ▼
MCP-to-All Middleware
        │
        ├─ Capability match vs Responder Registry
        ├─ Domain + pillar filter
        ├─ Max-responder cap (default: 5)
        ├─ Suppress irrelevant nodes (silent)
        │
        ▼
 Selected Responders (parallel async)
        │
        ▼
Response Bundle (ranked by confidence)
        │
        ├─ → Requesting orchestrator
        └─ → Aspen Grove v7 (audit event)
```

---

## Priority Levels

| Priority | SLA | Use Case |
|---|---|---|
| **P0** | < 50ms | SUPERNOVA emergency blast — thermal runaway prevention |
| **P1** | < 500ms | MICROWAVE predictive surge — 3-step forecast |
| **P2** | < 2s | SHADOW steady-state monitoring tick |
| **P3** | No SLA | GHOST background optimization |

---

## Aspen Grove v7 Audit Events

Every M2A exchange where `aspen_grove_audit: true` records:
- `broadcast_issued` — envelope ID, intent, pillar, timestamp
- `responders_evaluated` — count
- `responders_selected` — list of node IDs
- `responders_suppressed` — count
- `bundle_emitted` — bundle ID, consensus status, latency_ms

This makes every swarm coordination decision fully auditable and replayable.

---

## Implementation Checklist (Issue #11)

- [x] `schemas/m2a/request_envelope.json` — typed request contract
- [x] `schemas/m2a/response_bundle.json` — response aggregation schema
- [x] `schemas/m2a/responder_registry.json` — node registration schema
- [ ] `connectors/m2a_middleware.py` — relevance router + bundle emitter
- [ ] `connectors/responder_registry_loader.py` — registry hydration at startup
- [ ] `dashboard/m2a_bundle_view` — operator UI for bundle/result visualization
- [ ] Aspen Grove audit event integration in `mastermind-fusion/`
