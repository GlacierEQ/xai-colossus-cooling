# Power Systems — Phase 6

Dual 500MW utility substations + 8x GE LM6000 gas turbines + UPS + ATS for xAI Colossus v2.

## Capacity Model

```
  SUB-A (utility):  500 MW  ├────────────┐
  SUB-B (utility):  500 MW  │ Utility  │──┐
                            └────────────┘  │
  8x GE LM6000:     440 MW (55MW each)  │──┼──> Campus 13.8kV bus
  UPS Tier 1:        50 MW / 8 min      │  │
  UPS Tier 2:         4 MW / 15 min     │  │
  ----------------------------------------  │
  TOTAL FIRM:      1,440 MW  <────────────┘
  DESIGN LOAD:     1,435 MW
  HEADROOM:            5 MW
```

## Automation Thresholds

| Trigger | Action |
|---------|--------|
| Load >= 1,380 MW (96%) | Pre-spin 2 turbines |
| Grid freq deviation > 0.1 Hz | ATS alert |
| Any substation offline | ATS island mode transfer |
| UPS SOC < 40% | Alert + load-shed non-critical |
| UPS SOC < 20% | Emergency load shed |

## Transfer Sequence

1. Grid loss detected (< 2 cycles / 33ms)
2. UPS to battery (< 4ms, static ATS)
3. Turbines hot-start (< 10 min)
4. At 95% V / 59.9-60.1 Hz: transfer to generator bus
5. UPS returns to float charge via generator
6. On grid restoration: 5-min stability hold, then retransfer

## KPIs

| Metric | Target |
|--------|--------|
| Grid availability | 99.9999% (six-nines) |
| UPS transfer time | < 4 ms |
| Generator online time | < 10 min |
| Power factor | > 0.96 |
| THD | < 5% |
| Frequency deviation | < 0.1 Hz |
