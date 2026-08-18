# Agent Execution Contract

## Purpose

This contract defines the shared operating model for cooperating intelligence layers while preserving Operator authority and repository capability.

- **ChatGPT** — architecture judgment, routing, contradiction detection, reviewer-facing synthesis
- **Aspen Grove** — memory spine, audit trail, decision history, retrieval of prior patterns
- **Codex / coding agent** — implementation, patch generation, test repair, CI fixes, file-level execution

No layer owns the project. No assistant, memory system, repository, or policy may silently redefine the Operator's target.

The goal is not just to write more code. The goal is to produce **Pro Code elite humanized engineering** that preserves architecture, raises capability, improves reliability, compounds useful systems, and remains credible under upper-level review.

## Shared loop

Every non-trivial coding task should follow this sequence:

1. **Intent**
   - bind the Operator's full target;
   - identify subsystem and desired capability;
   - identify constraints without converting them into a smaller objective;
   - identify expected blast radius and preservation requirements.

2. **Research**
   - inspect affected files;
   - inspect imports and interface dependencies;
   - inspect tests and simulation harnesses;
   - inspect docs that make claims about the subsystem;
   - inspect related branches, predecessors, and sibling systems for capability donors.

3. **Build**
   - implement the **strongest coherent executable capability tranche**;
   - preserve compatibility where it retains useful behavior;
   - integrate complementary mechanisms when they compound value;
   - keep security fixes and architecture rewrites separable where that improves reviewability without weakening the target.

4. **Critic**
   - check regressions;
   - check contradictions;
   - check architecture weakening;
   - check capability suppression;
   - check whether claims exceed evidence;
   - check whether a smaller/easier implementation displaced the Operator's actual target.

5. **Audit**
   - record what changed;
   - record why it changed;
   - record capability gained and preserved;
   - record how it was verified;
   - record known limits or remaining gaps.

6. **Publish / Continue**
   - commit with clear intent;
   - update docs when architecture meaning changes;
   - attach reviewer notes or event log where appropriate;
   - continue upward until the coherent checkpoint is complete or a real surviving blocker exists.

## Role boundaries

### ChatGPT contributes
- intent parsing;
- subsystem selection;
- blast-radius assessment;
- architecture and reviewer judgment;
- PR split recommendations;
- contradiction and risk detection.

### Aspen Grove contributes
- decision memory;
- code-change history;
- verification history;
- schema/version lineage;
- cross-task retrieval of prior lessons.

### Codex contributes
- file inspection;
- implementation;
- patch generation;
- refactors;
- CI repair;
- test alignment.

These are contribution roles, not ownership grants.

## Non-negotiable rules

### 1. Preserve architecture boundaries
Do not casually mix runtime orchestration, memory/audit integration, telemetry persistence, analytics queries, API auth surfaces, and public/application-facing docs. Compose them through explicit contracts when cross-boundary integration creates value.

### 2. Favor additive compounding over destructive replacement
When a new subsystem is useful, attach or compose it cleanly before replacing core behavior. Replacement requires behavior-level comparison and preservation of unique capability.

### 3. Keep interfaces stable when useful dependents rely on them
If an interface is active in tests, workflows, simulations, or sibling systems, preserve compatibility or update all dependent surfaces coherently.

### 4. Split by concern when it improves review without shrinking capability
Separate security, analytics, orchestration, memory/audit, and packaging work when that makes verification stronger. PR boundaries are review mechanics, not product boundaries.

### 5. Audit meaningful decisions
If a change affects behavior, architecture, CI, reviewer posture, system capability, or lineage, leave an explicit decision record.

### 6. Never optimize for smallest scope by default
Do not instruct agents to:
- implement the smallest coherent change;
- minimize surface area as a general quality rule;
- freeze architecture or capability growth;
- shrink the task after a failure;
- replace a full system target with an MVP merely for easier verification.

A narrow experiment is allowed only when it resolves a named uncertainty while the full target remains preserved.

## Change classes

### Class A — Direct improvement candidates
- import cleanup;
- parameterized queries;
- auth hardening;
- typo/doc fixes;
- compatibility shims;
- bounded defect repair.

### Class B — Structural capability changes
- runtime API changes;
- orchestrator evolution;
- connector rewiring;
- workflow changes;
- simulation contract changes.

### Class C — Architecture-sensitive capability changes
- runtime model replacement;
- telemetry-path redesign;
- memory/runtime integration;
- public claim changes;
- cross-repository composition;
- retirement of an existing mechanism.

Class C requires deeper comparison and preservation, not automatic avoidance.

## Required preflight checklist

Before changing code:
- What full capability is the Operator asking for?
- What files are affected?
- What imports and external consumers depend on this?
- What tests or workflows will fail if this is wrong?
- What docs will become inaccurate?
- What prior branches or sibling systems contain capability worth preserving?
- Is this a security fix, runtime evolution, integration, or several concerns?
- What would constitute an artificial narrowing of the target?

## Required post-change checklist

After changing code:
- What capability became true?
- What was verified?
- What remains unverified?
- What prior capability was preserved?
- What architectural boundary was strengthened?
- What adversarial test was applied?
- What follow-up frontier remains?
- What should a reviewer know immediately?

## Bottom line

The repo should optimize for **engineering judgment expressed as working power**:

- stronger boundaries;
- deeper mechanisms;
- cleaner review lanes;
- stronger compatibility discipline;
- clearer audit trails;
- realistic failure handling;
- compound integration;
- elite humanized maintainability;
- code that becomes more capable and easier to trust, not merely smaller or larger.
