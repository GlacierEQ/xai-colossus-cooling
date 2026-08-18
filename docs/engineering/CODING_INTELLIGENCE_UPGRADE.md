# Coding Intelligence Upgrade

## Purpose

This document defines how the repository should evolve from a strong architecture artifact into a stronger engineering system with better coding judgment, review quality, implementation discipline, and measurable capability.

## Core principle

Upgrade coding intelligence by improving the loop, not only the code.

The strongest engineering loop is:

- understand the Operator's full intent;
- reconstruct current state and lineage;
- identify the highest-value bottleneck;
- design the strongest coherent executable advance;
- implement cleanly and deeply;
- integrate complementary capability;
- verify aggressively;
- adversarially attack the result;
- repair;
- record decisions and preserved gains;
- continue upward.

## Coding intelligence stack

### 1. Intent layer
Every non-trivial change should start with:
- problem statement;
- Operator target capability;
- target subsystem;
- constraints and external boundaries;
- expected blast radius;
- prior gains that must survive;
- verification path.

### 2. Structure layer
Every change should preserve or deliberately improve separation between:
- runtime control;
- analytics;
- memory / audit;
- API surface;
- deployment / CI;
- docs / reviewer-facing artifacts.

### 3. Verification layer
Every change should answer:
- what imports or APIs does this affect?
- what tests will fail if wrong?
- what simulations should still run?
- what branches or sibling systems contain useful alternative behavior?
- what integration/failure paths are material?
- what claim state is actually proved?

### 4. Review layer
Every significant change should pass through a 5-node review loop:
- **Router** — identify objective, subsystem, and execution surfaces;
- **Research** — inspect files, dependencies, tests, docs, lineage, and donors;
- **Build** — implement the strongest coherent executable capability tranche;
- **Critic** — check regressions, contradictions, capability suppression, and unverified claims;
- **Breaker** — attack integration, failure, recovery, concurrency, and scale assumptions where relevant.

### 5. Audit layer
Every meaningful change should leave:
- commit message with intent;
- capability delta;
- preserved-gain note when material;
- updated docs when architecture shifts;
- visible verification notes;
- event or audit trail when behavior changes materially.

## Recommended coding standards

### Preserve architecture boundaries
Do not mix runtime orchestration, telemetry persistence, memory integration, analytics queries, and job-application/public positioning casually. Integrate through explicit contracts when the combination produces real leverage.

### Prefer additive integration over destructive replacement
If a new subsystem is useful, compose it cleanly before replacing core behavior. Replacement must prove the new path preserves or exceeds the old path's material capability.

### Keep interfaces stable when tests and simulations depend on them
If a richer runtime API already exists, preserve compatibility or update tests, simulations, and docs together as one coherent change.

### Make security and correctness changes independently verifiable
Security fixes, parameterized queries, import cleanup, and auth hardening should remain reviewable even when they participate in a larger capability advance.

### Build Pro Code elite humanized engineering
Code should demonstrate:
- precise names;
- coherent responsibility boundaries;
- deep mechanisms where depth buys real value;
- explicit contracts;
- useful errors;
- realistic recovery;
- deterministic behavior where appropriate;
- strong observability;
- tests that protect actual behavior;
- no placeholder theater or ornamental AI abstraction.

## Capability upgrades to prioritize

### Immediate / highest leverage
1. compatibility-safe capability expansion;
2. stronger CI/test and simulation alignment;
3. explicit runtime schemas and contracts;
4. adversarial test surfaces per subsystem;
5. cross-repository capability donor mapping where sibling systems can strengthen this one.

### Next frontier
1. event schemas for Aspen integration;
2. forecast audit records;
3. piston effectiveness records;
4. architecture diagrams tied directly to code paths;
5. runtime failure/recovery instrumentation;
6. measurable performance and scale experiments.

### Advanced frontier
1. agent-assisted code review loop;
2. structured design-change proposals;
3. concern-aware merge discipline without capability fragmentation;
4. regression dashboards for runtime integrity;
5. adaptive optimization and recovery loops where justified by the bottleneck.

## Practical coding loop for this repo

### Before changing code
- inspect affected imports;
- inspect tests;
- inspect simulation harness;
- inspect docs that make claims about the subsystem;
- inspect relevant branches, predecessor implementations, and sibling repos;
- bind the full target before selecting the implementation path.

### During change
- maximize coherent capability for the selected checkpoint;
- avoid collapsing richer subsystems without behavior-level proof and explicit authorization;
- preserve runtime-critical paths;
- integrate useful adjacent mechanisms through clear interfaces;
- keep security fixes separable where practical;
- do not optimize for smallest diff, fewest files, or least ambitious scope.

### After change
- run affected and system-level tests;
- check CI assumptions;
- exercise material integration and recovery paths;
- adversarially inspect regression and suppression risk;
- update docs if architecture meaning changed;
- record known limits when claims exceed verification;
- identify the next highest-value bottleneck rather than declaring victory at the first green checkpoint.

## Anti-minimization law

Forbidden as default engineering behavior:

- plan minimally;
- implement the smallest coherent change;
- minimize surface area merely because smaller diffs are easier to review;
- shrink the task after a blocker;
- freeze architecture or capability growth;
- substitute an MVP for the Operator's requested full target;
- remove a distinct implementation because another one looks cleaner;
- equate governance or CI success with product success.

A narrow test harness, experiment, or isolated patch is valid when it is the best instrument for a named uncertainty or defect. It is not permission to redefine the larger system downward.

## Bottom line

Coding intelligence is the ability to:
- choose the right boundary;
- preserve and compound strong system shape;
- invent against the real bottleneck;
- implement deeply enough to matter;
- integrate without erasing strengths;
- verify and attack the result;
- repair failures instead of shrinking objectives;
- keep the repo credible under review;
- continuously move the system toward its strongest coherent form.
