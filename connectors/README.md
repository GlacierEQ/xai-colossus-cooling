# connectors/

This directory owns all **inbound data translation** for `xai-colossus-cooling`.
Each connector is a thin, stateless adapter between an upstream repo's output format
and the internal cooling domain model. Connectors MUST NOT contain business logic —
that lives in `apex_core/` and `simulation/`.

## Connectors

| File | Upstream Source | What It Does |
|---|---|---|
| `nanosphere_ingest.py` | `xai-colossus-nanosphere` | Reads `circuit_manifest.json`, maps circuit IDs to zones, emits fluid replacement alerts |
| `power_state_bridge.py` | `xai-colossus-energy` | Parses `power_state.json`, produces per-zone `ZoneThermalBudget` for orchestrator |

## ID Alignment Rule

**One source of truth for circuit → zone mapping: `CIRCUIT_TO_ZONE` in `nanosphere_ingest.py`.**

- `nanosphere_ingest.py` owns the `circuit_id → zone_id` map.
- `power_state_bridge.py` consumes `zone_id` values — it never invents them.
- All other connectors added in future must import from `nanosphere_ingest.CIRCUIT_TO_ZONE`.

## Adding a New Connector

1. Create `connectors/your_source_bridge.py`.
2. Implement a class with `.load_from_dict(data: dict)` as the standard entry point.
3. Return typed dataclasses — never raw dicts — to the orchestration layer.
4. Add an entry to this README table.
5. Add a test in `tests/test_connectors.py`.

## What Must NOT Live Here

- Thermal control logic
- PID setpoint calculations
- Swarm agent dispatch
- APEX manifest reads

Those belong in `apex_core/thermal_orchestrator.py` and `mastermind-fusion/`.
