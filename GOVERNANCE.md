# Repo Governance

## Mentat AI Scope

Mentat AI is authorized to **auto-handle** the following without human review:

| Class | Examples | Mentat OK? |
|---|---|---|
| `P1_SWARM` issues | MCP handler stubs, schema additions, agent test coverage | ✅ Yes |
| `P2_DOCS` issues | README updates, docstring passes, architecture doc edits | ✅ Yes |
| `P2_UI` issues | Dashboard widget updates, CLI flag additions | ✅ Yes |
| `MENTAT_OK` label | Any issue explicitly tagged | ✅ Yes |
| Dependency bumps | Non-breaking patch version bumps | ✅ Yes |

Mentat AI **must not** close or merge the following without human sign-off:

| Class | Reason |
|---|---|
| `P0_GATE` issues | Phase gate. Requires operator signature. |
| `HUMAN_GATE` label | Explicitly human-owned. |
| `RISK/EJ` issues | Environmental justice — legal exposure. |
| `RISK/LEGAL` issues | Legal/regulatory. Attorney review required. |
| `RISK/GRID` issues | Grid stability — operator review required. |
| `P1_PHYSICS` issues | Core physics changes require human thermal review. |
| Water plant commissioning | Safety-critical. Human sign-off mandatory. |

## Audit Trail Rule

> **“0 open issues” must never mean “no written specification.”**

Every closed issue must have either:
- A linked commit SHA demonstrating the work was done, OR
- A `wont-fix` comment with documented rationale signed by @GlacierEQ

Mentat AI must post a closing comment with the commit SHA before closing any issue it handled.

## Issue Taxonomy

| Label | Meaning | Who can close |
|---|---|---|
| `P0_GATE` | Phase deployment gate | Human only (operator sign-off required) |
| `P1_SWARM` | Swarm / MCP contract work | Mentat OK |
| `P1_PHYSICS` | Thermal physics / simulation | Human review required |
| `P2_UI` | Dashboard / CLI / API surface | Mentat OK |
| `P2_DOCS` | Documentation | Mentat OK |
| `RISK/EJ` | Environmental justice risk | Human + legal review |
| `RISK/LEGAL` | Legal / regulatory | Human + attorney |
| `RISK/GRID` | Grid stability risk | Operator review |
| `MENTAT_OK` | Explicitly Mentat-safe | Mentat OK |
| `HUMAN_GATE` | Explicitly human-owned | Human only |
| `PHASE_3` | Tracks Phase 3 work | — |
| `PHASE_4` | Tracks Phase 4 targets | — |
| `PHASE_GATE` | Phase gate blockers | Human only |
| `comp/cooling` | Cooling orchestration | — |
| `comp/nanosphere` | Nanosphere / nanofluid | — |
| `comp/energy` | Energy / CHUNK_POWER | — |
| `comp/swarm` | MCP / agent swarm | — |
| `comp/water` | Water plant | — |
| `comp/ci` | CI / gauntlet | — |

## Gate Issue Requirements

Every `P0_GATE` issue must include:
1. Gate identity table (phase, type, version, date opened, linked doc)
2. Acceptance criteria checklist (minimum 5 items, all must be checked before close)
3. Evidence table (criterion → linked commit / test run / sign-off comment)
4. Sign-off block with role, handle, date, and comment link
5. Explicit line: **Mentat MUST NOT close this gate issue.**

Use `.github/ISSUE_TEMPLATE/p0_gate.md` as the starting template.
