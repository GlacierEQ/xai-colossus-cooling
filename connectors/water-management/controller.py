"""
WaterManagementController
=========================
Orchestrates triple-redundancy water supply for Colossus v2 cooling.

Source priority order:
  1. PRIMARY   — 600mm municipal main (pressure-sustaining valve, EM flow meter ±0.5%)
  2. CISTERN   — 10,000,000L emergency tank (72hr autonomous operation at peak)
  3. RO_PLANT  — 500,000 L/day reverse osmosis
  4. AWG       — Atmospheric Water Generator array (backup/supplement)

AI pre-cooling: Grok 15-min lookahead triggers valve pre-staging.
All events → Kafka colossus.cooling.events + InfluxDB colossus_water_flow.
"""
import asyncio, logging, time, uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Callable, Dict

logger = logging.getLogger(__name__)


class WaterSource(Enum):
    MUNICIPAL = "municipal"
    CISTERN   = "cistern"
    RO_PLANT  = "ro_plant"
    AWG       = "awg"
    NONE      = "none"


class SourceStatus(Enum):
    ONLINE    = "online"
    DEGRADED  = "degraded"
    OFFLINE   = "offline"
    UNKNOWN   = "unknown"


@dataclass
class SourceState:
    source: WaterSource
    status: SourceStatus = SourceStatus.UNKNOWN
    flow_lpm: float = 0.0          # L/min actual
    pressure_bar: float = 0.0
    tds_ppm: float = 0.0           # Total Dissolved Solids
    temp_c: float = 18.0
    last_updated: float = field(default_factory=time.time)


@dataclass
class ValveState:
    valve_id: str
    source: WaterSource
    open_pct: float = 0.0          # 0=closed, 100=fully open
    target_pct: float = 0.0
    actuating: bool = False


class WaterManagementController:
    """
    Main water orchestration controller.
    Monitors all sources, switches automatically on failure,
    integrates AI pre-cooling predictions.
    """
    SOURCE_PRIORITY = [WaterSource.MUNICIPAL, WaterSource.CISTERN,
                       WaterSource.RO_PLANT, WaterSource.AWG]

    # Design flow rates (L/min)
    DESIGN_FLOW = {
        WaterSource.MUNICIPAL: 2500.0,
        WaterSource.CISTERN:   1800.0,   # controlled draw to preserve 72hr autonomy
        WaterSource.RO_PLANT:  347.0,    # 500K L/day = 347 L/min
        WaterSource.AWG:       14.0,     # 2000 L/day minimum array
    }

    def __init__(self, kafka_callback: Optional[Callable] = None,
                 influx_sink=None,
                 precooling_engine=None):
        self.kafka_cb = kafka_callback
        self.influx = influx_sink
        self.precooling = precooling_engine
        self._sources: Dict[WaterSource, SourceState] = {
            s: SourceState(source=s) for s in WaterSource if s != WaterSource.NONE
        }
        self._valves: Dict[WaterSource, ValveState] = {
            s: ValveState(valve_id=f"valve-{s.value}", source=s)
            for s in WaterSource if s != WaterSource.NONE
        }
        self._active_source = WaterSource.MUNICIPAL
        self._running = False
        self._stats = {"source_switches": 0, "precooling_triggers": 0,
                       "valve_ops": 0, "failovers": 0}

    async def start(self):
        self._running = True
        logger.info("[WaterCtrl] Starting — triple-redundancy active")
        await asyncio.gather(
            self._monitor_loop(),
            self._precooling_loop(),
        )

    async def stop(self):
        self._running = False
        await self._close_all_valves()

    async def _monitor_loop(self):
        while self._running:
            await self._poll_sources()
            await self._evaluate_failover()
            await asyncio.sleep(1.0)

    async def _precooling_loop(self):
        """Every 60s: ask Grok engine for 15-min lookahead, pre-stage valves."""
        while self._running:
            await asyncio.sleep(60.0)
            if self.precooling:
                try:
                    forecast = await self.precooling.forecast_15min()
                    if forecast.get("pre_stage_valves"):
                        await self._prestage(forecast)
                        self._stats["precooling_triggers"] += 1
                except Exception as e:
                    logger.warning(f"[WaterCtrl] Pre-cooling forecast error: {e}")

    async def _poll_sources(self):
        """In production: read from Modbus/OPC-UA sensor network."""
        import random
        for source, state in self._sources.items():
            state.flow_lpm     = round(self.DESIGN_FLOW[source] * random.uniform(0.97, 1.03), 2)
            state.pressure_bar = round(random.uniform(5.8, 6.5), 3)
            state.tds_ppm      = round(random.uniform(1.0, 8.0), 1)
            state.temp_c       = round(random.uniform(17.5, 18.5), 2)
            state.status       = SourceStatus.ONLINE
            state.last_updated = time.time()

    async def _evaluate_failover(self):
        active_state = self._sources[self._active_source]
        if active_state.status == SourceStatus.OFFLINE:
            await self._failover()

    async def _failover(self):
        old = self._active_source
        for source in self.SOURCE_PRIORITY:
            if self._sources[source].status == SourceStatus.ONLINE:
                self._active_source = source
                self._stats["failovers"] += 1
                self._stats["source_switches"] += 1
                logger.critical(f"[WaterCtrl] FAILOVER {old.value} -> {source.value}")
                await self._switch_valve(old, source)
                await self._emit_event("failover", old, source)
                return
        logger.critical("[WaterCtrl] EMERGENCY: all water sources OFFLINE")
        await self._emit_event("all_sources_offline", old, WaterSource.NONE)

    async def _switch_valve(self, close: WaterSource, open_: WaterSource):
        if close != WaterSource.NONE:
            self._valves[close].target_pct = 0.0
        if open_ != WaterSource.NONE:
            self._valves[open_].target_pct = 100.0
        self._stats["valve_ops"] += 2

    async def _prestage(self, forecast: dict):
        """Pre-open primary valve by forecast delta before load spike."""
        delta_pct = forecast.get("valve_prestage_pct", 10.0)
        v = self._valves[self._active_source]
        v.target_pct = min(100.0, v.open_pct + delta_pct)
        logger.info(f"[WaterCtrl] Pre-staging {self._active_source.value} valve -> {v.target_pct}%")

    async def _close_all_valves(self):
        for v in self._valves.values():
            v.target_pct = 0.0

    async def _emit_event(self, event_type: str, from_source: WaterSource, to_source: WaterSource):
        payload = {"event_id": str(uuid.uuid4()), "event_type": event_type,
                   "from_source": from_source.value, "to_source": to_source.value,
                   "timestamp": datetime.now(timezone.utc).isoformat(),
                   "active_source": self._active_source.value}
        if self.kafka_cb:
            asyncio.create_task(self.kafka_cb("colossus.cooling.events", payload))
        if self.influx:
            asyncio.create_task(self.influx.write_reading(
                measurement="colossus_water_flow",
                tags={"event_type": event_type, "source": to_source.value},
                fields={"active_source": to_source.value, "failover": int(event_type == "failover")}))

    def status(self) -> dict:
        return {"active_source": self._active_source.value,
                "sources": {s.value: {"status": self._sources[s].status.value,
                                       "flow_lpm": self._sources[s].flow_lpm}
                             for s in WaterSource if s != WaterSource.NONE},
                "stats": self._stats}
