"""
InfluxDB v3 Sink — Colossus Digital Twin
Retention policies, downsampling, PUE/WCI KPI tracking.

Series:
  colossus_telemetry    raw sensor readings (24h)
  colossus_aggregated   30s window stats (7d)
  colossus_pue          PUE + WCI forever
  colossus_gpu_thermal  per-GPU temps (24h)
  colossus_alerts       anomaly events (90d)
  colossus_water_flow   phase-2 water mgmt (7d)
"""
import asyncio, logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

RETENTION_POLICIES = [
    {"name": "hot_24h",  "duration": "24h", "shard": "1h",  "series": ["colossus_telemetry", "colossus_gpu_thermal"]},
    {"name": "warm_7d",  "duration": "7d",  "shard": "1d",  "series": ["colossus_aggregated", "colossus_water_flow"]},
    {"name": "cool_90d", "duration": "90d", "shard": "7d",  "series": ["colossus_alerts"]},
    {"name": "forever",  "duration": "0s",  "shard": "30d", "series": ["colossus_pue"]},
]

DOWNSAMPLE_TASKS = [
    {"name": "raw_to_1min",  "from": "colossus_telemetry",  "to": "colossus_aggregated", "every": "1m",  "fn": "mean"},
    {"name": "raw_to_5min",  "from": "colossus_telemetry",  "to": "colossus_aggregated", "every": "5m",  "fn": "mean,p95"},
    {"name": "raw_to_1hour", "from": "colossus_aggregated", "to": "colossus_aggregated", "every": "1h",  "fn": "mean,min,max"},
]

PUE_TARGET = 1.03
WCI_TARGET = 0.0


class InfluxV3Sink:
    def __init__(self, url: str = "http://colossus-influx-01:8086",
                 token: str = "", org: str = "glaciereq", bucket: str = "colossus_telemetry"):
        self.url, self.token, self.org, self.bucket = url, token, org, bucket
        self._client = None
        self._write_api = None
        self._stats = {"written": 0, "errors": 0, "batches": 0}

    async def connect(self):
        try:
            from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
            self._client = InfluxDBClientAsync(url=self.url, token=self.token, org=self.org)
            self._write_api = self._client.write_api()
            logger.info(f"[InfluxDB] Connected {self.url} bucket={self.bucket}")
        except Exception as e:
            logger.warning(f"[InfluxDB] Log-only mode: {e}")

    async def disconnect(self):
        if self._client: await self._client.close()

    async def write_reading(self, measurement: str, tags: Dict[str, str], fields: Dict[str, Any], ts: Optional[str] = None):
        point = {"measurement": measurement, "tags": tags, "fields": fields, "time": ts or datetime.now(timezone.utc).isoformat()}
        if self._write_api:
            try:
                await self._write_api.write(bucket=self.bucket, record=point)
                self._stats["written"] += 1
            except Exception as e:
                self._stats["errors"] += 1
                logger.error(f"[InfluxDB] Write error: {e}")
        else:
            logger.debug(f"[InfluxDB:LOG] {measurement} {fields}")
            self._stats["written"] += 1

    async def write_pue(self, it_load_kw: float, total_facility_kw: float, wci_ml_per_kwh: float = 0.0):
        pue = round(total_facility_kw / max(it_load_kw, 1.0), 4)
        await self.write_reading(
            measurement="colossus_pue",
            tags={"facility": "colossus-v2", "target": str(PUE_TARGET)},
            fields={"pue": pue, "pue_delta": round(pue - PUE_TARGET, 4),
                    "it_load_kw": it_load_kw, "total_facility_kw": total_facility_kw,
                    "wci_ml_per_kwh": wci_ml_per_kwh, "sla_met": int(pue <= PUE_TARGET)})

    async def write_batch(self, records: List[Dict[str, Any]]):
        await asyncio.gather(*[self.write_reading(**r) for r in records], return_exceptions=True)
        self._stats["batches"] += 1

    def schema_contracts(self) -> dict:
        return {"retention": RETENTION_POLICIES, "downsample": DOWNSAMPLE_TASKS,
                "pue_target": PUE_TARGET, "wci_target": WCI_TARGET}

    def stats(self) -> dict: return self._stats
