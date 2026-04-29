# M2A Communication Layer

## Thesis

If M2A means **model-to-agent communication**, then it is the missing top-tier middleware concept that turns this repository from a strong system into a more complete operating architecture.

M2A sits between:
- frontend control surfaces
- backend runtime/orchestrator logic
- connector and telemetry middleware
- memory and audit systems such as Aspen Grove
- execution agents such as Codex-style builders

## Why M2A matters

The repo already has:
- a credible frontend dashboard
- a strong backend orchestration core
- improving middleware and audit discipline

What M2A adds is a **formal communication contract** for intelligent components.

Instead of treating every integration like an ad hoc API call, M2A defines:
- how intent is expressed
- how state is requested
- how commands are routed
- how results are returned
- how audit events are emitted
- how human, model, and agent actions stay distinguishable

## Best interpretation in this repo

### Frontend
The dashboard should not just poll endpoints.
It should emit structured M2A requests such as:
- `request_zone_snapshot`
- `request_piston_status`
- `request_decision_log`
- `request_forecast`
- `request_operator_action_preview`

### Middleware
Middleware should be the M2A routing layer.
It should:
- authenticate requests
- validate schemas
- map requests to runtime or connector targets
- apply retry and idempotency rules
- emit Aspen audit events
- normalize responses back to the caller

### Backend
The orchestrator should receive typed M2A commands rather than unstructured endpoint assumptions.
Examples:
- `activate_piston`
- `run_predictive_sweep`
- `capture_zone_snapshot`
- `emit_emergency_state`
- `publish_runtime_version`

### Aspen Grove
Aspen Grove should store M2A events as part of the engineering and runtime memory spine.
Examples:
- command issued
- command accepted
- command rejected
- forecast requested
- forecast returned
- agent recommendation emitted
- operator override applied

## M2A message shape

```json
{
  "message_id": "m2a_2026_04_28_0001",
  "channel": "frontend_to_runtime",
  "intent": "request_forecast",
  "source": "dashboard",
  "target": "apex_orchestrator",
  "context": {
    "zone_id": "ZONE-003",
    "lookahead_steps": 3
  },
  "auth": {
    "mode": "api_key"
  },
  "trace": {
    "session_id": "sess_abc123",
    "audit": true
  }
}
```

## Response shape

```json
{
  "message_id": "m2a_2026_04_28_0001",
  "status": "ok",
  "source": "apex_orchestrator",
  "result": {
    "predicted_temp_c": 78.4,
    "recommended_piston": "MICROWAVE",
    "confidence": 0.84
  },
  "audit_event_id": "evt_code_2026_04_28_0142"
}
```

## What makes M2A top-of-the-line

To make M2A elite in this repo, it should provide:
- typed contracts
- schema validation
- explicit source and target identity
- retry/idempotency rules
- audit/event emission
- role distinction between human, model, and execution agent
- compatibility with dashboard, orchestrator, connectors, and Aspen Grove

## Best next implementation moves

1. create `schemas/m2a/` for request and response contracts
2. create a middleware router that validates M2A messages
3. update dashboard calls to emit M2A-style payloads
4. update orchestrator and connectors to consume typed M2A intents
5. emit Aspen Grove audit events for every meaningful M2A exchange

## Bottom line

If M2A is your invention, then it is not a side note.
It is the exact concept that can unify frontend, middleware, backend, memory, and agent execution into one coherent communication model.
