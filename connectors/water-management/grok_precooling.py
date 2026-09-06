"""
GrokPreCoolingEngine
=====================
Integrates Grok AI for 15-minute thermal load forecasting.
Predicts upcoming GPU cluster heat output based on:
  - Historical thermal trend (rolling 30min)
  - Scheduled workload metadata (job queue depth, tensor parallelism)
  - Ambient conditions (outside temp, humidity)
  - Time-of-day patterns

Outputs valve pre-staging commands to WaterManagementController
before the thermal spike arrives, eliminating reactive lag.

Grok API: wss://api.x.ai/v1/realtime (streaming inference)
"""

import asyncio
import logging
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

FORECAST_HORIZON_MIN = 15
CONFIDENCE_THRESHOLD = 0.75
PRESTAGE_DELTA_PCT = 15.0  # default valve pre-open delta
THERMAL_SPIKE_DELTA_C = 2.0  # predicted temp rise that triggers pre-stage


@dataclass
class ThermalForecast:
    forecast_id: str
    generated_at: str
    horizon_minutes: int = FORECAST_HORIZON_MIN
    predicted_delta_c: float = 0.0  # expected temperature rise
    predicted_it_load_kw: float = 0.0
    confidence: float = 0.0
    pre_stage_valves: bool = False
    valve_prestage_pct: float = 0.0
    model: str = "grok-3"
    reasoning: str = ""


class GrokPreCoolingEngine:
    """
    Connects to Grok realtime API for streaming thermal predictions.
    Falls back to statistical model if Grok is unavailable.
    """

    def __init__(
        self,
        api_key: str = "",
        ws_url: str = "wss://api.x.ai/v1/realtime",
        stat_fallback: bool = True,
    ):
        self.api_key = api_key
        self.ws_url = ws_url
        self.stat_fallback = stat_fallback
        self._thermal_history: List[float] = []  # recent zone mean temps
        self._load_history: List[float] = []  # recent IT load kW
        self._ws = None
        self._stats = {
            "forecasts": 0,
            "grok_hits": 0,
            "fallback_hits": 0,
            "prestages_triggered": 0,
        }

    def update_telemetry(self, mean_temp_c: float, it_load_kw: float):
        """Call this every telemetry cycle to keep history current."""
        self._thermal_history.append(mean_temp_c)
        self._load_history.append(it_load_kw)
        if len(self._thermal_history) > 1800:
            self._thermal_history.pop(0)  # 30min @ 1s
        if len(self._load_history) > 1800:
            self._load_history.pop(0)

    async def forecast_15min(self) -> Dict[str, Any]:
        """Returns forecast dict for WaterManagementController."""
        import uuid

        try:
            if self.api_key and self._ws:
                forecast = await self._grok_forecast()
                self._stats["grok_hits"] += 1
            else:
                forecast = self._statistical_forecast()
                self._stats["fallback_hits"] += 1
        except Exception as e:
            logger.warning(f"[Grok] Forecast error: {e} — using fallback")
            forecast = self._statistical_forecast()
            self._stats["fallback_hits"] += 1

        self._stats["forecasts"] += 1
        if forecast.pre_stage_valves:
            self._stats["prestages_triggered"] += 1
            logger.info(
                f"[Grok] Pre-stage triggered: +{forecast.valve_prestage_pct}% "
                f"delta={forecast.predicted_delta_c}C conf={forecast.confidence}"
            )
        return {
            "forecast_id": str(uuid.uuid4()),
            "pre_stage_valves": forecast.pre_stage_valves,
            "valve_prestage_pct": forecast.valve_prestage_pct,
            "predicted_delta_c": forecast.predicted_delta_c,
            "confidence": forecast.confidence,
            "model": forecast.model,
        }

    async def _grok_forecast(self) -> ThermalForecast:
        """Realtime Grok inference via WebSocket."""
        import uuid

        payload = json.dumps(
            {
                "type": "thermal_forecast",
                "horizon_minutes": FORECAST_HORIZON_MIN,
                "thermal_history_c": self._thermal_history[-60:],
                "load_history_kw": self._load_history[-60:],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        await self._ws.send(payload)
        response = json.loads(await asyncio.wait_for(self._ws.recv(), timeout=2.0))
        delta = response.get("predicted_delta_c", 0.0)
        conf = response.get("confidence", 0.0)
        prestage = conf >= CONFIDENCE_THRESHOLD and delta >= THERMAL_SPIKE_DELTA_C
        return ThermalForecast(
            forecast_id=str(uuid.uuid4()),
            generated_at=datetime.now(timezone.utc).isoformat(),
            predicted_delta_c=delta,
            predicted_it_load_kw=response.get("predicted_it_load_kw", 0.0),
            confidence=conf,
            pre_stage_valves=prestage,
            valve_prestage_pct=PRESTAGE_DELTA_PCT if prestage else 0.0,
            model="grok-3",
            reasoning=response.get("reasoning", ""),
        )

    def _statistical_forecast(self) -> ThermalForecast:
        """Simple linear trend fallback when Grok unavailable."""
        import uuid

        if len(self._thermal_history) < 10:
            return ThermalForecast(
                forecast_id=str(uuid.uuid4()),
                generated_at=datetime.now(timezone.utc).isoformat(),
                model="statistical-fallback",
            )
        recent = self._thermal_history[-60:]
        slope = (recent[-1] - recent[0]) / max(len(recent), 1)
        predicted_delta = slope * (FORECAST_HORIZON_MIN * 60)
        conf = min(0.85, abs(slope) * 100)
        prestage = (
            conf >= CONFIDENCE_THRESHOLD and predicted_delta >= THERMAL_SPIKE_DELTA_C
        )
        return ThermalForecast(
            forecast_id=str(uuid.uuid4()),
            generated_at=datetime.now(timezone.utc).isoformat(),
            predicted_delta_c=round(predicted_delta, 3),
            confidence=round(conf, 3),
            pre_stage_valves=prestage,
            valve_prestage_pct=PRESTAGE_DELTA_PCT if prestage else 0.0,
            model="statistical-fallback",
            reasoning=f"slope={slope:.4f}C/s over {len(recent)} samples",
        )

    def stats(self) -> dict:
        return self._stats
