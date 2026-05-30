# Codex Task Template

## Purpose

This template defines how coding agents should receive tasks in this repository.

The goal is to improve implementation quality by giving the agent enough structure to preserve architecture, verification, and review discipline.

## Template

```yaml
task:
  objective: "<clear objective>"
  repo: "GlacierEQ/xai-colossus-cooling"
  branch: "<target branch>"
  subsystem: "<subsystem or file group>"
  change_class:
    - security | analytics | runtime | memory | ci | docs | application
  constraints:
    - preserve architecture boundaries
    - preserve active imports where possible
    - keep runtime-critical paths intact
    - split unrelated changes when appropriate
  required_research:
    - inspect affected files
    - inspect dependent imports
    - inspect tests and workflows
    - inspect docs making subsystem claims
  deliverables:
    - patch or file set
    - verification notes
    - risk notes
    - reviewer summary
    - Aspen event
  verification:
    - targeted tests
    - import/path compatibility
    - simulation impact check
    - workflow assumption check
```

## Example

```yaml
task:
  objective: "Repair PR #10 CI without collapsing orchestrator architecture"
  repo: "GlacierEQ/xai-colossus-cooling"
  branch: "apex-unified-integration-pr7"
  subsystem: "thermal_orchestrator / CI"
  change_class:
    - runtime
    - ci
    - memory
  constraints:
    - preserve richer orchestrator surface expected by tests
    - keep Aspen Grove attached, not replacing runtime
    - avoid bundling unrelated docs or application changes
  required_research:
    - inspect tests/test_thermal_core.py
    - inspect simulation/sim_harness.py
    - inspect .github/workflows/ci.yml
    - inspect PR patch for apex-core/thermal_orchestrator.py
  deliverables:
    - compatibility layer or corrected runtime file
    - notes on what CI was failing on
    - notes on remaining architectural risk
    - reviewer summary
    - Aspen event
  verification:
    - pytest thermal core
    - simulation smoke path compatibility
    - import compatibility for apex_core package
```

## Required output shape

Every coding agent response should include:

1. **Findings**
2. **Patch summary**
3. **Verification**
4. **Risks / remaining gaps**
5. **Reviewer note**

## Bottom line

Better inputs produce better code changes.
A coding agent should never operate as a blind patch generator when the repository depends on architecture, CI, and reviewer trust.
