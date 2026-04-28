# Agent Execution Contract

## Purpose

This contract defines the shared operating model for three cooperating intelligence layers:

- **ChatGPT** — architecture judgment, routing, contradiction detection, reviewer-facing synthesis
- **Aspen Grove** — memory spine, audit trail, decision history, retrieval of prior patterns
- **Codex / coding agent** — implementation, patch generation, test repair, CI fixes, file-level execution

The goal is not just to write more code.
The goal is to produce code changes that preserve architecture, improve reliability, and remain credible under upper-level review.

## Shared loop

Every non-trivial coding task should follow this sequence:

1. **Intent**
   - define the problem
   - identify subsystem
   - identify constraints
   - identify expected blast radius

2. **Research**
   - inspect affected files
   - inspect imports and interface dependencies
   - inspect tests and simulation harnesses
   - inspect docs that make claims about the subsystem

3. **Build**
   - implement the smallest coherent change
   - preserve compatibility where practical
   - keep security fixes and architecture rewrites separable

4. **Critic**
   - check regressions
   - check contradictions
   - check architecture weakening
   - check whether claims exceed evidence

5. **Audit**
   - record what changed
   - record why it changed
   - record how it was verified
   - record known limits or remaining gaps

6. **Publish**
   - commit with clear intent
   - update docs when architecture meaning changes
   - attach reviewer notes or event log where appropriate

## Role ownership

### ChatGPT owns
- intent parsing
- subsystem selection
- blast-radius assessment
- architecture and reviewer judgment
- PR split recommendations
- contradiction and risk detection

### Aspen Grove owns
- decision memory
- code-change history
- verification history
- schema/version lineage
- cross-task retrieval of prior lessons

### Codex owns
- file inspection
- implementation
- patch generation
- refactors
- CI repair
- test alignment

## Non-negotiable rules

### 1. Preserve architecture boundaries
Do not casually mix:
- runtime orchestration
- memory / audit integration
- telemetry persistence
- analytics queries
- API auth surfaces
- public/application-facing docs

### 2. Favor additive integration over destructive replacement
When a new subsystem is useful, attach it cleanly before replacing core behavior.

### 3. Keep interfaces stable when tests and simulations depend on them
If an interface is active in tests, workflows, or simulations, either preserve compatibility or update all dependent surfaces together.

### 4. Split by concern class
Prefer separate PR tracks for:
- security fixes
- analytics/query correctness
- orchestration/runtime changes
- memory/audit integration
- docs/application packaging

### 5. Audit meaningful decisions
If a change affects behavior, architecture, CI, or reviewer posture, it should leave an explicit decision record.

## Change classes

### Class A — Safe merge candidates
- import cleanup
- parameterized queries
- auth hardening
- typo/doc fixes
- compatibility shims

### Class B — Review-required structural changes
- runtime API changes
- orchestrator rewrites
- connector rewiring
- workflow changes
- simulation contract changes

### Class C — Architecture-sensitive changes
- replacing async runtime with sync model
- removing telemetry paths
- attaching memory systems to runtime loops
- changing public claims about capability or validation

## Required preflight checklist

Before changing code:
- What files are affected?
- What imports depend on this?
- What tests or workflows will fail if this is wrong?
- What docs will become inaccurate?
- Is this a security fix, a runtime rewrite, or both?

## Required post-change checklist

After changing code:
- What was verified?
- What remains unverified?
- What architectural boundary was preserved?
- What follow-up change is still needed?
- What should a reviewer know immediately?

## Bottom line

The repo should optimize for engineering judgment.

That means:
- better boundaries
- cleaner review lanes
- stronger compatibility discipline
- clearer audit trails
- code that becomes easier to trust, not just larger.
