---
name: "P0_GATE — Deployment Gate"
about: "A hard stop that must be resolved before Phase advance. Nothing ships past this gate without sign-off."
title: "[P0_GATE] <gate name>"
labels: ["P0_GATE"]
assignees: []
---

## Gate Identity

| Field | Value |
|-------|-------|
| **Gate name** | *(e.g. Phase 3 → 4 Thermal Validation)* |
| **Phase transition** | Phase __ → Phase __ |
| **Owner** | *(GitHub handle — must be human, not Mentat)* |
| **Target date** | YYYY-MM-DD |
| **Blocking issues** | *(list #N, #N)* |

---

## Acceptance Criteria

All criteria must be checked ✅ before this gate closes. Do not close unless every box is checked.

- [ ] Physics unit tests pass (pytest tests/ -m physics, 0 failures)
- [ ] Connector integration tests pass (pytest tests/test_connectors.py, 0 failures)
- [ ] Digital twin simulation error < 2°C RMS vs sensor telemetry
- [ ] Water plant commissioning checklist complete (water_plant_commissioning.md §3)
- [ ] CHUNK_POWER_v2 energy balance within ±1% of measured draw
- [ ] All P0_GATE sub-issues closed
- [ ] No open RISK/EJ issues without mitigation plan documented
- [ ] Aspen Grove audit log shows 0 unresolved CRITICAL events for 72 hours
- [ ] Human operator sign-off (comment below with ✅ your GitHub handle)

---

## Evidence

<!-- Link CI run, test report, commissioning photos, sign-off screenshots -->

| Evidence type | Link / Notes |
|---|---|
| CI test run | |
| Digital twin RMS error report | |
| Water plant commissioning sign-off | |
| Aspen Grove 72h clean log | |

---

## Mentat Scope

**Mentat MAY auto-close sub-issues tagged `MENTAT_OK` once their CI checks pass.**
**Mentat MUST NOT close this gate issue.** Human sign-off required above.

---

## Notes

<!-- blockers, risks, rollback plan -->
