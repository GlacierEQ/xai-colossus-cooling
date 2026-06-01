# M2A Completion Sequence

## Objective

Connect the M2A / MCP-to-All system end-to-end and harden it in the shortest clean order.

## Sequence

### Stage 1 — Shared Runtime
1. Keep all `/api/m2a/*` routes on `executeM2ARoute(...)`.
2. Keep `registry-validation.ts` in the runtime path.
3. Keep `aspen-persistence.ts` as the single persistence abstraction.

### Stage 2 — Route Health
1. Add `/api/m2a/health`.
2. Verify registry file path resolution.
3. Verify all route endpoints respond with bundle + audit payloads.

### Stage 3 — Test Gate
1. Add Vitest config.
2. Add router tests.
3. Add registry validation tests.
4. Add route runtime tests.
5. Run in CI on dashboard/config/schema changes.

### Stage 4 — Aspen Sink
1. Prefer connector mode.
2. Fallback to webhook mode.
3. Fallback to offline mode.
4. Preserve identical event shape across all modes.

### Stage 5 — UI Completion
1. Forecast bundle panel.
2. Zone snapshot bundle panel.
3. Piston status bundle panel.
4. Pillar broadcast panel.
5. M2A health status panel as next optional polish.

## Done Definition

- all M2A routes use shared runtime
- registry validation blocks malformed configs
- audit persistence runs through one abstraction
- test suite runs in CI
- dashboard previews live bundle paths

## Memory Bridge

- GitHub is the durable source of truth for code, schemas, tests, and issue trail.
- Aspen Grove is the audit and event memory spine.
- MemoryPlugin is the portable cross-AI memory signal layer.
- Issue #11 is the active implementation ledger for this build.
