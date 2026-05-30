# Open Issues Registry

> Auto-generated reference. Ground truth is GitHub Issues. This file documents
> issue intent so spec is never lost even if the issue tracker is empty.

## P0_GATE

### [#15] Phase 3 → 4 Deployment Gate
https://github.com/GlacierEQ/xai-colossus-cooling/issues/15
- Blocks production deployment
- Requires @GlacierEQ operator sign-off
- Mentat MUST NOT close

---

## P1_SWARM

### [#16] Wire MCP router into APEX tick loop
https://github.com/GlacierEQ/xai-colossus-cooling/issues/16
- Mentat OK
- Blocks swarm live operation

### [PENDING] MCP schema JSON validation on inbound requests
- Validate every `MCPRequest` against `schemas/mcp_request.json` before dispatch
- Reject with `ResponseStatus.ERROR` and structured reason if schema fails
- Mentat OK

### [PENDING] Aspen Grove async flush — non-blocking audit writes
- Current `_log_event` does synchronous file I/O on every dispatch
- Replace with asyncio queue + background writer task
- Target: < 5ms overhead per dispatch
- Mentat OK

---

## P1_PHYSICS

### [PENDING] Digital twin 72h validation run
- Run `simulation/` harness against live or recorded sensor data
- Must achieve RMS error < 2°C for 72 continuous hours
- Gate criterion for Issue #15
- Human review required before closing

### [PENDING] SUPERNOVA piston gauntlet scenario
- Add gauntlet scenario: inject CRITICAL node at tick 10, verify SUPERNOVA fires by tick 11
- Must be green before Phase 4 gate closes
- Mentat OK for implementation, human review for physics correctness

---

## RISK/EJ

### [PENDING] Memphis/Southaven community impact — emissions mitigation plan
- Document mitigation plan for unpermitted gas turbine ops (Earthjustice filing)
- Map xAI Colossus power sources, emission inventory, community exposure radius
- Require legal review before closing
- Labels: RISK/EJ, RISK/LEGAL, HUMAN_GATE

### [PENDING] Water plant discharge compliance — Clean Water Act Section 402
- Cooling tower blowdown volume and chemical load must be documented
- Requires NPDES permit review or exemption documentation
- Labels: RISK/EJ, RISK/LEGAL, HUMAN_GATE

---

## RISK/GRID

### [PENDING] 1GW+ grid stress — MISO interconnect capacity acknowledgment
- Colossus 2 projected draw requires MISO transmission study
- Document current interconnect status, headroom, and contingency
- Labels: RISK/GRID, HUMAN_GATE

---

## P2_DOCS

### [PENDING] WATER_PLANT_ARCHITECTURE.md — add P&ID diagram reference
- Current doc has text descriptions of piping topology
- Add ASCII P&ID or link to external diagram
- Mentat OK

### [PENDING] API/ directory — add OpenAPI spec stub
- `api/` exists but has no spec file
- Add `api/openapi.yaml` with at least MCP endpoint stubs
- Mentat OK
