# Phase 3 → 4 Deployment Gate

> **This is a living gate document.** It is never "done." Status advances only
> when every acceptance criterion below is checked and a human operator has
> signed off in the linked GitHub gate issue.
>
> Current status: **PHASE 3 — IN PROGRESS**
> Gate issue: *(create from `.github/ISSUE_TEMPLATE/p0_gate.md`, link here)*

---

## What Phase 3 → 4 Means

| Layer | Phase 3 state | Phase 4 target |
|---|---|---|
| Thermal orchestration | v1.1 — SHADOW/MICROWAVE/SUPERNOVA online | v1.2+ — nanosphere + power_state wired, budget guard active |
| Water plant | Architecture designed, commissioning checklist written | Commissioning checklist 100% checked, sensor telemetry live |
| Digital twin | Simulation harness running | RMS error < 2°C vs live sensor data for 72h continuous |
| CHUNK_POWER_v2 | v1 energy model in use | v2 model active, energy balance within ±1% of measured draw |
| MCP swarm | Issue #11 design closed | `mastermind-fusion/mcp_router.py` live, all 4 request types tested |
| CI / gauntlet | Tests exist | All tests green on every push, gauntlet integration blocking merges |
| Aspen Grove audit | Logs written | 72h clean run: 0 unresolved CRITICAL events |

---

## Hard Acceptance Criteria

Nothing advances to Phase 4 until every row below is ✅.

### CI and Testing
- [ ] `pytest tests/ -v` — 0 failures, 0 errors
- [ ] `pytest tests/test_connectors.py` — all connector + MCP router tests green
- [ ] Gauntlet integration blocking merge on `main` for failing tests

### Thermal Physics
- [ ] Digital twin RMS error < 2°C vs live sensor telemetry (72h continuous run)
- [ ] SUPERNOVA piston fires correctly on injected CRITICAL node (gauntlet scenario)
- [ ] MICROWAVE budget_overrun flag fires when zone draw exceeds budget by >5%
- [ ] Nanosphere conductivity_factor > 1.0 for all active circuits in stub manifest

### Water Plant
- [ ] All items in `water_plant_commissioning.md` §3 checked
- [ ] Pressure profile matches `WATER_PLANT_ARCHITECTURE.md` spec ±2 PSI
- [ ] Primary pump failover tested: secondary comes online within 30s
- [ ] Chemical dosing (pH 7.0–8.5, conductivity < 100 μS/cm) verified

### Energy Accounting
- [ ] CHUNK_POWER_v2 energy balance within ±1% of measured PDU draw
- [ ] `power_state_bridge.PowerStateBridge` loads all 4 zones without warnings
- [ ] PUE < 1.45 sustained for 24h under production load

### Swarm / MCP
- [ ] All 4 MCP request types (`request_forecast`, `request_zone_snapshot`, `request_piston_status`, `emergency_broadcast`) return valid MCPResponse
- [ ] Emergency broadcast writes to `audit_logs/aspen_mcp_events.ndjson` within 100ms
- [ ] Aspen Grove audit log 72h clean (0 unresolved CRITICAL events)

### Compliance / Risk
- [ ] All open `RISK/EJ` issues have documented mitigation plans
- [ ] All open `RISK/LEGAL` issues resolved or escalated
- [ ] `RISK/GRID` issues reviewed by operator and acknowledged

---

## Sign-Off

Gate does not close without this table completed:

| Role | GitHub handle | Date | Signature comment |
|---|---|---|---|
| Operator / Casey | @GlacierEQ | | *(link to comment)* |
| Physics review | | | |
| Water plant review | | | |

---

## Historical Context

The original `PHASE_3_4_DEPLOYMENT.md` (archived below) declared status
"Ready for production deployment and Elon Musk briefing" on 2026-05-12
without linked test evidence or sign-off. That document is now replaced
by this gate. Claims in the original are aspirational metrics, not
verified acceptance criteria.

<details>
<summary>Original 2026-05-12 document (archived)</summary>

```
Date: 2026-05-12 | Status: Live

Key Metrics (claimed, not verified against gate criteria):
- GPU Temp: 35-42C (vs 65C baseline)
- Cost/TFLOP: 0.0282 USD (45% improvement)
- Uptime: 99.95%
- Scaling: 8-28000 nodes linear
```

</details>

---

## Open Gate Issues

*Link every blocking issue here as it is created.*

| Issue | Label | Status |
|---|---|---|
| *(create Phase 3→4 gate issue)* | P0_GATE PHASE_GATE | open |
