"""
CisternMonitor
==============
Monitors the 10,000,000-litre buried 316L stainless emergency cistern.
Tracks: volume, autonomy hours, fill rate, drain rate, leak detection.
Alerts when autonomy < 48hr (warning) or < 12hr (critical).
"""
import asyncio, logging, time, statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Callable

logger = logging.getLogger(__name__)

CISTERN_CAPACITY_L   = 10_000_000   # 10 million litres
PEAK_DRAW_LPM        = 1_800.0      # L/min at peak cooling load
AUTONOMY_TARGET_HR   = 72.0
AUTONOMY_WARNING_HR  = 48.0
AUTONOMY_CRITICAL_HR = 12.0
LEAK_THRESHOLD_LPM   = 5.0          # unexplained loss
LEVEL_WINDOW         = 120          # samples for trend analysis


@dataclass
class CisternReading:
    timestamp: str
    volume_litres: float
    level_pct: float           # 0-100%
    fill_rate_lpm: float       # positive = filling
    drain_rate_lpm: float      # positive = draining
    net_rate_lpm: float        # fill - drain
    temp_c: float
    pressure_bar: float
    autonomy_hours: float
    leak_detected: bool = False
    level_status: str = "ok"   # ok | warning | critical | overflow


class CisternMonitor:
    def __init__(self, initial_volume_l: float = CISTERN_CAPACITY_L,
                 alert_callback: Optional[Callable] = None,
                 influx_sink=None):
        self._volume = initial_volume_l
        self.alert_cb = alert_callback
        self.influx = influx_sink
        self._history: List[CisternReading] = []
        self._running = False
        self._stats = {"readings": 0, "leak_events": 0,
                       "warning_events": 0, "critical_events": 0}

    async def start(self, poll_interval_sec: float = 30.0):
        self._running = True
        logger.info(f"[Cistern] Monitor started — capacity={CISTERN_CAPACITY_L:,}L")
        while self._running:
            reading = await self._read()
            await self._evaluate(reading)
            await self._emit(reading)
            self._history.append(reading)
            if len(self._history) > LEVEL_WINDOW:
                self._history.pop(0)
            self._stats["readings"] += 1
            await asyncio.sleep(poll_interval_sec)

    async def stop(self):
        self._running = False

    async def _read(self) -> CisternReading:
        import random
        # Simulate slow drain at peak load
        drain = PEAK_DRAW_LPM * random.uniform(0.0, 0.05)  # 0-5% of peak
        fill  = drain * random.uniform(0.9, 1.1)            # ~balanced
        self._volume = max(0.0, min(CISTERN_CAPACITY_L,
                                    self._volume + (fill - drain) * 0.5))
        level_pct   = round((self._volume / CISTERN_CAPACITY_L) * 100, 2)
        autonomy_hr = round(self._volume / (PEAK_DRAW_LPM * 60), 2)  # hours
        leak = (drain - fill) > LEAK_THRESHOLD_LPM
        status = "ok"
        if self._volume >= CISTERN_CAPACITY_L * 0.99:
            status = "overflow"
        elif autonomy_hr <= AUTONOMY_CRITICAL_HR:
            status = "critical"
        elif autonomy_hr <= AUTONOMY_WARNING_HR:
            status = "warning"
        return CisternReading(
            timestamp=datetime.now(timezone.utc).isoformat(),
            volume_litres=round(self._volume, 1),
            level_pct=level_pct,
            fill_rate_lpm=round(fill, 2),
            drain_rate_lpm=round(drain, 2),
            net_rate_lpm=round(fill - drain, 2),
            temp_c=round(random.uniform(17.8, 18.2), 2),
            pressure_bar=round(random.uniform(0.8, 1.2), 3),
            autonomy_hours=autonomy_hr,
            leak_detected=leak,
            level_status=status
        )

    async def _evaluate(self, r: CisternReading):
        if r.leak_detected:
            self._stats["leak_events"] += 1
            logger.critical(f"[Cistern] LEAK DETECTED net_rate={r.net_rate_lpm} L/min")
        if r.level_status == "critical":
            self._stats["critical_events"] += 1
            logger.critical(f"[Cistern] CRITICAL autonomy={r.autonomy_hours}hr")
            if self.alert_cb:
                asyncio.create_task(self.alert_cb(r))
        elif r.level_status == "warning":
            self._stats["warning_events"] += 1
            logger.warning(f"[Cistern] WARNING autonomy={r.autonomy_hours}hr")

    async def _emit(self, r: CisternReading):
        if not self.influx: return
        try:
            await self.influx.write_reading(
                measurement="colossus_water_flow",
                tags={"source": "cistern", "status": r.level_status},
                fields={"volume_litres": r.volume_litres, "level_pct": r.level_pct,
                        "autonomy_hours": r.autonomy_hours, "drain_rate_lpm": r.drain_rate_lpm,
                        "fill_rate_lpm": r.fill_rate_lpm, "leak_detected": int(r.leak_detected)},
                ts=r.timestamp)
        except Exception as e:
            logger.warning(f"[Cistern] InfluxDB emit failed: {e}")

    def trend(self) -> dict:
        if not self._history: return {}
        vols = [r.volume_litres for r in self._history]
        auths = [r.autonomy_hours for r in self._history]
        return {"current_volume_l": self._history[-1].volume_litres,
                "current_level_pct": self._history[-1].level_pct,
                "autonomy_hours": self._history[-1].autonomy_hours,
                "vol_trend_lpm": round(statistics.mean([r.net_rate_lpm for r in self._history]), 3),
                "capacity_l": CISTERN_CAPACITY_L, "status": self._history[-1].level_status}

    def stats(self) -> dict: return self._stats
