"""
Free Cooling Economiser — Phase 5D
Amplitude-controlled bypass: when ambient ≤ 14°C, bypass chillers entirely.
Hybrid mode between 14°C and 18°C — partial economisation.
Target: ≥ 4,000 free-cooling hours/year.
"""
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

FULL_ECONOMISER_THRESHOLD_C  = 14.0
HYBRID_UPPER_THRESHOLD_C     = 18.0


class EconomiserMode(Enum):
    CHILLER_ONLY  = "chiller_only"    # ambient > 18°C
    HYBRID        = "hybrid"          # 14°C < ambient ≤ 18°C
    FREE_COOLING  = "free_cooling"    # ambient ≤ 14°C — chillers off


@dataclass
class EconomiserStatus:
    mode: EconomiserMode = EconomiserMode.CHILLER_ONLY
    ambient_temp_c: float = 20.0
    bypass_valve_pct: float = 0.0     # 0 = full chiller, 100 = full free cooling
    chiller_load_reduction_pct: float = 0.0
    free_cooling_hours_ytd: float = 0.0


class FreeCoolingController:
    def __init__(self):
        self.status = EconomiserStatus()

    def evaluate(self, ambient_c: float, load_kw: float) -> EconomiserStatus:
        self.status.ambient_temp_c = ambient_c

        if ambient_c <= FULL_ECONOMISER_THRESHOLD_C:
            self.status.mode = EconomiserMode.FREE_COOLING
            self.status.bypass_valve_pct = 100.0
            self.status.chiller_load_reduction_pct = 100.0
            self.status.free_cooling_hours_ytd += 1 / 3600  # per-second increment
            logger.info("FREE COOLING active — ambient %.1f°C, chillers bypassed", ambient_c)

        elif ambient_c <= HYBRID_UPPER_THRESHOLD_C:
            # Linear blend between thresholds
            blend = (HYBRID_UPPER_THRESHOLD_C - ambient_c) / (
                HYBRID_UPPER_THRESHOLD_C - FULL_ECONOMISER_THRESHOLD_C)
            self.status.mode = EconomiserMode.HYBRID
            self.status.bypass_valve_pct = round(blend * 100, 1)
            self.status.chiller_load_reduction_pct = round(blend * 100, 1)
            self.status.free_cooling_hours_ytd += blend / 3600
            logger.info("HYBRID ECONOMISER — %.0f%% free cooling", blend * 100)

        else:
            self.status.mode = EconomiserMode.CHILLER_ONLY
            self.status.bypass_valve_pct = 0.0
            self.status.chiller_load_reduction_pct = 0.0

        return self.status

    def snapshot(self):
        return {
            "mode": self.status.mode.value,
            "ambient_temp_c": self.status.ambient_temp_c,
            "bypass_valve_pct": self.status.bypass_valve_pct,
            "chiller_load_reduction_pct": self.status.chiller_load_reduction_pct,
            "free_cooling_hours_ytd": round(self.status.free_cooling_hours_ytd, 1),
        }
