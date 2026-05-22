# Phase 6 — Power Systems

Dual 500 MW substations, 8 on-site 50 MW gas turbines, 24-string UPS, ATS/STS transfer switching,
black-start sequencing, and 5-tier load shedding for xAI Colossus 2.

## Architecture

```
Utility Grid A (500 MW) ──┐
                          ├─► 11 kV Bus ──► ATS ──► IT Load Bus
Utility Grid B (500 MW) ──┘         │
                                     ├─► 8× GTG 50 MW on-site
                                     └─► 24× UPS strings → STS → Critical bus
```

## Modules

| Module | Function |
|---|---|
| `controller.py` | Source capacity evaluation, turbine dispatch, telemetry |
| `turbine_fleet.py` | 8-unit fleet model, economic dispatch, black-start sequence |
| `ats_sts_timing.py` | Transfer timing tests, STS < 4 ms, ATS < 100 ms, 5-tier load shed |
| `black_start.py` | 10-step IEEE C37.101 black-start runbook orchestrator |
| `grid_orchestrator.py` | Grid A/B failure, island-mode, rebalance logic |
| `ups_manager.py` | UPS string status, 15-minute ride-through autonomy |

## KPIs

| KPI | Target |
|---|---|
| Total on-site generation | 400 MW (8 × 50 MW GTG) |
| ATS transfer time | < 100 ms |
| STS transfer time | < 4 ms |
| UPS ride-through | ≥ 15 min |
| Black-start to full load | < 15 min |
| Grid failover (islanding) | < 5 s |
| Redundancy | N+2 all active components |
| Load shed tiers | 5 (Tier 1 = GPU compute — never shed) |
