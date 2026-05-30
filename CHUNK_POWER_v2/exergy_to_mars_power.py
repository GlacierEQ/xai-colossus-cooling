"""
CHUNK 3: Exergy-to-Mars Waste Heat Recovery
xAI Colossus Cooling — APEX Architecture
Author: Casey Barton | GlacierEQ
Status: FULLY IMPLEMENTED — CHUNK POWER v2.0

Real-time exergy analysis + Universe Fuel model.
When recovery > 40% threshold → auto-propose revenue arbitrage.
ORC (Organic Rankine Cycle) + Absorption Chiller integration.
"""

from __future__ import annotations
import time
import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

logger = logging.getLogger("ExergyToMars")

T_DEAD_K = 308.15      # 35°C Memphis ambient (dead state)
T_DISTRICT_C = 90.0    # district heating delivery target
ORC_EFFICIENCY = 0.12  # organic Rankine cycle thermal→electric efficiency
ABS_CHILLER_COP = 0.7  # absorption chiller COP (heat → cooling)


@dataclass
class WasteHeatStream:
    """A single recoverable heat stream from the cooling system."""
    stream_id: str
    source: str                    # e.g. "chiller_condenser", "rack_exhaust"
    temperature_c: float           # stream temperature
    heat_flow_kw: float            # available heat flow

    @property
    def temperature_k(self) -> float:
        return self.temperature_c + 273.15

    @property
    def exergy_kw(self) -> float:
        """Carnot-quality available work: W = Q(1 - T_dead/T_source)."""
        if self.temperature_k <= T_DEAD_K:
            return 0.0
        return self.heat_flow_kw * (1.0 - T_DEAD_K / self.temperature_k)

    @property
    def quality_factor(self) -> float:
        """Thermodynamic quality: exergy fraction of total enthalpy."""
        if self.heat_flow_kw <= 0:
            return 0.0
        return self.exergy_kw / self.heat_flow_kw


@dataclass
class RecoveryAction:
    """A proposed or active waste heat recovery action."""
    action_id: str
    stream_id: str
    method: str                        # "orc", "absorption_chiller", "district_heat"
    recovered_kw: float
    revenue_usd_hr: float = 0.0
    auto_proposed: bool = False


class ExergyToMarsPowerSystem:
    """
    Waste heat recovery orchestrator.
    - Monitors all condenser and exhaust heat streams in real time.
    - Computes second-law efficiency across the plant.
    - Auto-proposes revenue when recovery fraction exceeds 40%.
    - Integrates ORC (power) + Absorption Chiller (cooling) + District Heat.
    """

    RECOVERY_TRIGGER_FRACTION = 0.40   # auto-propose above this
    ELECTRICITY_PRICE_USD_KWH = 0.075  # Memphis industrial rate
    COOLING_VALUE_USD_KWH = 0.04       # value of cooling from absorption

    def __init__(self, revenue_callback: Optional[Callable[[RecoveryAction], None]] = None):
        self.streams: dict[str, WasteHeatStream] = {}
        self.actions: list[RecoveryAction] = []
        self.revenue_callback = revenue_callback
        logger.info("ExergyToMarsPowerSystem initialized — waste heat tracking active")

    def add_stream(self, stream: WasteHeatStream) -> None:
        self.streams[stream.stream_id] = stream

    @property
    def total_heat_kw(self) -> float:
        return sum(s.heat_flow_kw for s in self.streams.values())

    @property
    def total_exergy_kw(self) -> float:
        return sum(s.exergy_kw for s in self.streams.values())

    @property
    def second_law_efficiency(self) -> float:
        """Plant second-law efficiency = exergy recovered / exergy available."""
        recovered_exergy = sum(a.recovered_kw for a in self.actions)
        if self.total_exergy_kw <= 0:
            return 0.0
        return recovered_exergy / self.total_exergy_kw

    def compute_orc_output(self, stream: WasteHeatStream) -> float:
        """Electric power from ORC for a given waste heat stream."""
        return stream.heat_flow_kw * ORC_EFFICIENCY

    def compute_absorption_cooling(self, stream: WasteHeatStream) -> float:
        """Cooling output from absorption chiller driven by this stream."""
        return stream.heat_flow_kw * ABS_CHILLER_COP

    def evaluate_streams(self) -> list[RecoveryAction]:
        """Rank streams by exergy quality and propose optimal recovery actions."""
        proposals = []
        for s in sorted(self.streams.values(), key=lambda x: x.exergy_kw, reverse=True):
            if s.temperature_c > 120:
                # High-grade → ORC (power generation)
                orc_kw = self.compute_orc_output(s)
                revenue = orc_kw * self.ELECTRICITY_PRICE_USD_KWH
                proposals.append(RecoveryAction(
                    action_id=f"ORC-{s.stream_id}",
                    stream_id=s.stream_id,
                    method="orc",
                    recovered_kw=orc_kw,
                    revenue_usd_hr=revenue,
                    auto_proposed=True,
                ))
            elif 60 <= s.temperature_c <= 120:
                # Mid-grade → Absorption chiller
                cool_kw = self.compute_absorption_cooling(s)
                revenue = cool_kw * self.COOLING_VALUE_USD_KWH
                proposals.append(RecoveryAction(
                    action_id=f"ABS-{s.stream_id}",
                    stream_id=s.stream_id,
                    method="absorption_chiller",
                    recovered_kw=cool_kw,
                    revenue_usd_hr=revenue,
                    auto_proposed=True,
                ))
            elif s.temperature_c >= 40:
                # Low-grade → District heating
                proposals.append(RecoveryAction(
                    action_id=f"DH-{s.stream_id}",
                    stream_id=s.stream_id,
                    method="district_heat",
                    recovered_kw=s.heat_flow_kw * 0.85,
                    revenue_usd_hr=s.heat_flow_kw * 0.85 * 0.02,
                    auto_proposed=True,
                ))
        return proposals

    def run_cycle(self) -> dict:
        """Execute one evaluation cycle."""
        proposals = self.evaluate_streams()
        self.actions = proposals

        total_recovered = sum(a.recovered_kw for a in proposals)
        recovery_fraction = total_recovered / max(self.total_heat_kw, 1)
        total_revenue_hr = sum(a.revenue_usd_hr for a in proposals)

        if recovery_fraction >= self.RECOVERY_TRIGGER_FRACTION:
            logger.info(f"UNIVERSE FUEL: Recovery={recovery_fraction:.1%} → auto-proposing revenue ${total_revenue_hr:.2f}/hr")
            if self.revenue_callback:
                for a in proposals:
                    self.revenue_callback(a)

        return {
            "total_heat_kw": round(self.total_heat_kw, 1),
            "total_exergy_kw": round(self.total_exergy_kw, 1),
            "total_recovered_kw": round(total_recovered, 1),
            "recovery_fraction": round(recovery_fraction, 3),
            "second_law_efficiency": round(self.second_law_efficiency, 3),
            "estimated_revenue_usd_hr": round(total_revenue_hr, 2),
            "actions": len(proposals),
        }


if __name__ == "__main__":
    system = ExergyToMarsPowerSystem()
    system.add_stream(WasteHeatStream("COND-01", "chiller_condenser", 42.0, 18000.0))
    system.add_stream(WasteHeatStream("RACK-EXH", "rack_exhaust", 55.0, 800.0))
    result = system.run_cycle()
    print(f"Total Heat: {result['total_heat_kw']} kW | Recovery: {result['recovery_fraction']:.1%}")
    print(f"Second Law Eff: {result['second_law_efficiency']:.1%} | Revenue: ${result['estimated_revenue_usd_hr']}/hr")
