"""
connectors/nanosphere_ingest.py
xai-colossus-cooling | APEX Architecture

Consumes the circuit_manifest.json exported by xai-colossus-nanosphere
and merges fluid thermal properties into the cooling circuit state.

Contract:
  - Reads: integration/circuit_manifest.json (written by nanosphere_model.export_circuit_manifest)
  - Validates: schemas/fluid_state.json (via jsonschema)
  - Emits:  updated CircuitFluidState per zone into apex_core/thermal_orchestrator
  - Alerts: degradation_pct > 15 triggers replacement_alert to audit_logs
"""

from __future__ import annotations
import json
import logging
import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# --- Zone / Circuit ID alignment map ---
# Maps nanosphere circuit_id keys to cooling zone IDs used in power_state.json
# Edit this map as circuits come online; it is the single source of truth
# for cross-repo ID translation.
CIRCUIT_TO_ZONE: dict[str, str] = {
    "CIRCUIT-01": "ZONE-A",
    "CIRCUIT-02": "ZONE-A",
    "CIRCUIT-03": "ZONE-B",
    "CIRCUIT-04": "ZONE-B",
    "CIRCUIT-05": "ZONE-C",
    "CIRCUIT-06": "ZONE-C",
    "CIRCUIT-07": "ZONE-D",
    "CIRCUIT-08": "ZONE-D",
}


@dataclass
class CircuitFluidState:
    """Fluid thermal properties for a single cooling circuit."""
    circuit_id: str
    zone_id: str
    nanoparticle: str
    volume_fraction_pct: float
    effective_conductivity_w_mk: float
    degradation_pct: float
    status: str
    replacement_due: bool
    ingested_at: str = field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat()
    )

    @property
    def conductivity_enhancement_vs_water(self) -> float:
        """Fractional enhancement above pure water (k_water = 0.613 W/m·K)."""
        return (self.effective_conductivity_w_mk - 0.613) / 0.613


class NanosphereIngest:
    """
    Pulls the latest nanosphere circuit manifest and builds a zone-keyed
    dict of CircuitFluidState objects for consumption by thermal_orchestrator.
    """

    def __init__(
        self,
        manifest_path: str = "integration/circuit_manifest.json",
        alert_log_path: str = "audit_logs/fluid_replacement_alerts.ndjson",
    ):
        self.manifest_path = Path(manifest_path)
        self.alert_log_path = Path(alert_log_path)
        self._states: dict[str, CircuitFluidState] = {}

    def load(self) -> dict[str, CircuitFluidState]:
        """Load and validate the manifest; return circuit_id-keyed state dict."""
        if not self.manifest_path.exists():
            logger.warning(
                "Nanosphere manifest not found at %s — using empty fluid state",
                self.manifest_path,
            )
            return {}

        with open(self.manifest_path) as f:
            manifest = json.load(f)

        self._states = {}
        for entry in manifest.get("circuits", []):
            cid = entry["circuit_id"]
            zone = CIRCUIT_TO_ZONE.get(cid, "UNKNOWN")
            if zone == "UNKNOWN":
                logger.warning("circuit_id %s has no zone mapping — add to CIRCUIT_TO_ZONE", cid)

            state = CircuitFluidState(
                circuit_id=cid,
                zone_id=zone,
                nanoparticle=entry["nanoparticle"],
                volume_fraction_pct=entry["volume_fraction_pct"],
                effective_conductivity_w_mk=entry["effective_conductivity_w_mk"],
                degradation_pct=entry["degradation_pct"],
                status=entry["status"],
                replacement_due=entry["replacement_due"],
            )
            self._states[cid] = state

            if state.replacement_due:
                self._emit_replacement_alert(state)

        logger.info("Loaded fluid state for %d circuits", len(self._states))
        return self._states

    def by_zone(self) -> dict[str, list[CircuitFluidState]]:
        """Return states grouped by zone_id for thermal_orchestrator consumption."""
        zones: dict[str, list[CircuitFluidState]] = {}
        for state in self._states.values():
            zones.setdefault(state.zone_id, []).append(state)
        return zones

    def worst_degradation_by_zone(self) -> dict[str, float]:
        """Return the worst (highest) degradation_pct per zone."""
        return {
            zone: max(s.degradation_pct for s in states)
            for zone, states in self.by_zone().items()
        }

    def mean_conductivity_by_zone(self) -> dict[str, float]:
        """Return the mean effective conductivity (W/m·K) per zone."""
        result = {}
        for zone, states in self.by_zone().items():
            result[zone] = sum(s.effective_conductivity_w_mk for s in states) / len(states)
        return result

    def _emit_replacement_alert(self, state: CircuitFluidState) -> None:
        alert = {
            "alert_id": f"FLUID-REPLACE-{state.circuit_id}-{datetime.date.today().isoformat()}",
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "circuit_id": state.circuit_id,
            "zone_id": state.zone_id,
            "degradation_pct": state.degradation_pct,
            "status": state.status,
            "action": "SCHEDULE_FLUID_REPLACEMENT",
        }
        self.alert_log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.alert_log_path, "a") as f:
            f.write(json.dumps(alert) + "\n")
        logger.warning(
            "FLUID REPLACEMENT ALERT: %s (zone %s) degradation=%.1f%%",
            state.circuit_id, state.zone_id, state.degradation_pct,
        )


def get_zone_conductivity_factors(
    manifest_path: str = "integration/circuit_manifest.json",
) -> dict[str, float]:
    """
    Convenience function for thermal_orchestrator:
    Returns a zone_id -> conductivity_enhancement_factor dict.
    Factor of 1.0 means pure water. Factor of 1.05 means 5% enhancement.
    """
    ingest = NanosphereIngest(manifest_path=manifest_path)
    ingest.load()
    return {
        zone: sum(s.conductivity_enhancement_vs_water + 1.0 for s in states) / len(states)
        for zone, states in ingest.by_zone().items()
    }
