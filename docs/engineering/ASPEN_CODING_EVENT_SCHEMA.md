# Aspen Grove Coding Event Schema

## Purpose

This document defines the event types Aspen Grove should record for coding, CI, refactor, and review workflows.

Aspen Grove is not just for runtime telemetry.
It should also preserve the engineering decision trail.

## Event design principles

- every event should be structured
- every event should be attributable to a task or decision
- every event should separate fact from recommendation where possible
- every event should be compact enough to search and rich enough to audit

## Core fields

Every coding event should include:

- `event_id`
- `event_type`
- `ts`
- `repo`
- `branch`
- `actor`
- `task_id`
- `subsystem`
- `summary`
- `payload`

## Recommended event types

### `code_task_started`
Use when a non-trivial task begins.

### `files_inspected`
Use after the relevant files, tests, workflows, or docs have been inspected.

### `blast_radius_assessed`
Use when dependency impact is mapped.

### `compatibility_risk_found`
Use when a change threatens active imports, tests, simulations, or interfaces.

### `patch_generated`
Use when a concrete implementation patch is produced.

### `ci_failure_diagnosed`
Use when a workflow or test failure has been traced to a probable cause.

### `verification_completed`
Use when tests, smoke runs, or import checks have been completed.

### `pr_split_recommended`
Use when a bundled PR should be decomposed by concern class.

### `reviewer_summary_emitted`
Use when the system emits the final concise explanation a reviewer should see.

## Example event

```json
{
  "event_id": "evt_code_2026_04_28_001",
  "event_type": "ci_failure_diagnosed",
  "ts": "2026-04-28T23:15:00Z",
  "repo": "GlacierEQ/xai-colossus-cooling",
  "branch": "apex-unified-integration-pr7",
  "actor": "chatgpt",
  "task_id": "task_fix_pr10_ci",
  "subsystem": "thermal_orchestrator / CI",
  "summary": "CI likely failing because tests import apex_core while the PR only changes apex-core and also reduces the expected orchestrator API.",
  "payload": {
    "facts": [
      "tests import apex_core.thermal_orchestrator",
      "workflow runs pytest tests/ -v --tb=short",
      "PR patch rewrites apex-core/thermal_orchestrator.py into a smaller sync model"
    ],
    "recommendation": "restore a compatibility layer before deeper runtime redesign"
  }
}
```

## Change-class tags

Each event should optionally include one or more tags:

- `change:security`
- `change:analytics`
- `change:runtime`
- `change:memory`
- `change:ci`
- `change:docs`
- `change:application`

## Risk-level tags

Each event should optionally include:

- `risk:low`
- `risk:medium`
- `risk:high`

## Why this matters

A coding system becomes much more powerful when it remembers:
- what failed
- why it failed
- what was changed
- what was preserved
- what still needs review

That memory is what turns one-off fixes into engineering intelligence.
