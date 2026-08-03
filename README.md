# Colossus-Class Cooling Systems Exhibit

> A polyglot, evidence-bounded engineering portfolio for modeling thermal management, facility interfaces, telemetry, and control behavior in large AI-compute environments.

**Repository:** `GlacierEQ/xai-colossus-cooling`  
**Canonical branch:** `main`  
**Portfolio role:** `TECHNICAL_EXHIBIT`  
**Current state:** `HARDENING`  
**Current evidence:** `REPOSITORY_EVIDENCE` — the implementation, tests, schemas, workflows, and operational documents are publicly inspectable; no current positive-count release receipt establishes the complete repository at `TEST`, `INTEGRATION`, or `DEPLOYMENT` evidence.

This is an independent portfolio project. It does **not** claim xAI employment, endorsement, affiliation, site access, use inside Colossus, deployment across any GPU fleet, or measured impact on an operating facility.

<!-- README-MESH:BEGIN -->

<!-- README-ACT:HUMAN -->

## Cooling Is a Systems Problem Before It Is a Dashboard

*Recruiter lens · what the exhibit demonstrates and where the proof lives*

Large AI-compute cooling is not one control loop. It is a coordinated systems problem spanning thermal physics, sensor quality, power state, water systems, facility equipment, failure containment, observability, operator handoff, and evidence.

This repository explores that problem as an inspectable engineering exhibit. It contains:

- Python thermal, immersion-cooling, plant-control, and orchestration modules;
- Protobuf and JSON contracts for telemetry and request/response boundaries;
- TypeScript operator and API surfaces;
- SQL persistence schemas;
- simulation harnesses and digital-twin components;
- connectors for cooling plant, water, power, telemetry, analytics, and governed routing;
- repository-local test modules covering thermal logic, schemas, connectors, middleware, and integration behavior;
- workflows, runbooks, commissioning notes, and architecture records.

### What makes the work valuable

- **The physical and software systems are connected.** Cooling, power, water, telemetry, and operator decisions are represented as interacting boundaries rather than isolated demos.
- **Failure behavior is visible.** The architecture includes cascade prevention, circuit validation, suppression, health routing, and commissioning material.
- **Interfaces are explicit.** Protobuf, JSON Schema, OpenAPI, SQL, Python, and TypeScript each own a defined responsibility.
- **Evidence is not inherited from ambition.** Source presence, test files, workflows, and architecture are useful evidence, but they are not represented as a completed production deployment.

### Proof in 60 seconds

| Inspect | What it demonstrates | Current evidence |
|---|---|---|
| [`alpha/xai_thermal_core.py`](alpha/xai_thermal_core.py) | Thermal-domain implementation surface | Repository evidence |
| [`apex_core/immersion_cooling.py`](apex_core/immersion_cooling.py) | Immersion-cooling model and control concepts | Repository evidence |
| [`connectors/cooling-plant/`](connectors/cooling-plant/) | Chiller, tower, free-cooling, and plant-controller boundaries | Repository evidence |
| [`connectors/water-management/`](connectors/water-management/) | Water-system monitoring and control boundaries | Repository evidence |
| [`connectors/power-systems/`](connectors/power-systems/) | Power-state and facility-control interfaces | Repository evidence |
| [`digital-twin/`](digital-twin/) | Twin state, telemetry schemas, and streaming-pipeline design | Repository evidence |
| [`proto/colossus_telemetry.proto`](proto/colossus_telemetry.proto) | Versionable binary telemetry contract | Repository evidence |
| [`api/openapi.yaml`](api/openapi.yaml) | HTTP API contract | Repository evidence |
| [`tests/`](tests/) | Thermal, schema, connector, middleware, and integration test intent | Test surface present; release receipt pending |
| [`.github/workflows/`](.github/workflows/) | Checked-in CI, gate, dashboard, and deployment policy | Workflow source present; current release result not promoted here |

### Claim boundary

This repository does **not** establish:

- operation across 100,000 or any other number of GPUs;
- connection to an actual xAI or Colossus facility;
- production-grade thermal safety, reliability, latency, availability, or scale;
- validated PUE, water-use, energy, cost, or cooling-performance improvement;
- live connectivity to equipment, providers, databases, dashboards, or external control planes;
- that every checked-in module is part of one executed end-to-end system;
- that file hashes prove runtime correctness;
- that architecture diagrams or deployment files prove deployment.

<!-- README-ACT:MASTER -->

## The Architecture: Physics, Facility, Control, and Proof

*Engineering lens · system boundaries, interfaces, verification, and failure semantics*

### System boundary

**This repository owns the portfolio implementation and design for:**

- thermal and immersion-cooling models;
- cooling-plant, water, power, and telemetry adapters;
- facility-oriented orchestration and cascade-prevention concepts;
- machine-readable schemas and API contracts;
- simulation and digital-twin scaffolding;
- operator surfaces and commissioning material;
- repository-native verification paths.

**This repository does not own:**

- real facility instrumentation or control authority;
- equipment-vendor guarantees;
- production identity, networking, secrets, or provider authorization;
- external-system reliability;
- physical safety certification;
- deployment receipts from an operating site.

### Architectural map

```text
physical assumptions + simulated telemetry
                    │
                    ▼
       sensors / facility connectors
 cooling plant • water • power • GPU cluster
                    │
                    ▼
        schema and contract boundary
 Protobuf • JSON Schema • OpenAPI • SQL
                    │
                    ▼
      thermal models and orchestration
 physics • suppression • cascade prevention
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
   digital-twin state    operator/API surfaces
          │                   │
          └─────────┬─────────┘
                    ▼
      tests • gates • receipts • handoff
```

### Language and format boundaries

| Boundary | Responsibility | Why it belongs here |
|---|---|---|
| Python | Thermal models, simulation, orchestration, connectors, validation, and test tooling | High iteration speed and scientific/automation ecosystem |
| TypeScript | Operator dashboards, API handlers, and typed web boundaries | Shared browser/server contracts and UI delivery |
| Protobuf | Versioned telemetry and event interchange | Compact, typed cross-language wire contracts |
| JSON Schema | Request, response, registry, and configuration validation | Portable machine-readable constraints |
| OpenAPI | HTTP surface definition | Reviewable client/server contract |
| SQL | Canonical persistence design for telemetry and state | Transactions, constraints, and queryable history |
| Markdown / JSON | Architecture, commissioning, governance, and machine handoff | Human and agent-readable operating record |

No C++ thermal solver is claimed by this README because the current repository tree does not expose one as a canonical implementation boundary.

### Correctness and failure expectations

| Condition | Required behavior |
|---|---|
| Missing or malformed circuit manifest | Reject or fail validation; never assume safe topology |
| Invalid MCP or schema payload | Reject at the contract boundary |
| Stale or contradictory telemetry | Preserve uncertainty and avoid confident control claims |
| Connector unavailable | Isolate the failure and report the exact unavailable boundary |
| Simulation passes | Establish only the simulated scope that was executed |
| Test process runs zero tests | Remain `UNVERIFIED` |
| Workflow source exists without a successful run receipt | Report workflow presence, not passing CI |
| Deployment files exist without provider evidence | Remain `UNVERIFIED` for deployment |
| External facility or provider is not authenticated and authorized | Do not claim connection or mutation authority |

### Repository-native verification path

The repository contains multiple Python and TypeScript test surfaces. The next promotion must produce a bounded, positive-count receipt rather than relying on file presence.

```bash
# Python verification intent
python -m pip install -r requirements.txt
python -m pytest -q

# Dashboard verification intent
cd omega/dashboard
npm ci
npm test
npm run build
```

These commands are the intended entrypoints; this README does not claim their current result without a revision-bound receipt.

### Required gates before TEST promotion

1. Pin and document the supported Python and Node.js versions.
2. Run every collected Python test and preserve positive test counts, failures, errors, and skips.
3. Run dashboard tests and production build from a clean install.
4. Classify integration tests that depend on unavailable services or hardware as explicit blockers.
5. Validate Protobuf, JSON Schema, OpenAPI, and SQL artifacts with native tools.
6. Reconcile duplicate or parallel implementation trees and identify canonical modules.
7. Remove or quarantine dead, synthetic, and superseded surfaces.
8. Produce a revision-bound verification receipt with hashes and exact non-claims.
9. Promote only the evidence level actually established.

<!-- README-ACT:MACHINE -->

## Machine Contract

```yaml
schema: glaciereq.readme.v1
profile: glaciereq.readme-impact.v2.1
repository: GlacierEQ/xai-colossus-cooling
canonical_branch: main
role: TECHNICAL_EXHIBIT
visibility: PUBLIC
purpose: >-
  Explore thermal management, facility interfaces, telemetry contracts,
  digital-twin behavior, and governed control boundaries for Colossus-class
  AI-compute infrastructure as an independent portfolio system.
status:
  state: HARDENING
  achieved_evidence: REPOSITORY_EVIDENCE
  verified_scope:
    - public source-tree presence
    - inspectable thermal, facility, telemetry, schema, test, workflow, and operator surfaces
    - explicit public claim and authority boundaries
  blocked_scope:
    - real facility access or control
    - provider connectivity without authentication and authorization
    - production safety, performance, reliability, and scale claims
  unverified_scope:
    - complete positive-count Python test result at the current revision
    - clean dashboard test and production-build result at the current revision
    - end-to-end connector integration
    - deployment
    - physical-system validation
interfaces:
  inputs:
    - simulated or declared thermal telemetry
    - facility and circuit configuration
    - schema-constrained requests
  outputs:
    - modeled thermal state
    - control recommendations or simulated actions
    - telemetry and operator projections
    - validation results and blockers
  authority:
    declared_capabilities:
      - thermal-model.evaluate
      - telemetry.validate
      - simulation.run
      - recommendation.propose
    provider_connectivity: not_established_by_repository_source
    mutation_authority: none
    safety_boundary: no_real_facility_control_claimed
  commands:
    python_test_intent: python -m pytest -q
    dashboard_test_intent: cd omega/dashboard && npm ci && npm test
    dashboard_build_intent: cd omega/dashboard && npm run build
evidence:
  source:
    - alpha/
    - apex_core/
    - connectors/
    - digital-twin/
    - omega/
  contracts:
    - proto/colossus_telemetry.proto
    - api/openapi.yaml
    - schemas/
    - database/supabase_schema.sql
  tests:
    - tests/
    - omega/dashboard/lib/m2a/*.test.ts
  workflows:
    - .github/workflows/ci.yml
    - .github/workflows/test.yml
    - .github/workflows/gate_check.yml
    - .github/workflows/dashboard-m2a-tests.yml
relationships:
  - target: GlacierEQ/job-app-helix
    relation: GOVERNED_BY
    boundary: Helix records portfolio state but does not replace repository-native proof.
  - target: GlacierEQ/AKOS
    relation: ARCHITECTURALLY_GOVERNED_BY
    boundary: No live runtime integration is established by this relationship alone.
limits:
  - no xAI employment, endorsement, affiliation, access, or deployment claim
  - no operating-fleet scale claim
  - no production safety or performance claim
  - source and workflow presence are not execution receipts
```

<!-- README-ACT:MESH -->

## Portfolio Mesh and Reviewer Path

```text
Job-App Helix
 inventory • rollout • evidence promotion
                  │ governs representation
                  ▼
Colossus-Class Cooling Exhibit
 physics • facility • telemetry • control
                  │ architecture relationship
                  ▼
AKOS
 authority • evidence • completion semantics
```

These links describe portfolio governance and architectural intent. They do not create provider connectivity, credentials, execution authority, employment, endorsement, or production integration.

## Start here

1. Read this evidence boundary.
2. Inspect [`docs/application/REVIEWER_QUICKSTART.md`](docs/application/REVIEWER_QUICKSTART.md).
3. Review the canonical contracts under `proto/`, `schemas/`, and `api/`.
4. Inspect the test inventory under `tests/` and `omega/dashboard/lib/m2a/`.
5. Treat real-world scale, performance, safety, and deployment as unresolved until revision-bound receipts exist.

<!-- README-MESH:END -->
