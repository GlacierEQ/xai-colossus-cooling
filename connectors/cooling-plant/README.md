# Phase 5D — Chiller Plant & Heat Rejection

Magnetic-bearing centrifugal chillers, cooling towers, free cooling economisation,
and AI-predictive pre-cooling for xAI Colossus 2.

## Architecture

```
GPU Heat Load (1.2 GW thermal)
        │
        ▼
 DLC Cold Plates / Immersion Baths
        │
        ▼
 Chiller Plant (R-1234ze, COP 7.8)
        │
        ├──► Cooling Towers (ZLD forced draft)
        │
        └──► Free Cooling Economiser (ambient ≤ 14°C)
```

## Modules

| Module | Function |
|---|---|
| `chiller_plant.py` | Chiller fleet management, COP tracking, staging logic |
| `cooling_tower.py` | Tower fan control, ZLD blowdown, Legionella protocol |
| `free_cooling.py` | Economiser mode, ambient threshold, bypass valves |
| `plant_controller.py` | Unified plant controller: PUE optimisation, AI pre-cooling |

## KPIs

| KPI | Target |
|---|---|
| Total cooling capacity | 1.44 GW (20% margin) |
| Chiller COP | ≥ 7.8 at full load |
| PUE contribution | ≤ 1.03 facility PUE |
| Free cooling hours/yr | ≥ 4,000 (climate-dependent) |
| Cooling tower WCI | ≤ 0.02 L/kWh |
| ZLD compliance | 100% zero liquid discharge |
| Legionella protocol | Monthly thermal shock + weekly ATP test |
