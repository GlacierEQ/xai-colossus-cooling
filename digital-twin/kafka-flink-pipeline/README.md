# Kafka → Flink Digital Twin Pipeline

Real-time ingestion and processing for the xAI Colossus v2 cooling infrastructure.

## Architecture
```
Zone Telemetry Agents  (14 zones × 142 sensors = 1,988 sensors)
         |
         ▼  800M events/day via InfiniBand Quantum-3
  Kafka Topics  colossus.telemetry.zone.zone-{01..14}
  + colossus.cooling.events | colossus.gpu.thermal | colossus.power.pdu
         |
         ▼
  Flink Job: colossus-digital-twin-ingest  (parallelism=256)
    ├─ Dedup → Watermark(200ms) → KeyBy(zone+type)
    ├─ SlidingWindow(30s/5s) → Aggregate(min/max/mean/p95/p99/stddev)
    ├─ AnomalyFlag(Z>3.0) → side output ALERT
    └─ SinkRouter
         ├─ InfluxDB v3  (HOT/WARM/FOREVER series)
         ├─ S3 Data Lake (Parquet, partitioned zone/date)
         └─ Alert Kafka  → PagerDuty
```

## Storage Tiers — 5 EB Total
| Tier | Medium | Capacity | Latency | Retention |
|------|--------|----------|---------|----------|
| HOT  | NVMe SSD | 100 TB | <1ms | 24h raw |
| WARM | SAS SSD | 500 TB | <5ms | 7d aggregated |
| COOL | HDD RAID-60 | 2 PB | <50ms | 90d archive |
| COLD | Tape LTO-9 | 2.4 EB | hours | 7y compliance |
| LAKE | Object Store | unlimited | — | ML training |

## InfluxDB Series
| Series | Retention | Purpose |
|--------|-----------|--------|
| colossus_telemetry | 24h | Raw sensor readings |
| colossus_aggregated | 7d | Window stats |
| colossus_pue | forever | PUE 1.03 + WCI 0.0 KPIs |
| colossus_gpu_thermal | 24h | Per-GPU temps |
| colossus_alerts | 90d | Anomaly events |
| colossus_water_flow | 7d | Phase-2 water mgmt |

## KPIs
- **PUE target:** 1.03 (industry avg 1.58 — 35% better)
- **WCI target:** 0.0 mL/kWh (zero-evaporation closed-loop)
- **Stream throughput:** 800M events/day = 9,260 events/sec
- **Checkpoint:** 5s EXACTLY_ONCE, RocksDB state backend
