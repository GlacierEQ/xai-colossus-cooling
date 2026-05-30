# CHUNK_POWER_v2/

## Responsibility

This directory owns **one thing**: the per-chunk energy accounting model for
a Colossus-scale GPU cluster. A "chunk" is a logical grouping of racks —
typically 8–32 racks sharing a power distribution unit (PDU) and a cooling
circuit. CHUNK_POWER_v2 translates raw PDU telemetry into structured per-chunk
energy state that the cooling and physics layers can consume.

## What Lives Here

| File | Purpose |
|---|---|
| `chunk_power_model.py` | Core per-chunk draw, PUE, budget, and headroom calculations |
| `chunk_energy_state.json` | Schema: output contract consumed by `connectors/power_state_bridge.py` |
| `chunk_aggregator.py` | Rolls up chunk-level data to zone-level `power_state.json` format |
| `v1_compat.py` | Thin shim re-exporting v1 API surface during migration window |
| `tests/` | Unit tests — every calculation must be covered |

## What Must NOT Live Here

- Thermal control decisions (apex_core)
- Fluid state / nanoparticle properties (connectors/nanosphere_ingest)
- Agent swarm dispatch (mastermind-fusion)
- Grid-level capacity planning (xai-colossus-energy repo)

## Interface Contract

CHUNK_POWER_v2 emits a `chunk_energy_state` dict per chunk with these
fields consumed by `power_state_bridge.PowerStateBridge`:

```json
{
  "chunk_id": "CHUNK-A-001",
  "zone_id": "ZONE-A",
  "rack_ids": ["RACK-001", "RACK-002"],
  "draw_kw": 4800.0,
  "compute_kw": 4200.0,
  "cooling_kw": 600.0,
  "pue": 1.143,
  "headroom_kw": 200.0,
  "timestamp": "2026-05-28T00:00:00Z"
}
```

## v1 → v2 Migration

v1 used a flat dict with no `zone_id` field and mixed imperial/metric units.
v2 enforces:
- All thermal values in SI (Watts, Celsius, kg/s)
- `zone_id` required on every record for bridge compatibility
- `headroom_kw` mandatory (was optional in v1)

`v1_compat.py` provides backward compatibility. Remove it after all callers
have been migrated. Track migration in GitHub Issue tagged `comp/energy`.

## Energy Balance Acceptance Criterion

The Phase 3→4 deployment gate requires CHUNK_POWER_v2 energy balance
within ±1% of measured draw. This is a hard gate criterion — see
[PHASE_3_4_DEPLOYMENT.md](../PHASE_3_4_DEPLOYMENT.md).
