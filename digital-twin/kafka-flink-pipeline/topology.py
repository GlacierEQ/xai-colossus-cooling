"""
Flink Streaming Topology — xAI Colossus Digital Twin
Ingests colossus.telemetry.* Kafka topics.
Pipeline: dedup -> normalize -> window aggregate -> anomaly flag -> multi-sink

Storage tiers (5 EB total):
  HOT   NVMe SSD       100 TB   <1ms    24h raw
  WARM  SAS SSD        500 TB   <5ms    7d aggregated
  COOL  HDD RAID-60    2 PB     <50ms   90d archive
  COLD  Tape LTO-9     2.4 EB   hours   7y compliance
  LAKE  Object store   unlimited  -     ML training
"""

import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

STORAGE_TIERS = [
    {
        "tier": "HOT",
        "medium": "NVMe SSD",
        "capacity_tb": 100,
        "latency": "<1ms",
        "retention": "24h",
        "type": "raw",
    },
    {
        "tier": "WARM",
        "medium": "SAS SSD",
        "capacity_tb": 500,
        "latency": "<5ms",
        "retention": "7d",
        "type": "aggregated",
    },
    {
        "tier": "COOL",
        "medium": "HDD RAID-60",
        "capacity_tb": 2_000,
        "latency": "<50ms",
        "retention": "90d",
        "type": "archive",
    },
    {
        "tier": "COLD",
        "medium": "Tape LTO-9",
        "capacity_tb": 2_400_000,
        "latency": "hours",
        "retention": "7y",
        "type": "compliance",
    },
    {
        "tier": "LAKE",
        "medium": "Object Store",
        "capacity_tb": None,
        "latency": "varies",
        "retention": "forever",
        "type": "ml_training",
    },
]

TOPICS = [f"colossus.telemetry.zone.zone-{i:02d}" for i in range(1, 15)] + [
    "colossus.cooling.events",
    "colossus.power.pdu",
    "colossus.gpu.thermal",
    "colossus.security.access",
]


@dataclass
class FlinkJobConfig:
    job_name: str = "colossus-digital-twin-ingest"
    parallelism: int = 256
    checkpoint_interval_ms: int = 5_000
    checkpoint_mode: str = "EXACTLY_ONCE"
    watermark_lag_ms: int = 200
    window_size_sec: int = 30
    window_slide_sec: int = 5
    kafka_group_id: str = "colossus-flink-twin"
    kafka_bootstrap: str = "colossus-kafka-01:9092,colossus-kafka-02:9092"
    influx_url: str = "http://colossus-influx-01:8086"
    influx_org: str = "glaciereq"
    influx_bucket: str = "colossus_telemetry"
    s3_lake_bucket: str = "s3://colossus-data-lake"
    anomaly_threshold: float = 3.0
    dead_letter_topic: str = "colossus.dlq.telemetry"


class ColossusFlinkTopology:
    def __init__(self, config: Optional[FlinkJobConfig] = None):
        self.config = config or FlinkJobConfig()

    def describe_dag(self) -> List[Dict[str, Any]]:
        c = self.config
        return [
            {
                "step": 1,
                "op": "KafkaSource",
                "detail": f"{len(TOPICS)} topics group={c.kafka_group_id}",
            },
            {
                "step": 2,
                "op": "Deserialize",
                "detail": "JSON -> TelemetryEvent POJO / Avro in prod",
            },
            {
                "step": 3,
                "op": "Dedup",
                "detail": f"KeyBy(reading_id) TTL={c.watermark_lag_ms * 10}ms",
            },
            {
                "step": 4,
                "op": "WatermarkAssign",
                "detail": f"BoundedOutOfOrder lag={c.watermark_lag_ms}ms",
            },
            {"step": 5, "op": "KeyBy", "detail": "zone_id + sensor_type"},
            {
                "step": 6,
                "op": "SlidingWindow",
                "detail": f"{c.window_size_sec}s / {c.window_slide_sec}s slide",
            },
            {
                "step": 7,
                "op": "AggregateFunction",
                "detail": "min/max/mean/p95/p99/stddev per group",
            },
            {
                "step": 8,
                "op": "AnomalyFlag",
                "detail": f"Z-score > {c.anomaly_threshold} -> ALERT side output",
            },
            {
                "step": 9,
                "op": "SinkRouter",
                "detail": "fan-out: HOT/WARM/COOL/LAKE + InfluxDB + DLQ",
            },
            {
                "step": 10,
                "op": "InfluxDBSink",
                "detail": f"bucket={c.influx_bucket} org={c.influx_org}",
            },
            {
                "step": 11,
                "op": "S3LakeSink",
                "detail": f"Parquet partitioned zone/date -> {c.s3_lake_bucket}",
            },
            {
                "step": 12,
                "op": "AlertKafkaSink",
                "detail": "colossus.alerts.anomaly + PagerDuty webhook",
            },
            {
                "step": 13,
                "op": "Checkpoint",
                "detail": f"{c.checkpoint_interval_ms}ms {c.checkpoint_mode} RocksDB",
            },
        ]

    def storage_summary(self) -> dict:
        return {
            t["tier"]: {k: v for k, v in t.items() if k != "tier"}
            for t in STORAGE_TIERS
        }

    def to_dict(self) -> dict:
        return {
            "job": self.config.__dict__,
            "dag": self.describe_dag(),
            "storage": self.storage_summary(),
            "topics": TOPICS,
        }
