# ❄️ xAI Colossus Cooling — Thermal Management

[![Tests](https://img.shields.io/badge/tests-63%20passing-brightgreen.svg)](https://github.com/GlacierEQ/xai-colossus-cooling)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![Pro-Code](https://img.shields.io/badge/Pro--Code-7--gate%20audit-brightgreen.svg)](PRO_CODE_AUDIT.md)

> Autonomous thermal management for a **1.5GW, 200k-GPU AI supercomputer**.
> Physics-Informed Neural Network · 100-tank immersion · Cascade shield · Predictive dispatch.

---

## Architecture

```
┌─────────────────────────────────────────┐
│     APEX THERMAL ORCHESTRATOR           │
│  tick-driven · 500ms · Fusion Modes     │
└──────────┬──────────────────────────────┘
           │
    ┌──────┼──────┬──────┬──────┐
    ▼      ▼      ▼      ▼      ▼
 MICROWAVE SUPERNOVA SHADOW GHOST  CORE-THINK
 Zone     Emergency Anomaly Micro  Predictive
 Sweep    Blast    Detect  Optim  Dispatch
```

## Quick Start

```python
from apex_core.thermal_orchestrator import (
    APEXThermalOrchestrator, CoolingMode, CoolingZone, ThermalNode
)
import asyncio

orch = APEXThermalOrchestrator(mode=CoolingMode.COLOSSUS)
zone = CoolingZone(zone_id="ZONE-A", zone_name="Primary")
zone.nodes.append(ThermalNode(
    node_id="N001", rack_id="RACK-001", zone_id="ZONE-A",
    temp_celsius=75.0, gpu_utilization=0.8, power_watts=700
))
orch.register_zone(zone)

result = asyncio.run(orch.tick_cycle())
```

## Pistons (5)

| Piston | Purpose | Innovation |
|--------|---------|------------|
| **MICROWAVE** | Zone sweep, CRAC/liquid boost | Automatic cooling escalation |
| **SUPERNOVA** | Emergency full blast | GPU throttle at 90°C |
| **SHADOW** | Anomaly detection | EMA baseline tracking |
| **GHOST** | Micro-optimization | Invisible flow adjustments |
| **CORE-THINK** | Predictive dispatch | Pre-cooling before thermal events |

## Physics Models

- **PINN** — Physics-Informed Neural Network for thermal validation
- **Maxwell** — Heat transfer in immersion cooling
- **Hamilton-Crosser** — Composite material thermal conductivity
- **Arrhenius** — Degradation lifecycle modeling

## Double Helix

**Alpha (What)**: `thermal/` — PINN, immersion, cascade, predictive
**Omega (How)**: `core/` — Orchestrator, API gateway, MCP bridge

See [`HELIX.md`](HELIX.md) for architecture details.

## Testing

```bash
python -m pytest tests/ -v
```

**63 tests** passing: thermal nodes, cooling zones, pistons, orchestrator integration, MCP validation.

## Scale

| Metric | Value |
|--------|-------|
| Cooling tanks | 100 (immersion) |
| Temperature zones | 4 (A-D) |
| CRAC units | 8 max per zone |
| Liquid flow | 10 LPM boost |
| Tick interval | 500ms |
| Alert levels | 4 (normal/warm/hot/critical) |

---

> *"Physics-first thermal management. Every watt accounted for."*
