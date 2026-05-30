# PR #10 Decision Memo

## Current state

PR #10 is currently open, unmerged, and not mergeable.

## Main finding

The branch contains valuable work, but it currently bundles multiple concern classes into one review lane:

- security fixes
- analytics/query correctness changes
- Aspen Grove memory integration
- orchestrator/runtime compatibility work

That makes the branch harder to review and weaker as a canonical architecture signal.

## Recommended decision

Treat PR #10 as an integration workbench, not the final review surface.

### Keep and preserve
- API authentication hardening
- analytics query parameterization
- Aspen Grove attachment work
- runtime compatibility restoration

### Do not assume yet
- final merge shape
- final orchestrator architecture
- final runtime/memory boundary implementation
- final proof of production readiness

## Best split path

### Track A — Security / correctness
- API key validation
- empty-key bypass prevention
- analytics query safety

### Track B — Aspen Grove spine
- memory and audit attachment
- event schemas
- forecast and piston audit hooks

### Track C — Runtime review
- orchestrator compatibility
- async/sync interface discipline
- simulation and test alignment

## Why this is the strongest move

This repo is strongest when:
- main stays clean for reviewer and executive skim
- architecture docs stay ahead of implementation ambiguity
- runtime boundaries remain explicit
- unrelated concern classes do not get forced through one PR

## Bottom line

PR #10 contains useful engineering work, but the intelligent move is to preserve the good pieces, reduce bundled scope, and keep the repository legible under serious technical review.
