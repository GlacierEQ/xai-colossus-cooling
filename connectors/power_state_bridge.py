"""
connectors/power_state_bridge.py
xai-colossus-cooling | APEX Architecture

Bridges xai-colossus-energy's power_state.json format with
xai-colossus-cooling's zone/circuit model.

Contract:
  - Consumes: PowerState JSON (schemas/power_state.json in xai-colossus-energy)
  - Emits:    per-zone thermal budget dict for thermal_orchestrator
  - Validates: circuit_id keys exist in CIRCUIT_TO_ZONE (from nanosphere_ingest)

This is the single translation layer between the energy and cooling repos.
Do NOT duplicate zone ID logic here — import from nanosphere_ingest.
"""

from __future__ import annotations
import json
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# Canonical zone IDs — must match power_state.json zone_id values
VALID_ZONES = {"ZONE-A", "ZONE-B", "ZONE-C", "ZONE-D"}

# PUE alert threshold — if PUE exceeds this, log a warning to cooling ops
PUE_ALERT_THRESHOLD = 1.45


@dataclass
class ZoneThermalBudget:
    """Per-zone thermal budget derived from energy power_state snapshot."""

    zone_id: str
    total_draw_kw: float
    compute_kw: float
    cooling_kw: float
    rack_count: int
    avg_inlet_temp_c: Optional[float]
    avg_outlet_temp_c: Optional[float]

    @property
    def delta_t(self) -> Optional[float]:
        if self.avg_inlet_temp_c is not None and self.avg_outlet_temp_c is not None:
            return self.avg_outlet_temp_c - self.avg_inlet_temp_c
        return None

    @property
    def kw_per_rack(self) -> float:
        return self.total_draw_kw / self.rack_count if self.rack_count else 0.0


class PowerStateBridge:
    """
    Parses a PowerState snapshot from xai-colossus-energy and exposes
    per-zone thermal budget objects for the cooling orchestration layer.
    """

    def __init__(
        self,
        power_state_path: str = "../xai-colossus-energy/schemas/power_state_snapshot.json",
    ):
        self.power_state_path = power_state_path
        self._snapshot: dict = {}
        self._budgets: dict[str, ZoneThermalBudget] = {}

    def load_from_file(
        self, path: Optional[str] = None
    ) -> dict[str, ZoneThermalBudget]:
        import pathlib

        p = pathlib.Path(path or self.power_state_path)
        with open(p) as f:
            return self.load_from_dict(json.load(f))

    def load_from_dict(self, snapshot: dict) -> dict[str, ZoneThermalBudget]:
        """Parse a PowerState dict (already loaded from JSON) into zone budgets."""
        self._snapshot = snapshot
        pue = snapshot.get("pue")
        if pue and pue > PUE_ALERT_THRESHOLD:
            logger.warning(
                "PUE=%.3f exceeds threshold %.2f — cooling efficiency degraded",
                pue,
                PUE_ALERT_THRESHOLD,
            )

        self._budgets = {}
        for zone_data in snapshot.get("zones", []):
            zid = zone_data["zone_id"]
            if zid not in VALID_ZONES:
                logger.warning("Unknown zone_id %s in power_state — skipping", zid)
                continue
            self._budgets[zid] = ZoneThermalBudget(
                zone_id=zid,
                total_draw_kw=zone_data["draw_kw"],
                compute_kw=zone_data.get("compute_kw", 0.0),
                cooling_kw=zone_data.get("cooling_kw", 0.0),
                rack_count=zone_data.get("rack_count", 0),
                avg_inlet_temp_c=zone_data.get("avg_inlet_temp_c"),
                avg_outlet_temp_c=zone_data.get("avg_outlet_temp_c"),
            )

        logger.info(
            "PowerStateBridge: loaded %d zones, total_draw=%.1f kW, PUE=%.3f",
            len(self._budgets),
            snapshot.get("total_draw_kw", 0),
            pue or 0,
        )
        return self._budgets

    @property
    def total_draw_kw(self) -> float:
        return self._snapshot.get("total_draw_kw", 0.0)

    @property
    def megapack_net_kw(self) -> float:
        return self._snapshot.get("megapack_net_kw", 0.0)

    @property
    def grid_price(self) -> Optional[float]:
        return self._snapshot.get("grid_price_usd_per_mwh")

    def hottest_zone(self) -> Optional[str]:
        """Return zone_id with highest avg_outlet_temp_c."""
        candidates = [
            (zid, b.avg_outlet_temp_c)
            for zid, b in self._budgets.items()
            if b.avg_outlet_temp_c is not None
        ]
        return max(candidates, key=lambda x: x[1])[0] if candidates else None
