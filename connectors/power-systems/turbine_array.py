"""
GasTurbineArrayController
==========================
Manages 8x on-site gas turbines providing 440 MW backup/peaker capacity.

Specs per unit:
  - Model: GE LM6000 PC Sprint (55 MW each)
  - Fuel: Natural gas (primary) + diesel backup
  - Start time: < 10 min (hot), < 30 min (cold)
  - Emissions: CARB Tier 4 compliant
  - Generator: 60 Hz, 13.8 kV output -> campus 13.8 kV bus
  - Heat rate: 8,900 BTU/kWh (LHV)
  - Exhaust: HRSG optional for combined heat recovery

Array modes:
  STANDBY    — all units in hot standby, < 10min to full power
  PEAKING    — 1-4 units online for grid peak shaving
  ISLAND     — full 8-unit operation during grid outage
  EMERGENCY  — maximum output, overrides all limits
"""
import asyncio, logging, time, uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Callable, Dict, List

logger = logging.getLogger(__name__)

TURBINE_COUNT          = 8
TURBINE_CAPACITY_MW    = 55.0
ARRAY_CAPACITY_MW      = TURBINE_COUNT * TURBINE_CAPACITY_MW   # 440 MW
HOT_START_MIN          = 10
COLD_START_MIN         = 30
HEAT_RATE_BTU_KWH      = 8_900
EMISSION_NOX_PPM_MAX   = 9.0


class TurbineMode(Enum):
    STANDBY   = "standby"
    STARTING  = "starting"
    ONLINE    = "online"
    PEAKING   = "peaking"
    ISLAND    = "island"
    EMERGENCY = "emergency"
    OFFLINE   = "offline"
    FAULT     = "fault"


@dataclass
class TurbineState:
    turbine_id: str
    unit_number: int
    mode: TurbineMode = TurbineMode.STANDBY
    output_mw: float = 0.0
    exhaust_temp_c: float = 480.0
    inlet_temp_c: float = 25.0
    speed_rpm: float = 3600.0
    fuel_flow_mmbtu_hr: float = 0.0
    nox_ppm: float = 4.5
    runtime_hours: float = 0.0
    last_start: Optional[str] = None
    fault_codes: List[str] = field(default_factory=list)

    @property
    def online(self) -> bool:
        return self.mode in (TurbineMode.ONLINE, TurbineMode.PEAKING,
                             TurbineMode.ISLAND, TurbineMode.EMERGENCY)


class GasTurbineArrayController:
    def __init__(self, kafka_callback: Optional[Callable] = None, influx_sink=None):
        self.kafka_cb = kafka_callback
        self.influx = influx_sink
        self._running = False
        self._turbines: List[TurbineState] = [
            TurbineState(turbine_id=f"GT-{i:02d}", unit_number=i)
            for i in range(1, TURBINE_COUNT + 1)
        ]
        self._array_mode = TurbineMode.STANDBY
        self._stats = {"starts": 0, "island_events": 0,
                       "emergency_events": 0, "readings": 0}

    async def start(self, poll_interval_sec: float = 5.0):
        self._running = True
        logger.info(f"[TurbineArray] {TURBINE_COUNT}x GE LM6000 | {ARRAY_CAPACITY_MW}MW capacity")
        while self._running:
            await self._poll_all()
            await asyncio.sleep(poll_interval_sec)

    async def stop(self): self._running = False

    async def activate_island_mode(self):
        """Called by PowerOrchestrator on grid loss."""
        self._array_mode = TurbineMode.ISLAND
        self._stats["island_events"] += 1
        logger.critical("[TurbineArray] ISLAND MODE — grid loss detected, all turbines starting")
        for t in self._turbines:
            if t.mode not in (TurbineMode.ONLINE, TurbineMode.FAULT):
                asyncio.create_task(self._start_turbine(t))
        if self.kafka_cb:
            asyncio.create_task(self.kafka_cb("colossus.power.alerts", {
                "event_id": str(uuid.uuid4()), "event_type": "island_mode_activated",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "turbines_starting": TURBINE_COUNT}))

    async def _start_turbine(self, t: TurbineState):
        t.mode = TurbineMode.STARTING
        t.last_start = datetime.now(timezone.utc).isoformat()
        self._stats["starts"] += 1
        await asyncio.sleep(0.1)  # In real: 10-30 min startup sequence
        t.mode = TurbineMode.ONLINE
        t.output_mw = TURBINE_CAPACITY_MW
        logger.info(f"[TurbineArray] {t.turbine_id} ONLINE | {t.output_mw}MW")

    async def _poll_all(self):
        import random
        for t in self._turbines:
            if t.online:
                t.output_mw      = round(TURBINE_CAPACITY_MW * random.uniform(0.95, 1.0), 2)
                t.exhaust_temp_c = round(480 + random.gauss(0, 5), 1)
                t.fuel_flow_mmbtu_hr = round((t.output_mw * 1000 * HEAT_RATE_BTU_KWH) / 1e6, 2)
                t.nox_ppm        = round(random.uniform(3.5, 7.0), 2)
                t.runtime_hours  += (5.0 / 3600)
        self._stats["readings"] += 1
        if self.influx:
            total_mw = sum(t.output_mw for t in self._turbines if t.online)
            try:
                await self.influx.write_reading(
                    measurement="colossus_power",
                    tags={"source": "turbine_array", "mode": self._array_mode.value},
                    fields={"total_output_mw": total_mw,
                            "units_online": sum(1 for t in self._turbines if t.online),
                            "array_capacity_mw": ARRAY_CAPACITY_MW})
            except Exception as e:
                logger.warning(f"[TurbineArray] InfluxDB emit failed: {e}")

    def array_status(self) -> dict:
        online = [t for t in self._turbines if t.online]
        return {"array_mode": self._array_mode.value,
                "units_online": len(online),
                "total_capacity_mw": ARRAY_CAPACITY_MW,
                "current_output_mw": round(sum(t.output_mw for t in online), 2),
                "stats": self._stats}
