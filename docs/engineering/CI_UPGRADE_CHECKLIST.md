# CI Upgrade Checklist

## Purpose

This checklist defines CI protections that mirror the engineering contract.

The goal is not only to catch syntax failures.
The goal is to catch architecture drift, compatibility breaks, and review-surface inconsistencies early.

## Priority CI protections

### 1. Import compatibility check
Protect against:
- package path mismatches
- renamed modules without compatibility shims
- broken simulation imports
- test imports drifting from repo structure

#### Example targets
- `apex_core.thermal_orchestrator`
- simulation harness imports
- connector imports
- package init surface

### 2. Runtime boundary check
Protect against:
- replacing core orchestrator behavior accidentally
- collapsing async interfaces into smaller incompatible sync models
- mixing memory/audit logic directly into runtime-critical code without review

#### Minimum review questions
- did a runtime interface disappear?
- did a class or method expected by tests disappear?
- was Aspen attached or did it replace core behavior?

### 3. Docs drift check
Protect against:
- README claims drifting away from current repo shape
- architecture docs not matching actual file/module structure
- application-facing claims outpacing what is verified

#### Minimum drift checks
- referenced files exist
- core doc paths resolve
- application docs exist in expected locations

## Recommended CI stages

### Stage A — Import and package surface
- verify key imports resolve
- verify compatibility packages exist where expected
- verify simulation harness imports still work

### Stage B — Targeted tests
- run thermal core tests
- run focused sensor tests where present
- fail early on import/interface regressions

### Stage C — Simulation smoke
- run a small simulation scenario
- verify harness startup path still works
- do not require production credentials for smoke path

### Stage D — Docs integrity
- verify architecture and application docs referenced by README exist
- optionally validate key markdown paths and repo references

## Suggested checks

### Import compatibility script
Should verify imports such as:
- `from apex_core.thermal_orchestrator import APEXThermalOrchestrator`
- `from apex_core.thermal_orchestrator import CoolingZone, ThermalNode`
- simulation harness import path

### Runtime compatibility assertions
Should verify the orchestrator still exposes:
- `register_zone`
- `tick_cycle`
- `run`
- piston classes expected by tests

### Docs integrity assertions
Should verify these files exist:
- `docs/application/EXECUTIVE_SUMMARY.md`
- `docs/application/STATEMENT_OF_EXCEPTIONAL_WORK.md`
- `docs/application/ROLE_FIT.md`
- `docs/application/ROADMAP.md`
- `docs/application/KNOWN_LIMITS_AND_NEXT_STEPS.md`
- `docs/architecture/aspen-grove-v7-integration.md`
- `docs/audits/repo-strength-audit-2026-04-28.md`

## Failure handling rule

When CI fails, the review output should identify failure class:
- import/path failure
- interface compatibility failure
- test logic failure
- simulation failure
- docs drift failure

That makes fix strategy much faster.

## Bottom line

Good CI should protect:
- compatibility
- boundaries
- simulations
- reviewer trust

It should not just say "tests failed."
It should tell us what class of engineering mistake happened.
