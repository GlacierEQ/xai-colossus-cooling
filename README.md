# Colossus Cooling Simulation and Control Testbed

An independent thermal-orchestration portfolio project for exploring how simulated compute-facility telemetry can be classified, aggregated, and converted into explicit cooling decisions.

This repository is **not affiliated with xAI**, does not use proprietary xAI data, and is not evidence of deployment inside Colossus or any production datacenter. Hardware scale, PUE, latency, reliability, and cost outcomes remain unverified unless accompanied by a current reproducible receipt.

## What is implemented

The strongest current path is a Python simulation and test harness:

- [`apex_core/thermal_orchestrator.py`](apex_core/thermal_orchestrator.py) models thermal nodes and cooling zones, classifies threshold states, computes zone statistics, and dispatches asynchronous controller modules.
- [`cells/rack_cell.py`](cells/rack_cell.py) models rack-level inlet, exhaust, power, and intervention thresholds.
- [`src/thermal_sentinel.py`](src/thermal_sentinel.py) provides a small trend-projection demonstration. It is a heuristic proxy, **not a trained LSTM model**.
- [`omega/apex_cli.py`](omega/apex_cli.py) exposes blueprint-generation and dependency/environment status commands.
- [`connectors/`](connectors/) contains optional integration adapters and simulation bridges. Adapter presence does not establish live provider connectivity.
- [`tests/`](tests/) contains behavioral tests for thermal classification, zone computation, controller actions, schemas, connector boundaries, and selected integration paths.

The repository also contains dashboards, digital-twin experiments, engineering documents, and historical architecture layers. Those surfaces have different evidence states and should not be treated as one production runtime.

## Fastest reproducible review

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install pytest pytest-asyncio
python -m pytest tests/test_thermal_core.py -q
```

On Windows PowerShell, activate with:

```powershell
.venv\Scripts\Activate.ps1
```

The broader dependency set is recorded in [`requirements.txt`](requirements.txt). It includes optional data, connector, ML, simulation, visualization, and document-generation packages; installing it is not required to inspect the core thermal tests.

## Demonstration commands

### Core behavioral tests

```bash
python -m pytest tests/test_thermal_core.py -v
```

### Dependency and environment report

```bash
python omega/apex_cli.py status
```

The status command reports imports and environment-variable presence. It is **not** a live service-health check.

### Blueprint-generation experiment

```bash
python -m pip install ezdxf matplotlib
python omega/apex_cli.py blueprint --all --output /tmp/CCL-002-demo
```

Generated drawings are portfolio artifacts and require independent engineering review before any real-world use.

## Core architecture

```text
simulated telemetry
        │
        ▼
ThermalNode / RackCell
        │
        ▼
CoolingZone aggregation
        │
        ├── threshold classification
        ├── anomaly baseline comparison
        └── thermal-budget checks
        │
        ▼
APEXThermalOrchestrator
        │
        ├── MICROWAVE  — zone sweep and bounded cooling adjustments
        ├── SUPERNOVA  — explicit emergency response decisions
        ├── SHADOW     — moving-baseline anomaly detection
        ├── GHOST      — small simulated flow adjustments
        └── optional connector and forecasting paths
```

The names are project terminology. The implemented behavior is defined by source and tests, not by the labels.

## Evidence state

| Capability | Current evidence state |
|---|---|
| Thermal-node and zone models | Source present; behavioral tests present |
| Threshold and emergency decision logic | Source present; behavioral tests present |
| Moving-baseline anomaly detection | Source present; behavioral tests present |
| Blueprint generation | Source present; CI smoke gate proposed on the hardening branch |
| Trend-based thermal sentinel | Heuristic simulation only |
| Digital-twin and dashboard layers | Source present; end-to-end deployment not verified here |
| MCP, Aspen, Supabase, Notion, or external-provider connectivity | Adapters or references may exist; live integration not established by this README |
| Real GPU telemetry or cooling hardware control | Not implemented or verified in this review |
| 100,000-GPU or hyperscale operation | Scenario language only; not verified |
| Production PUE, latency, availability, or cost improvement | Not verified |

## Repository boundaries

This repository contains multiple generations and experimental layers. The current canonical review order is:

1. `apex_core/` and `cells/` for the primary simulation model;
2. `tests/test_thermal_core.py` for the clearest behavioral contract;
3. `omega/apex_cli.py` for blueprint and environment commands;
4. `connectors/` for optional boundaries that require separate verification;
5. `digital-twin/`, dashboards, ML experiments, and historical documents only after their own runnable receipts are established.

## Related portfolio modules

- [`xai-colossus-cooling-alpha`](https://github.com/GlacierEQ/xai-colossus-cooling-alpha) isolates a small stateless thermal-envelope specification.
- [`xai-colossus-cooling-omega`](https://github.com/GlacierEQ/xai-colossus-cooling-omega) isolates a small stateful flow-controller demonstration.
- [`xai-colossal-cooling`](https://github.com/GlacierEQ/xai-colossal-cooling) is a separate historical research and implementation lineage. It is not treated as a duplicate until its unique content is compared and preserved.
- [`monolith`](https://github.com/GlacierEQ/monolith) records the portfolio relationship and canonicalization state without moving source ownership.

## Promotion requirements

Before this project is presented as hardware-verified or deployment-ready, it still needs:

1. a clean full-suite dependency and test receipt at an exact commit;
2. deterministic fixtures for all simulations used in public demonstrations;
3. separation or retirement of duplicate historical paths;
4. explicit schemas for telemetry units and validity ranges;
5. fault-injection and recovery tests;
6. authenticated integration tests for any claimed external connector;
7. disclosed benchmark environments for every scale, latency, PUE, or reliability claim;
8. a security review covering secrets, untrusted telemetry, command authority, and dependency risk.

## Authorship and use

Independent portfolio work by Casey Barton / GlacierEQ. Company and product names identify the engineering problem space only; they do not imply employment, endorsement, partnership, insider access, or production deployment.
