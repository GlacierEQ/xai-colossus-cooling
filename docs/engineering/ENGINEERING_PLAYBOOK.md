# Engineering Playbook

## Purpose

This playbook unifies the repository's engineering rules into one operator manual.

It is meant to guide:
- ChatGPT as architecture router and critic
- Aspen Grove as memory and audit spine
- Codex or coding agents as implementation layer
- human reviewers as final decision-makers

## Operating goal

Build changes that are:
- architecturally coherent
- reviewable in small pieces
- compatible with existing tests and simulations
- auditable after the fact
- credible for upper-level technical review

## Core loop

Every non-trivial change follows:

1. **Intent**
2. **Research**
3. **Build**
4. **Critic**
5. **Audit**
6. **Publish**

## Decision map

### ChatGPT / architecture layer
Owns:
- problem framing
- subsystem selection
- blast-radius assessment
- contradiction detection
- PR split recommendations
- reviewer summary

### Aspen Grove / memory layer
Owns:
- event memory
- decision history
- code-change history
- prior-failure retrieval
- schema and version lineage

### Codex / execution layer
Owns:
- implementation
- patch generation
- CI repair
- refactors
- compatibility shims
- test alignment

## Change handling rules

### Rule 1 — Separate concern classes
Prefer separate tracks for:
- security fixes
- analytics fixes
- runtime/orchestrator changes
- memory or Aspen integration
- docs and application packaging

### Rule 2 — Preserve active interfaces
If tests, simulations, or imports depend on an interface, preserve compatibility or update all dependents together.

### Rule 3 — Attach before replacing
When adding a useful subsystem, attach it cleanly before replacing core runtime behavior.

### Rule 4 — Keep runtime-critical paths explicit
Emergency behavior, telemetry paths, and orchestrator boundaries should not become ambiguous inside convenience rewrites.

### Rule 5 — Record meaningful decisions
If a change affects CI, architecture, behavior, reviewer posture, or merge strategy, record the decision.

## Review checklist

Before coding:
- what subsystem is affected?
- what imports depend on it?
- what tests or workflows touch it?
- what docs become stale if it changes?
- is this additive, replacement, or compatibility work?

After coding:
- what was verified?
- what remains unverified?
- what boundary was preserved?
- what should be merged separately?
- what should a reviewer know immediately?

## PR discipline

### Good PR shape
A good PR should usually represent one of these:
- one security fix
- one analytics fix
- one orchestrator/runtime adjustment
- one compatibility layer
- one docs/application packaging change

### Bad PR shape
Avoid PRs that combine:
- security fixes + runtime rewrites
- docs packaging + behavior changes + CI fixes
- memory integration + orchestrator replacement + analytics edits

## CI discipline

CI should protect:
- import compatibility
- runtime interface stability
- smoke-test viability
- docs drift for public claims

See `docs/engineering/CI_UPGRADE_CHECKLIST.md`.

## Aspen Grove discipline

Every real engineering task should generate audit events for:
- task start
- files inspected
- blast radius assessed
- compatibility risk found
- patch generated
- verification completed
- split recommendation if needed
- reviewer summary

See `docs/engineering/ASPEN_CODING_EVENT_SCHEMA.md`.

## Bottom line

The repository should scale by improving the engineering loop.

That means:
- cleaner boundaries
- better audit memory
- stronger CI protection
- smaller merge lanes
- better reviewer trust
