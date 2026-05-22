"""
SubstationController
====================
Manages dual 500MW utility substations (A + B) feeding the Colossus campus.

Specs per substation:
  - Capacity: 500 MW continuous
  - Voltage: 345 kV transmission -> 138 kV subtransmission -> 13.8 kV distribution
  - Transformers: 3x 167 MVA units per substation (N+1 redundancy)
  - Protection: SEL-421 line differential + SEL-311L distance relay
  - Transfer time: < 100ms automatic, < 8min manual
  - PQ meters: Dranetz HDPQ Xplorer on every feeder (1-second interval)

Total utility capacity: 1,000 MW
Design load: 1,400 MW (GPU cluster 1,400 MW + facility 35 MW)
Backup gap covered by: 8x gas turbines (440 MW total)
"""
import asyncio, logging, time, uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Callable, Dict, List

logger = logging.getLogger(__name__)

SUBSTATION_CAPACITY_MW   = 500.0
TRANSFORMER_MVA          = 167.0
TRANSFORMERS_PER_SUB     = 3
TRANSMISSION_KV          = 345.0
DISTRIBUTION_KV          = 13.8
TRANSFER_AUTO_MS         = 100
PQ_INTERVAL_SEC          = 1
OVERLOAD_THRESHOLD_PCT   = 95.0
EMERGENCY_THRESHOLD_PCT  = 100.0


class SubstationStatus(Enum):
    ONLINE     = "online"
    DEGRADED   = "degraded"    # 1 of 3 transformers out
    OVERLOADED = "overloaded"
    OFFLINE    = "offline"
    TRANSFER   = "transfer"    # mid-switchover


@dataclass
class TransformerState:
    transformer_id: str
    substation_id: str
    capacity_mva: float = TRANSFORMER_MVA
    load_mw: float = 0.0
    temp_c: float = 65.0
    online: bool = True
    oil_temp_c: float = 55.0
    winding_temp_c: float = 85.0

    @property
    def load_pct(self) -> float:
        return (self.load_mw / self.capacity_mva) * 100 if self.capacity_mva > 0 else 0.0


@dataclass
class SubstationReading:
    substation_id: str
    timestamp: str
    status: str
    total_load_mw: float
    capacity_mw: float
    load_pct: float
    voltage_kv: float
    frequency_hz: float
    power_factor: float
    active_transformers: int
    total_transformers: int
    thd_pct: float           # Total Harmonic Distortion
    alerts: List[str] = field(default_factory=list)


class SubstationController:
    SUBSTATIONS = ["SUB-A", "SUB-B"]

    def __init__(self, kafka_callback: Optional[Callable] = None, influx_sink=None):
        self.kafka_cb = kafka_callback
        self.influx = influx_sink
        self._running = False
        self._transformers: Dict[str, List[TransformerState]] = {
            sid: [TransformerState(transformer_id=f"{sid}-TX{i}", substation_id=sid)
                  for i in range(1, TRANSFORMERS_PER_SUB + 1)]
            for sid in self.SUBSTATIONS
        }
        self._readings: Dict[str, SubstationReading] = {}
        self._stats = {"readings": 0, "overload_events": 0, "transfer_events": 0}

    async def start(self, poll_interval_sec: float = 1.0):
        self._running = True
        logger.info("[SubstationCtrl] Dual 500MW substations online")
        while self._running:
            for sid in self.SUBSTATIONS:
                reading = await self._poll(sid)
                await self._evaluate(reading)
                await self._emit(reading)
                self._readings[sid] = reading
            self._stats["readings"] += 1
            await asyncio.sleep(poll_interval_sec)

    async def stop(self): self._running = False

    async def _poll(self, substation_id: str) -> SubstationReading:
        import random
        txs = self._transformers[substation_id]
        active = [t for t in txs if t.online]
        capacity = sum(t.capacity_mva for t in active)
        load = capacity * random.uniform(0.72, 0.88)  # typical 72-88% utilization
        for t in active:
            t.load_mw = round(load / len(active), 2)
            t.temp_c  = round(65.0 + (t.load_pct / 100) * 25, 2)
        load_pct = (load / capacity * 100) if capacity > 0 else 0.0
        alerts = []
        if load_pct >= EMERGENCY_THRESHOLD_PCT:
            alerts.append(f"EMERGENCY: {substation_id} at {load_pct:.1f}% capacity")
        elif load_pct >= OVERLOAD_THRESHOLD_PCT:
            alerts.append(f"OVERLOAD: {substation_id} at {load_pct:.1f}% capacity")
            self._stats["overload_events"] += 1
        status = ("offline" if not active else
                  "overloaded" if load_pct >= OVERLOAD_THRESHOLD_PCT else
                  "degraded" if len(active) < TRANSFORMERS_PER_SUB else "online")
        return SubstationReading(
            substation_id=substation_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            status=status, total_load_mw=round(load, 2),
            capacity_mw=round(capacity, 2), load_pct=round(load_pct, 2),
            voltage_kv=round(TRANSMISSION_KV * random.uniform(0.995, 1.005), 2),
            frequency_hz=round(60.0 + random.gauss(0, 0.005), 4),
            power_factor=round(random.uniform(0.96, 0.99), 3),
            active_transformers=len(active), total_transformers=len(txs),
            thd_pct=round(random.uniform(1.2, 3.5), 2), alerts=alerts
        )

    async def _evaluate(self, r: SubstationReading):
        if r.alerts:
            for alert in r.alerts:
                logger.warning(f"[Substation] {alert}")
            if self.kafka_cb:
                asyncio.create_task(self.kafka_cb("colossus.power.alerts", {
                    "event_id": str(uuid.uuid4()), "substation_id": r.substation_id,
                    "status": r.status, "load_pct": r.load_pct,
                    "timestamp": r.timestamp, "alerts": r.alerts}))

    async def _emit(self, r: SubstationReading):
        if not self.influx: return
        try:
            await self.influx.write_reading(
                measurement="colossus_power",
                tags={"source": r.substation_id, "status": r.status},
                fields={"load_mw": r.total_load_mw, "load_pct": r.load_pct,
                        "voltage_kv": r.voltage_kv, "frequency_hz": r.frequency_hz,
                        "power_factor": r.power_factor, "thd_pct": r.thd_pct},
                ts=r.timestamp)
        except Exception as e:
            logger.warning(f"[Substation] InfluxDB emit failed: {e}")

    def cluster_load(self) -> dict:
        total = sum(r.total_load_mw for r in self._readings.values())
        return {"total_load_mw": round(total, 2), "substations": {
            sid: {"load_mw": r.total_load_mw, "load_pct": r.load_pct, "status": r.status}
            for sid, r in self._readings.items()}}
