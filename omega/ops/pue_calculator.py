"""
Real-Time PUE / WCI Calculator
================================
Power Usage Effectiveness (PUE) = Total Facility Power / IT Equipment Power
Water Consumption Index (WCI) = Litres consumed / kWh IT load

Targets:
  PUE  : 1.03  (industry avg 1.58 => 35% better)
  WCI  : 0.0 mL/kWh  (zero-evaporation closed-loop cooling)

Alert thresholds:
  PUE WARNING  : > 1.05
  PUE CRITICAL : > 1.10
  WCI WARNING  : > 5 mL/kWh  (any evaporative loss)
  WCI CRITICAL : > 20 mL/kWh

Trend window: 300 readings (rolling 5-min at 1s cadence)
"""

import logging
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Callable

logger = logging.getLogger(__name__)

PUE_TARGET = 1.03
PUE_WARNING = 1.05
PUE_CRITICAL = 1.10
WCI_TARGET = 0.0
WCI_WARNING = 5.0  # mL/kWh
WCI_CRITICAL = 20.0  # mL/kWh
TREND_WINDOW = 300  # samples
INDUSTRY_AVG_PUE = 1.58


@dataclass
class PUESample:
    timestamp: str
    it_load_kw: float
    total_facility_kw: float
    cooling_kw: float
    lighting_kw: float
    ups_loss_kw: float
    water_consumed_litres: float  # over measurement period
    measurement_period_hours: float = 1.0
    pue: float = 0.0
    wci_ml_per_kwh: float = 0.0
    pue_status: str = "ok"  # ok | warning | critical
    wci_status: str = "ok"


class PUECalculator:
    def __init__(self, alert_callback: Optional[Callable] = None, influx_sink=None):
        self.alert_cb = alert_callback
        self.influx = influx_sink
        self._history: List[PUESample] = []
        self._stats = {
            "samples": 0,
            "pue_warnings": 0,
            "pue_criticals": 0,
            "wci_warnings": 0,
            "wci_criticals": 0,
        }

    def record(
        self,
        it_load_kw: float,
        total_facility_kw: float,
        cooling_kw: float = 0.0,
        lighting_kw: float = 0.0,
        ups_loss_kw: float = 0.0,
        water_consumed_litres: float = 0.0,
        measurement_period_hours: float = 1.0,
    ) -> PUESample:
        pue = round(total_facility_kw / max(it_load_kw, 0.001), 4)
        it_kwh = it_load_kw * measurement_period_hours
        wci = round((water_consumed_litres * 1000) / max(it_kwh, 0.001), 4)  # mL/kWh

        pue_status = "ok"
        if pue >= PUE_CRITICAL:
            pue_status = "critical"
            self._stats["pue_criticals"] += 1
        elif pue >= PUE_WARNING:
            pue_status = "warning"
            self._stats["pue_warnings"] += 1

        wci_status = "ok"
        if wci >= WCI_CRITICAL:
            wci_status = "critical"
            self._stats["wci_criticals"] += 1
        elif wci >= WCI_WARNING:
            wci_status = "warning"
            self._stats["wci_warnings"] += 1

        sample = PUESample(
            timestamp=datetime.now(timezone.utc).isoformat(),
            it_load_kw=it_load_kw,
            total_facility_kw=total_facility_kw,
            cooling_kw=cooling_kw,
            lighting_kw=lighting_kw,
            ups_loss_kw=ups_loss_kw,
            water_consumed_litres=water_consumed_litres,
            measurement_period_hours=measurement_period_hours,
            pue=pue,
            wci_ml_per_kwh=wci,
            pue_status=pue_status,
            wci_status=wci_status,
        )
        self._history.append(sample)
        if len(self._history) > TREND_WINDOW:
            self._history.pop(0)
        self._stats["samples"] += 1

        if pue_status != "ok" or wci_status != "ok":
            logger.warning(f"[PUE] pue={pue} ({pue_status}) wci={wci} ({wci_status})")
            if self.alert_cb:
                import asyncio

                try:
                    loop = asyncio.get_event_loop()
                    loop.create_task(self.alert_cb(sample))
                except RuntimeError:
                    pass
        else:
            logger.info(
                f"[PUE] pue={pue} wci={wci} IT={it_load_kw}kW total={total_facility_kw}kW"
            )

        return sample

    def trend(self) -> dict:
        if not self._history:
            return {}
        pues = [s.pue for s in self._history]
        wcis = [s.wci_ml_per_kwh for s in self._history]
        it = [s.it_load_kw for s in self._history]
        latest = self._history[-1]
        return {
            "latest_pue": latest.pue,
            "latest_wci": latest.wci_ml_per_kwh,
            "pue_mean": round(statistics.mean(pues), 4),
            "pue_min": round(min(pues), 4),
            "pue_max": round(max(pues), 4),
            "wci_mean": round(statistics.mean(wcis), 4),
            "it_load_mean_kw": round(statistics.mean(it), 2),
            "samples_in_window": len(self._history),
            "pue_target": PUE_TARGET,
            "pue_vs_industry": round(
                ((INDUSTRY_AVG_PUE - latest.pue) / INDUSTRY_AVG_PUE) * 100, 1
            ),
            "pue_status": latest.pue_status,
            "wci_status": latest.wci_status,
        }

    def stats(self) -> dict:
        return self._stats
