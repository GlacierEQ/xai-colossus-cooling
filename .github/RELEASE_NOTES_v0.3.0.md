# v0.3.0-apex — Release Notes

**Tagged:** 2026-05-21
**Branch:** main (pre-swarm-fabric baseline)

## What's stable at this tag

- `xai-cooling-physics-core.py` — core thermal physics engine (12.4 KB)
- `apex_cli.py` — APEX CLI entrypoint (7.1 KB)
- `xai-cooling-masterswarm-manifest.json` — swarm deployment manifest
- `apex-core/` + `apex_core/` — dual APEX engine modules
- `api/` — REST/WebSocket API layer
- `cells/` — thermal cell zone controllers
- `sensors/` — sensor ingestion pipeline
- `simulation/` — CFD/thermal simulation engine
- `connectors/` — external system connectors
- `dashboard/` — monitoring dashboard (Vercel)
- `database/` — schema + migrations
- `auth/` — authentication layer
- `mastermind-fusion/` — mastermind orchestrator integration
- `CHUNK_POWER_v2/` — power chunking subsystem
- `ASPEN_GROVE_INTEGRATION.md` — aspen-grove-operator integration

## What's coming in v0.4.0

- `schemas/m2a/` — M2A swarm fabric schema contracts (PR #13)
- `connectors/m2a-middleware/` — relevance router
- Aspen Grove audit event emitter
- InfluxDB bundle telemetry writer
- Dashboard M2A composer UI
- Git submodule: `docs/colossus-build-blueprint`

## Cross-links

- [colossus-build-blueprint](https://github.com/GlacierEQ/colossus-build-blueprint) — Phase 5 physical cooling specs
- [Z-BACKUP-mastermind-colossus](https://github.com/GlacierEQ/Z-BACKUP-mastermind-colossus) — Ring -3 codex shadow tree
- Issue #11 — M2A implementation tracking
