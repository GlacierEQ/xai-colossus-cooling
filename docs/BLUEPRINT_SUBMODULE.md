# 🔗 colossus-build-blueprint — Submodule Reference

This repo (`xai-colossus-cooling`) is the **live engineering implementation** of the physical cooling systems specified in the master build blueprint.

## Master Blueprint Repo

> **[GlacierEQ/colossus-build-blueprint](https://github.com/GlacierEQ/colossus-build-blueprint)**
> xAI Colossus 2 — Hyper-Intelligent Master Build Plan: Geotechnical, Foundation, Water, Architecture, GPU, Cooling Engineering

## Phase Mapping

| Blueprint Phase | xai-colossus-cooling Module | Key Specs |
|---|---|---|
| [Phase 5A — Cooling](https://github.com/GlacierEQ/colossus-build-blueprint/blob/main/phases/phase-5-cooling/README.md) | `cells/`, `sensors/`, `simulation/` | PUE 1.03, WCI 0.02 L/kWh, 48 zones × 25 MW |
| [Phase 4 — GPU Architecture](https://github.com/GlacierEQ/colossus-build-blueprint/blob/main/phases/phase-4-servers-gpu/README.md) | `api/`, `connectors/` | 2M GPU, 1,200W TDP per GPU, 800M telemetry streams |
| [Phase 2 — Water](https://github.com/GlacierEQ/colossus-build-blueprint/blob/main/phases/phase-2-water/README.md) | `sensors/` (water sensors) | Triple-redundancy intake, VPF distribution |
| [Digital Twin](https://github.com/GlacierEQ/colossus-build-blueprint/blob/main/digital-twin/README.md) | `dashboard/`, `database/` | Kafka → Flink → InfluxDB → Grafana |

## To Add as Git Submodule

Once both repos are configured with appropriate access, run:

```bash
# From root of xai-colossus-cooling
git submodule add https://github.com/GlacierEQ/colossus-build-blueprint.git docs/colossus-build-blueprint
git submodule update --init --recursive
```

This pins `docs/colossus-build-blueprint/` to the blueprint's `main` branch HEAD.
Update to latest blueprint specs at any time:

```bash
cd docs/colossus-build-blueprint
git pull origin main
cd ../..
git add docs/colossus-build-blueprint
git commit -m "chore: update blueprint submodule to latest main"
```

## Sync Policy

- Blueprint `main` branch is the **source of truth** for physical specs (dimensions, materials, load ratings)
- `xai-colossus-cooling` implements those specs in software — never override a blueprint physical spec without updating the blueprint first
- When Phase 5B+ cooling specs are added to the blueprint, open a corresponding issue here for software implementation tracking

## Key Constants Derived from Blueprint

```python
# From Phase 5A cooling specs
THERMAL_ZONES = 48
THERMAL_LOAD_PER_ZONE_MW = 25
TOTAL_THERMAL_LOAD_MW = 1_200
TARGET_PUE = 1.03
TARGET_WCI_L_PER_KWH = 0.02
COOLANT_SUPPLY_TEMP_C = 20.0
GPU_TJ_CAP_C = 85.0
DELTA_T_C = GPU_TJ_CAP_C - COOLANT_SUPPLY_TEMP_C  # = 65.0

# From Phase 4 GPU specs
TOTAL_GPUS = 2_000_000
GPU_TDP_WATTS = 1_200
SENSOR_STREAMS = 800_000_000  # 800M telemetry time-series
```
