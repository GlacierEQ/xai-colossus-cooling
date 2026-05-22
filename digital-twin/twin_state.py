"""
Twin State Composer — Phase 7 Digital Twin (Hardened)
Aggregates live snapshots from Water, GPU, Power, and Cooling agents
into one unified facility state document pushed to InfluxDB + Kafka.
"""
import asyncio, logging, uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class TwinStateComposer:
    def __init__(
        self,
        water_agent=None,
        gpu_agent=None,
        power_controller=None,
        turbine_fleet=None,
        ats_controller=None,
        ups_manager=None,
        influx_sink=None,
        kafka_callback: Optional[Callable] = None,
    ):
        self.water     = water_agent
        self.gpu       = gpu_agent
        self.power     = power_controller
        self.turbines  = turbine_fleet
        self.ats       = ats_controller
        self.ups       = ups_manager
        self.influx    = influx_sink
        self.kafka_cb  = kafka_callback
        self.running   = False
        self._last_state: Dict = {}

    # ------------------------------------------------------------------
    # Compose a single unified state snapshot from all live agents
    # ------------------------------------------------------------------
    def compose(self) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        state = {
            "snapshot_id": str(uuid.uuid4()),
            "timestamp": now,
            "water":   self.water.snapshot()   if self.water   else {},
            "gpu":     self.gpu.snapshot()     if self.gpu     else {},
            "power":   self.power.snapshot()   if self.power   else {},
            "turbines":self.turbines.snapshot() if self.turbines else {},
            "ats":     self.ats.transfer_report() if self.ats  else {},
            "ups":     self.ups.snapshot()     if self.ups     else {},
        }
        state["kpis"] = self._compute_kpis(state)
        self._last_state = state
        return state

    # ------------------------------------------------------------------
    # Derived KPIs from live data
    # ------------------------------------------------------------------
    def _compute_kpis(self, state: Dict) -> Dict[str, float]:
        kpis: Dict[str, float] = {}
        # PUE: total facility power / IT power
        try:
            power_data = state["power"]
            total_mw = sum(v["mw_active"] for v in power_data.get("sources", {}).values())
            it_mw = state["gpu"].get("total_power_kw", 0) / 1000
            kpis["pue"] = round(total_mw / it_mw, 4) if it_mw > 0 else 0.0
        except Exception:
            kpis["pue"] = 0.0
        # Max GPU junction temp
        try:
            kpis["max_gpu_tj_c"] = state["gpu"].get("max_die_temp_c", 0.0)
        except Exception:
            kpis["max_gpu_tj_c"] = 0.0
        # Cistern level
        try:
            kpis["cistern_level_pct"] = state["water"].get("cistern_level_pct", 0.0)
        except Exception:
            kpis["cistern_level_pct"] = 0.0
        # Turbine MW online
        try:
            kpis["turbine_mw_online"] = state["turbines"].get("total_mw", 0.0)
        except Exception:
            kpis["turbine_mw_online"] = 0.0
        return kpis

    # ------------------------------------------------------------------
    # Continuous polling loop — compose + publish every interval
    # ------------------------------------------------------------------
    async def run(self, interval_s: float = 10.0):
        self.running = True
        while self.running:
            try:
                state = self.compose()
                await self._publish(state)
            except Exception as exc:
                logger.error("TwinStateComposer error: %s", exc)
            await asyncio.sleep(interval_s)

    async def stop(self):
        self.running = False

    # ------------------------------------------------------------------
    # Publish to InfluxDB + Kafka
    # ------------------------------------------------------------------
    async def _publish(self, state: Dict):
        if self.influx:
            try:
                await self.influx.write_reading(
                    measurement="colossus_kpi",
                    tags={"scope": "facility"},
                    fields=state["kpis"],
                )
            except Exception as exc:
                logger.error("InfluxDB publish error: %s", exc)
        if self.kafka_cb:
            try:
                await self.kafka_cb("colossus.twin.state", state)
            except Exception as exc:
                logger.error("Kafka publish error: %s", exc)

    @property
    def last_state(self) -> Dict:
        return self._last_state
