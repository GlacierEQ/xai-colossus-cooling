"""
Colossus cooling thermal reality — first-principles heat balance.

Q = m_dot * c_p * ΔT  (water)
PUE-style efficiency index from cooling power vs IT load.

No placeholders. SI units.
"""
from __future__ import annotations

# Specific heat capacity of liquid water (J / (kg·K))
CP_WATER = 4184.0
# Density approximation for volume↔mass at ~25°C (kg/L)
RHO_WATER = 0.997


class ThermalState:
    """Immutable-ish thermal snapshot (plain class for py3.9 importlib safety)."""

    __slots__ = (
        "it_load_mw",
        "coolant_flow_kg_s",
        "inlet_c",
        "outlet_c",
        "cooling_electrical_mw",
    )

    def __init__(
        self,
        it_load_mw: float,
        coolant_flow_kg_s: float,
        inlet_c: float,
        outlet_c: float,
        cooling_electrical_mw: float,
    ) -> None:
        self.it_load_mw = it_load_mw
        self.coolant_flow_kg_s = coolant_flow_kg_s
        self.inlet_c = inlet_c
        self.outlet_c = outlet_c
        self.cooling_electrical_mw = cooling_electrical_mw

    @property
    def delta_t_c(self) -> float:
        return self.outlet_c - self.inlet_c

    @property
    def heat_reject_mw(self) -> float:
        """Sensible heat removed by coolant stream (MW)."""
        # Q (W) = m_dot (kg/s) * cp (J/kg·K) * ΔT (K)
        q_w = self.coolant_flow_kg_s * CP_WATER * self.delta_t_c
        return q_w / 1_000_000.0

    @property
    def heat_margin_mw(self) -> float:
        """Positive => coolant can reject more than IT load."""
        return self.heat_reject_mw - self.it_load_mw

    @property
    def pue_cooling(self) -> float:
        """
        Simplified partial PUE: (IT + cooling electrical) / IT.
        Returns inf if IT load is 0.
        """
        if self.it_load_mw <= 0:
            return float("inf")
        return (self.it_load_mw + self.cooling_electrical_mw) / self.it_load_mw


def flow_kg_s_from_lpm(lpm: float) -> float:
    """Liters/min → kg/s for water."""
    liters_per_s = lpm / 60.0
    return liters_per_s * RHO_WATER


def required_flow_kg_s(it_load_mw: float, delta_t_c: float) -> float:
    """Minimum mass flow to reject IT load at given ΔT."""
    if delta_t_c <= 0:
        raise ValueError("delta_t_c must be > 0")
    if it_load_mw < 0:
        raise ValueError("it_load_mw must be >= 0")
    # m_dot = Q / (cp * ΔT); Q in W
    q_w = it_load_mw * 1_000_000.0
    return q_w / (CP_WATER * delta_t_c)


def assess_loop(
    it_load_mw: float,
    flow_lpm: float,
    inlet_c: float,
    outlet_c: float,
    cooling_electrical_mw: float,
    throttle_margin_mw: float = 0.0,
) -> dict:
    """
    Assess a cooling loop. status:
      NOMINAL | THROTTLE_RISK | CRITICAL
    """
    flow = flow_kg_s_from_lpm(flow_lpm)
    state = ThermalState(
        it_load_mw=it_load_mw,
        coolant_flow_kg_s=flow,
        inlet_c=inlet_c,
        outlet_c=outlet_c,
        cooling_electrical_mw=cooling_electrical_mw,
    )
    margin = state.heat_margin_mw
    if state.delta_t_c <= 0:
        status = "CRITICAL"
        reason = "non_positive_delta_t"
    elif margin < 0:
        status = "CRITICAL"
        reason = "insufficient_heat_rejection"
    elif margin < throttle_margin_mw:
        status = "THROTTLE_RISK"
        reason = "thin_thermal_margin"
    else:
        status = "NOMINAL"
        reason = "margin_ok"

    return {
        "status": status,
        "reason": reason,
        "it_load_mw": it_load_mw,
        "heat_reject_mw": round(state.heat_reject_mw, 4),
        "heat_margin_mw": round(margin, 4),
        "delta_t_c": round(state.delta_t_c, 4),
        "flow_kg_s": round(flow, 4),
        "flow_lpm": flow_lpm,
        "pue_cooling": (
            round(state.pue_cooling, 4)
            if state.pue_cooling != float("inf")
            else None
        ),
        "required_flow_kg_s_for_delta": (
            round(required_flow_kg_s(it_load_mw, state.delta_t_c), 4)
            if state.delta_t_c > 0
            else None
        ),
    }
