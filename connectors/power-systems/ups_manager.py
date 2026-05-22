"""
UPSManager
==========
Manages the campus UPS (Uninterruptible Power Supply) array.

Tier 1 (Critical IT — GPU compute): 
  - 20x 2.5 MW lithium-ion UPS modules = 50 MW
  - Runtime: 8 minutes at full 1.4 GW load (bridge to turbine)
  - Technology: VRLA Li-Ion, double-conversion online
  - Bypass: Static bypass < 4ms, maintenance bypass available

Tier 2 (Facility + Cooling):
  - 8x 500 kW UPS modules = 4 MW
  - Runtime: 15 minutes (water pumps, HVAC, controls always on)

Battery health: Cell-level BMS monitoring, thermal runaway detection.
"""
import asyncio, logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Callable, List

logger = logging.getLogger(__name__)

TIER1_MODULES        = 20
TIER1_MODULE_MW      = 2.5
TIER1_TOTAL_MW       = TIER1_MODULES * TIER1_MODULE_MW     # 50 MW
TIER1_RUNTIME_MIN    = 8

TIER2_MODULES        = 8
TIER2_MODULE_KW      = 500.0
TIER2_TOTAL_MW       = (TIER2_MODULES * TIER2_MODULE_KW) / 1000  # 4 MW
TIER2_RUNTIME_MIN    = 15

BATTERY_CRITICAL_PCT = 20.0
BATTERY_WARNING_PCT  = 40.0


@dataclass
class UPSModule:
    module_id: str
    tier: int
    capacity_kw: float
    soc_pct: float = 100.0         # State of Charge
    soh_pct: float = 98.0          # State of Health
    online: bool = True
    bypassed: bool = False
    on_battery: bool = False
    input_voltage_v: float = 480.0
    output_voltage_v: float = 480.0
    temp_c: float = 25.0
    load_kw: float = 0.0
    thermal_alarm: bool = False


@dataclass
class UPSReading:
    timestamp: str
    tier: int
    total_capacity_kw: float
    total_load_kw: float
    modules_online: int
    modules_total: int
    min_soc_pct: float
    avg_soc_pct: float
    on_battery: bool
    estimated_runtime_min: float
    status: str  # ok | warning | critical | on_battery


class UPSManager:
    def __init__(self, kafka_callback: Optional[Callable] = None, influx_sink=None):
        self.kafka_cb = kafka_callback
        self.influx = influx_sink
        self._running = False
        self._t1_modules = [
            UPSModule(module_id=f"UPS-T1-{i:02d}", tier=1, capacity_kw=TIER1_MODULE_MW * 1000)
            for i in range(1, TIER1_MODULES + 1)
        ]
        self._t2_modules = [
            UPSModule(module_id=f"UPS-T2-{i:02d}", tier=2, capacity_kw=TIER2_MODULE_KW)
            for i in range(1, TIER2_MODULES + 1)
        ]
        self._on_battery = False
        self._stats = {"readings": 0, "battery_events": 0, "thermal_alarms": 0}

    async def start(self, poll_interval_sec: float = 5.0):
        self._running = True
        logger.info(f"[UPS] Tier1={TIER1_TOTAL_MW}MW ({TIER1_RUNTIME_MIN}min) | Tier2={TIER2_TOTAL_MW}MW ({TIER2_RUNTIME_MIN}min)")
        while self._running:
            for tier, modules in [(1, self._t1_modules), (2, self._t2_modules)]:
                reading = await self._poll_tier(tier, modules)
                await self._evaluate(reading)
                await self._emit(reading)
            self._stats["readings"] += 1
            await asyncio.sleep(poll_interval_sec)

    async def stop(self): self._running = False

    async def switch_to_battery(self):
        """Called by PowerOrchestrator on grid loss before turbines online."""
        self._on_battery = True
        self._stats["battery_events"] += 1
        logger.critical("[UPS] SWITCHING TO BATTERY — grid/turbine feed lost")
        for m in self._t1_modules + self._t2_modules:
            m.on_battery = True

    async def restore_utility(self):
        self._on_battery = False
        for m in self._t1_modules + self._t2_modules:
            m.on_battery = False
            m.soc_pct = min(100.0, m.soc_pct + 0.1)  # Charging
        logger.info("[UPS] Utility restored — charging batteries")

    async def _poll_tier(self, tier: int, modules: List[UPSModule]) -> UPSReading:
        import random
        online = [m for m in modules if m.online]
        for m in online:
            if m.on_battery:
                m.soc_pct = max(0.0, m.soc_pct - random.uniform(0.05, 0.15))
            else:
                m.soc_pct = min(100.0, m.soc_pct + random.uniform(0.0, 0.02))
            m.load_kw = m.capacity_kw * random.uniform(0.60, 0.85)
            m.temp_c  = round(25.0 + (m.load_kw / m.capacity_kw) * 15, 2)
            m.thermal_alarm = m.temp_c > 40.0
            if m.thermal_alarm:
                self._stats["thermal_alarms"] += 1
        socs = [m.soc_pct for m in online] or [100.0]
        cap  = sum(m.capacity_kw for m in online)
        load = sum(m.load_kw for m in online)
        min_soc = min(socs)
        runtime_min = (min_soc / 100.0) * (TIER1_RUNTIME_MIN if tier == 1 else TIER2_RUNTIME_MIN)
        status = ("on_battery" if self._on_battery else
                  "critical" if min_soc <= BATTERY_CRITICAL_PCT else
                  "warning" if min_soc <= BATTERY_WARNING_PCT else "ok")
        return UPSReading(
            timestamp=datetime.now(timezone.utc).isoformat(), tier=tier,
            total_capacity_kw=round(cap, 2), total_load_kw=round(load, 2),
            modules_online=len(online), modules_total=len(modules),
            min_soc_pct=round(min_soc, 2), avg_soc_pct=round(sum(socs)/len(socs), 2),
            on_battery=self._on_battery, estimated_runtime_min=round(runtime_min, 2),
            status=status
        )

    async def _evaluate(self, r: UPSReading):
        if r.status in ("critical", "on_battery"):
            logger.critical(f"[UPS] Tier{r.tier} {r.status.upper()} soc={r.min_soc_pct}% runtime={r.estimated_runtime_min}min")

    async def _emit(self, r: UPSReading):
        if not self.influx: return
        try:
            await self.influx.write_reading(
                measurement="colossus_power",
                tags={"source": f"ups_tier{r.tier}", "status": r.status},
                fields={"total_load_kw": r.total_load_kw, "min_soc_pct": r.min_soc_pct,
                        "estimated_runtime_min": r.estimated_runtime_min,
                        "on_battery": int(r.on_battery), "modules_online": r.modules_online})
        except Exception as e:
            logger.warning(f"[UPS] InfluxDB emit failed: {e}")
