# GPU Cluster Agent — Phase 4

Orchestrates the 2,000,000 GPU cluster for xAI Colossus v2.

## Hierarchy
```
Cluster: 2,000,000 GPUs
  14 Zones x ~142,857 GPUs
    24 Rows per zone
      NVL72 Nodes (72 GPUs each) — ~27,778 total nodes
        H200 | GB200 | B200 GPU models
          NVLink fabric per zone
          InfiniBand Quantum-3 interconnect
```

## Thermal Throttle Policy
| Die Temp | Action | Power Reduction |
|----------|--------|-----------------|
| >= 83C | Warning throttle | 25% |
| >= 87C | High throttle | 50% |
| >= 90C | Critical alert | 75% |
| >= 95C | Emergency shutdown | 100% |

## Pre-Cooling Integration
At >= 87C, ThermalThrottleCoordinator requests Grok pre-cooling
forecast, triggering water valve pre-staging before the thermal
spike propagates through the cooling loop.

## KPIs
| KPI | Target |
|-----|--------|
| Mean die temp | <= 72C |
| Throttle events | 0/day |
| Emergency shutdowns | 0 |
| Cluster power | <= 1.4 GW (2M x 700W) |
| Snapshot latency P99 | < 30s |
