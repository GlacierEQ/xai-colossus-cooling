# Coding Intelligence Upgrade

## Purpose

This document defines how the repository should evolve from a strong architecture artifact into a stronger engineering system with better coding judgment, review quality, and implementation discipline.

## Core principle

Upgrade coding intelligence by improving the loop, not only the code.

The strongest engineering loop is:
- understand intent
- inspect current state
- plan minimally
- implement cleanly
- verify aggressively
- record decisions
- preserve architecture

## Coding intelligence stack

### 1. Intent layer
Every non-trivial change should start with:
- problem statement
- target subsystem
- constraints
- expected blast radius
- verification path

### 2. Structure layer
Every change should preserve separation between:
- runtime control
- analytics
- memory / audit
- API surface
- deployment / CI
- docs / reviewer-facing artifacts

### 3. Verification layer
Every change should answer:
- what imports or APIs does this affect?
- what tests will fail if wrong?
- what simulations should still run?
- what branch or PR risks increase?

### 4. Review layer
Every significant change should pass through a 4-node review loop:
- **Router** — identify subsystem and scope
- **Research** — inspect files, dependencies, tests, and docs
- **Build** — implement smallest coherent change
- **Critic** — check regressions, contradictions, and unverified claims

### 5. Audit layer
Every meaningful change should leave:
- commit message with intent
- updated docs when architecture shifts
- visible verification notes
- event or audit trail when behavior changes materially

## Recommended coding standards

### Preserve architecture boundaries
Do not mix these casually:
- runtime orchestration
- telemetry persistence
- memory integration
- analytics queries
- job-application/public positioning

### Prefer additive integration over destructive replacement
If a new subsystem is useful, attach it cleanly before replacing core behavior.

### Keep interfaces stable when tests and simulations depend on them
If a richer runtime API already exists, either:
- preserve compatibility
- or update tests, simulations, and docs together

### Make security and correctness changes easy to merge independently
Security fixes, parameterized queries, import cleanup, and auth hardening should be separable from architectural rewrites.

## Capability upgrades to prioritize

### Near-term
1. compatibility-safe refactors
2. stronger CI/test alignment
3. explicit runtime schemas
4. review checklists per subsystem

### Medium-term
1. event schemas for Aspen integration
2. forecast audit records
3. piston effectiveness records
4. architecture diagrams tied to code paths

### Long-term
1. agent-assisted code review loop
2. structured design-change proposals
3. merge discipline by concern class
4. regression dashboards for runtime integrity

## Practical coding loop for this repo

### Before changing code
- inspect affected imports
- inspect tests
- inspect simulation harness
- inspect docs that make claims about the subsystem

### During change
- minimize surface area
- avoid collapsing richer subsystems without explicit justification
- preserve runtime-critical paths
- keep security fixes isolated where possible

### After change
- run or target affected tests
- check CI assumptions
- update docs if architecture meaning changed
- record known limits when claims exceed verification

## Bottom line

Coding intelligence is not just writing more code.
It is the ability to:
- choose the right boundary
- preserve system shape
- integrate without erasing strengths
- keep the repo credible under review
