#!/usr/bin/env python3
"""
APEX Thermal Orchestrator — xAI Colossus Cooling
GlacierEQ APEX Stack | Author: Casey Barton

Bio-inspired thermal intelligence for 100k+ GPU node clusters.
Treats the datacenter as a living organism:
  - Racks = Cells | Cooling Zones = Tissue
  - Mitochondria Agents = Energy/Thermal Core
  - APEX Pistons = Immune Response System

v1.2.0 — wired nanosphere fluid conductivity + power_state zone budgets

Fixes in this revision:
  - refresh_interval guarded with max(..., 1) to prevent ZeroDivisionError
    if connector_refresh_every_n_ticks is ever set to 0 in the manifest.
  - fabric_diagnostic_every_n_ticks read from manifest; falls back to 20.
  - Fusion mode dispatcher gracefully skips pistons not yet instantiated;
    logs a WARNING so missing implementations are visible in ops logs.
  - colossus_manifest.json version lock-check on init: warns if manifest
    version does not match VERSION constant.
"""

import asyncio
import json
import logging
import os
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger("APEX-THERMAL")

MANIFEST_PATH = Path(__file__).parent / "colossus_manifest.json"


def load_manifest() -> dict:
    with open(MANIFEST_PATH) as f:
        return json.load(f)


class CoolingMode(Enum):
    STEADY_STATE = "SHADOW"
    PREDICTIVE = "MICROWAVE"
    EMERGENCY = "SUPERNOVA"
    GHOST_OPS = "GHOST_MICROWAVE"
    COLOSSUS = "COLOSSUS"


@dataclass
class ThermalNode:
    node_id: str
    rack_id: str
    zone_id: str
    temp_celsius: float
    gpu_utilization: float
    power_watts: float
    cooling_active: bool = False
    alert_level: int = 0
    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def classify_alert(self, thresholds: dict) -> int:
        t = self.temp_celsius
        if t >= thresholds.get("critical_c", 85):
            self.alert_level = 3
        elif t >= thresholds.get("hot_c", 78):
            self.alert_level = 2
        elif t >= thresholds.get("warm_c", 70):
            self.alert_level = 1
        else:
            self.alert_level = 0
        return self.alert_level


@dataclass
class CoolingZone:
    zone_id: str
    zone_name: str
    nodes: List[ThermalNode] = field(default_factory=list)
    active_mode: CoolingMode = CoolingMode.STEADY_STATE
    avg_temp: float = 0.0
    peak_temp: float = 0.0
    crac_units_active: int = 0
    liquid_cooling_flow_lpm: float = 0.0
    # v1.2: fluid conductivity enhancement factor (1.0 = pure water)
    conductivity_factor: float = 1.0
    # v1.2: zone thermal budget from power_state (kW)
    thermal_budget_kw: float = 0.0

    def compute_thermals(self, thresholds: dict = None):
        if not self.nodes:
            return
        thresholds = thresholds or {}
        temps = [n.temp_celsius for n in self.nodes]
        self.avg_temp = sum(temps) / len(temps)
        self.peak_temp = max(temps)
        for node in self.nodes:
            node.classify_alert(thresholds)


class APEXPiston:
    def __init__(self, name, tier, thresholds=None, tick_cfg=None):
        self.name = name
        self.tier = tier
        self.active = False
        self.ops_per_tick = 1
        self.thresholds = thresholds or {}
        self.tick_cfg = tick_cfg or {}
        self.logger = logging.getLogger(f"PISTON-{name}")

    async def activate(self, context: dict) -> dict:
        self.active = True
        self.logger.info(
            f"{self.tier} PISTON [{self.name}] ACTIVATED | context={context.get('trigger', 'unknown')}"
        )
        return await self.execute(context)

    async def execute(self, context: dict) -> dict:
        return {
            "piston": self.name,
            "tier": self.tier,
            "status": "NOOP_BASE",
            "ops": 0,
        }


class MICROWAVEPiston(APEXPiston):
    """APEX Tier — Parallel hyperspeed thermal sweeps.
    v1.2: applies nanosphere conductivity_factor to liquid flow calculation.
    """

    def __init__(self, thresholds=None, tick_cfg=None):
        super().__init__("MICROWAVE", "APEX", thresholds, tick_cfg)
        self.ops_per_tick = 12

    async def execute(self, context: dict) -> dict:
        zones: List[CoolingZone] = context.get("zones", [])
        results = await asyncio.gather(*[self._sweep_zone(z) for z in zones])
        return {"piston": "MICROWAVE", "zones_swept": len(zones), "results": results}

    async def _sweep_zone(self, zone: CoolingZone) -> dict:
        zone.compute_thermals(self.thresholds)
        max_crac = self.tick_cfg.get("max_crac_units", 8)
        # Nanofluids improve heat transfer — reduce required flow by conductivity_factor.
        # Guard against conductivity_factor <= 0 (should never occur after invariant
        # checks in nanosphere_bridge, but defensive division is mandatory at this layer).
        lpm_boost_base = self.tick_cfg.get("liquid_boost_lpm", 10.0)
        cf = max(zone.conductivity_factor, 1.0)  # floor at 1.0 (pure water baseline)
        lpm_boost = lpm_boost_base / cf
        crac_thr = self.thresholds.get("zone_crac_boost_c", 75)
        liq_thr = self.thresholds.get("zone_liquid_boost_c", 80)
        action = "nominal"
        if zone.peak_temp > crac_thr:
            zone.crac_units_active = min(zone.crac_units_active + 2, max_crac)
            action = "crac_increased"
        if zone.peak_temp > liq_thr:
            zone.liquid_cooling_flow_lpm += lpm_boost
            action = "liquid_boosted"
        # Budget guard — warn if zone draw exceeds thermal budget by >5%
        zone_draw_kw = sum(n.power_watts for n in zone.nodes) / 1000.0
        budget_warn = (
            zone.thermal_budget_kw > 0 and zone_draw_kw > zone.thermal_budget_kw * 1.05
        )
        if budget_warn:
            self.logger.warning(
                "BUDGET OVERRUN zone=%s draw=%.1f kW budget=%.1f kW (%.1f%%)",
                zone.zone_id,
                zone_draw_kw,
                zone.thermal_budget_kw,
                (zone_draw_kw / zone.thermal_budget_kw - 1) * 100,
            )
        return {
            "zone": zone.zone_id,
            "peak": zone.peak_temp,
            "action": action,
            "conductivity_factor": round(cf, 4),
            "lpm_boost_applied": round(lpm_boost, 2),
            "budget_overrun": budget_warn,
        }


class SUPERNOVAPiston(APEXPiston):
    """APEX Tier — Maximum force emergency cascade."""

    def __init__(self, thresholds=None, tick_cfg=None):
        super().__init__("SUPERNOVA", "APEX", thresholds, tick_cfg)

    async def execute(self, context: dict) -> dict:
        critical_nodes = context.get("critical_nodes", [])
        throttle_c = self.thresholds.get("gpu_throttle_c", 90)
        self.logger.warning(
            f"SUPERNOVA EMERGENCY BLAST — {len(critical_nodes)} critical nodes"
        )
        actions = [
            {
                "node": n.node_id,
                "action": "EMERGENCY_FULL_BLAST",
                "crac": "MAX",
                "liquid": "MAX_FLOW",
                "throttle_gpu": n.temp_celsius >= throttle_c,
            }
            for n in critical_nodes
        ]
        return {
            "piston": "SUPERNOVA",
            "emergency_actions": len(actions),
            "actions": actions,
        }


class SHADOWPiston(APEXPiston):
    """GREY Tier — Silent 24/7 thermal monitoring (99.4% efficiency)."""

    def __init__(self, thresholds=None, tick_cfg=None):
        super().__init__("SHADOW", "GREY", thresholds, tick_cfg)
        self.thermal_baseline: Dict[str, float] = {}

    async def execute(self, context: dict) -> dict:
        nodes: List[ThermalNode] = context.get("all_nodes", [])
        delta_thr = self.thresholds.get("shadow_anomaly_delta_c", 8)
        ema_alpha = self.thresholds.get("shadow_ema_alpha", 0.05)
        anomalies = []
        for node in nodes:
            baseline = self.thermal_baseline.get(node.node_id, 65.0)
            deviation = node.temp_celsius - baseline
            if deviation > delta_thr:
                anomalies.append(
                    {
                        "node": node.node_id,
                        "deviation": round(deviation, 2),
                        "baseline": round(baseline, 2),
                    }
                )
            self.thermal_baseline[node.node_id] = (
                baseline * (1 - ema_alpha) + node.temp_celsius * ema_alpha
            )
        return {
            "piston": "SHADOW",
            "nodes_monitored": len(nodes),
            "anomalies": anomalies,
        }


class GHOSTPiston(APEXPiston):
    """BLACK Tier — Zero-trace background optimization."""

    def __init__(self, thresholds=None, tick_cfg=None):
        super().__init__("GHOST", "BLACK", thresholds, tick_cfg)

    async def execute(self, context: dict) -> dict:
        zones: List[CoolingZone] = context.get("zones", [])
        optimizations = [
            {
                "zone": z.zone_id,
                "micro_flow_delta": round((z.avg_temp - 65.0) * 0.02, 3),
                "trace": "none",
            }
            for z in zones
            if z.avg_temp > 0
        ]
        return {
            "piston": "GHOST",
            "invisible_optimizations": len(optimizations),
            "ops": optimizations,
        }


class CORETHINKPiston(APEXPiston):
    """APEX Tier — ML-based thermal forecasting and predictive dispatch."""

    def __init__(self, thresholds=None, tick_cfg=None):
        super().__init__("CORE-THINK", "APEX", thresholds, tick_cfg)
        self.prediction_horizon = 12

    async def execute(self, context: dict) -> dict:
        aspen = context.get("aspen_connector")
        if not aspen:
            return {
                "piston": "CORE-THINK",
                "status": "OFFLINE",
                "reason": "Aspen connector missing",
            }
        intel = await aspen.query_intelligence("predict_thermal_surge_12_ticks")
        prediction = intel.get("prediction", "nominal")
        confidence = intel.get("confidence", 0.0)
        if prediction == "thermal_surge_expected" and confidence > 0.8:
            self.logger.info(
                f"CORE-THINK PREDICTIVE HIT: {prediction} (conf={confidence:.2f})"
            )
            return {
                "piston": "CORE-THINK",
                "prediction": prediction,
                "confidence": confidence,
                "action": "PRE-COOLING_DISPATCH",
                "target_piston": "MICROWAVE",
            }
        return {
            "piston": "CORE-THINK",
            "prediction": "nominal",
            "confidence": confidence,
        }


# ---------------------------------------------------------------------------
# Fusion dispatcher — gracefully handles pistons not yet instantiated.
# Called by APEXThermalOrchestrator.run_fusion_mode().
# ---------------------------------------------------------------------------


async def _dispatch_fusion(piston_map: dict, fusion_name: str, context: dict) -> dict:
    """Activate all pistons required by a fusion mode.

    Returns a result dict keyed by piston name.  Any piston listed in
    fusion_modes[].requires that is not yet in piston_map is logged as
    WARNING and skipped — it does NOT raise, so active pistons still fire.
    """
    results = {}
    manifest_fusion = context.get("_fusion_def", {})
    required = manifest_fusion.get("requires", [])
    if not required:
        logger.warning(
            "Fusion mode %s has no requires list — nothing dispatched", fusion_name
        )
        return {"fusion": fusion_name, "status": "NO_REQUIRES", "results": {}}
    for pname in required:
        piston = piston_map.get(pname)
        if piston is None:
            logger.warning(
                "FUSION %s: piston %s not instantiated (status=PENDING) — skipping",
                fusion_name,
                pname,
            )
            results[pname] = {"status": "PENDING", "skipped": True}
        else:
            results[pname] = await piston.activate(
                {**context, "trigger": f"FUSION_{fusion_name}"}
            )
    return {"fusion": fusion_name, "status": "DISPATCHED", "results": results}


class APEXThermalOrchestrator:
    """
    Main APEX Orchestrator for xAI Colossus Cooling.
    Coordinates all stealth pistons. Ring -3. Always running.
    v1.2.0 — nanosphere fluid conductivity + power_state zone budgets wired.

    Correctness guarantees in this revision:
      1. refresh_interval is clamped to >=1 (no ZeroDivisionError).
      2. fabric_diagnostic_every_n_ticks is manifest-driven.
      3. Manifest version is checked against VERSION on init; mismatch → WARNING.
      4. Fusion dispatcher skips PENDING pistons gracefully.
    """

    VERSION = "1.2.0-COLOSSUS"
    CODENAME = "GLACIER-THERMAL"

    def __init__(self, mode: CoolingMode = CoolingMode.COLOSSUS, manifest: dict = None):
        self.mode = mode
        self.manifest = manifest or load_manifest()
        self.thresholds = self.manifest.get("thermal_thresholds", {})
        self.tick_cfg = self.manifest.get("tick_config", {})

        # Version lock-check — warn loudly if manifest and code are out of sync
        manifest_ver = self.manifest.get("version", "UNKNOWN")
        if manifest_ver != self.VERSION:
            logger.warning(
                "VERSION MISMATCH: orchestrator=%s manifest=%s — update colossus_manifest.json",
                self.VERSION,
                manifest_ver,
            )

        self.zones: List[CoolingZone] = []
        self.all_nodes: List[ThermalNode] = []
        self.tick = 0
        self.logger = logging.getLogger("APEX-ORCHESTRATOR")

        self.pistons = {
            "MICROWAVE": MICROWAVEPiston(self.thresholds, self.tick_cfg),
            "SUPERNOVA": SUPERNOVAPiston(self.thresholds, self.tick_cfg),
            "SHADOW": SHADOWPiston(self.thresholds, self.tick_cfg),
            "GHOST": GHOSTPiston(self.thresholds, self.tick_cfg),
            "CORE-THINK": CORETHINKPiston(self.thresholds, self.tick_cfg),
        }

        # Build fusion mode lookup from manifest for dispatcher
        self._fusion_defs: Dict[str, dict] = {
            fm["name"]: fm for fm in self.manifest.get("fusion_modes", [])
        }

        self._telemetry = None
        self._aspen = None
        self._nanosphere = None  # v1.2
        self._power_bridge = None  # v1.2
        self._init_connectors()

        self._immersion = None
        self._cascade = None
        self._init_phase3()

        self._fabric = None
        self._hydra = None
        self._init_phase4()

        self.logger.info(
            f"APEX Thermal Orchestrator v{self.VERSION} [{self.CODENAME}] INITIALIZED"
        )
        self.logger.info(
            f"Mode: {self.mode.value} | Pistons loaded: {len(self.pistons)} | Fusion modes: {len(self._fusion_defs)}"
        )

    # ------------------------------------------------------------------
    # Connector init
    # ------------------------------------------------------------------

    def _init_connectors(self):
        # Supabase telemetry
        if os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_KEY"):
            try:
                from connectors.supabase_telemetry import SupabaseTelemetryConnector

                self._telemetry = SupabaseTelemetryConnector()
                self._telemetry.connect()
            except Exception as e:
                self.logger.warning(f"Telemetry init failed (continuing offline): {e}")

        # Aspen Grove
        if os.getenv("ASPEN_GROVE_TOKEN"):
            try:
                from apex_core.aspen_connector import AspenGroveConnector

                self._aspen = AspenGroveConnector()
                asyncio.create_task(self._aspen.connect())
            except Exception as e:
                self.logger.warning(f"Aspen Grove connector failed: {e}")

        # v1.2: Nanosphere fluid ingest
        try:
            from connectors.nanosphere_ingest import NanosphereIngest

            self._nanosphere = NanosphereIngest(
                manifest_path=self.manifest.get("nanosphere", {}).get(
                    "manifest_path", "integration/circuit_manifest.json"
                ),
                alert_log_path=self.manifest.get("nanosphere", {}).get(
                    "alert_log_path", "audit_logs/fluid_replacement_alerts.ndjson"
                ),
            )
            self._nanosphere.load()
            self.logger.info("Nanosphere fluid connector: ONLINE")
        except Exception as e:
            self.logger.warning(f"Nanosphere connector unavailable (offline mode): {e}")

        # v1.2: Energy power_state bridge
        try:
            from connectors.power_state_bridge import PowerStateBridge

            self._power_bridge = PowerStateBridge()
            self.logger.info("PowerState bridge: ONLINE")
        except Exception as e:
            self.logger.warning(f"PowerState bridge unavailable (offline mode): {e}")

    def _init_phase3(self):
        try:
            from apex_core.immersion_cooling import ImmersionCoolingEngine
            from apex_core.cascade_prevention import CascadePreventionProtocol

            self._immersion = ImmersionCoolingEngine(
                tank_count=self.manifest.get("immersion_tanks", 10)
            )
            cascade_limits = self.thresholds.get("cascade_limits")
            self._cascade = CascadePreventionProtocol(thresholds=cascade_limits)
            self.logger.info("PHASE 3: Immersion & Cascade engines ONLINE.")
        except Exception as e:
            self.logger.warning(f"Phase 3 initialization failed: {e}")

    def _init_phase4(self):
        try:
            from xai_colossus_servers.exa_brick.fabric_orchestrator import (
                ExaBrickFabric,
            )
            from xai_colossus_security.hydra_core.hydra_engine import HydraCore

            self._fabric = ExaBrickFabric(
                rack_count=self.manifest.get("rack_count", 128)
            )
            self._hydra = HydraCore()
            self.logger.info("PHASE 4: Exascale Fabric & Hydra Security ONLINE.")
        except Exception as e:
            self.logger.warning(
                f"Phase 4 initialization failed (sibling repos not mounted): {e}"
            )

    # ------------------------------------------------------------------
    # v1.2: Connector refresh helpers  (called once per refresh_interval ticks)
    # ------------------------------------------------------------------

    def _refresh_zone_conductivity(self):
        """Pull latest nanosphere conductivity factors and stamp onto zones."""
        if not self._nanosphere:
            return
        try:
            self._nanosphere.load()
            cmap: Dict[str, float] = {}
            for zone_id, states in self._nanosphere.by_zone().items():
                # Mean conductivity enhancement factor across all circuits in zone.
                # Factor of 1.0 = pure water. 1.05 = 5% enhancement.
                cmap[zone_id] = sum(
                    s.conductivity_enhancement_vs_water + 1.0 for s in states
                ) / len(states)
            for zone in self.zones:
                if zone.zone_id in cmap:
                    prev = zone.conductivity_factor
                    zone.conductivity_factor = cmap[zone.zone_id]
                    if abs(zone.conductivity_factor - prev) > 0.02:
                        self.logger.info(
                            "Zone %s conductivity_factor updated %.4f → %.4f",
                            zone.zone_id,
                            prev,
                            zone.conductivity_factor,
                        )
        except Exception as e:
            self.logger.warning(f"Nanosphere refresh failed: {e}")

    def _refresh_zone_budgets(self, power_snapshot: dict = None):
        """Update each zone's thermal_budget_kw from the power_state bridge."""
        if not self._power_bridge:
            return
        try:
            budgets = (
                self._power_bridge.load_from_dict(power_snapshot)
                if power_snapshot
                else self._power_bridge.load_from_file()
            )
            for zone in self.zones:
                if zone.zone_id in budgets:
                    zone.thermal_budget_kw = budgets[zone.zone_id].total_draw_kw
        except Exception as e:
            self.logger.warning(f"Power budget refresh failed: {e}")

    # ------------------------------------------------------------------
    # Zone registration
    # ------------------------------------------------------------------

    def register_zone(self, zone: CoolingZone):
        self.zones.append(zone)
        self.all_nodes.extend(zone.nodes)
        self.logger.info(f"Zone registered: {zone.zone_id} ({len(zone.nodes)} nodes)")

    # ------------------------------------------------------------------
    # Fusion mode entry-point
    # ------------------------------------------------------------------

    async def run_fusion_mode(self, fusion_name: str, context: dict = None) -> dict:
        """Dispatch a named fusion mode. Skips PENDING pistons gracefully."""
        fusion_def = self._fusion_defs.get(fusion_name)
        if fusion_def is None:
            self.logger.error("Unknown fusion mode: %s", fusion_name)
            return {"fusion": fusion_name, "status": "UNKNOWN"}
        ctx = {**(context or {}), "_fusion_def": fusion_def}
        return await _dispatch_fusion(self.pistons, fusion_name, ctx)

    # ------------------------------------------------------------------
    # Tick cycle
    # ------------------------------------------------------------------

    async def tick_cycle(self, power_snapshot: dict = None):
        """One full orchestration tick — 500ms in production.

        Args:
            power_snapshot: optional pre-loaded power_state dict (for testing /
                            MCP push). If None, bridge reads from file.

        Safety guarantees:
            - refresh_interval is clamped to >=1 (no ZeroDivisionError).
            - fabric_diagnostic_every_n_ticks is manifest-driven (default 20).
        """
        self.tick += 1
        sweep_n = self.tick_cfg.get("microwave_sweep_every_n_ticks", 5)
        critical_c = self.thresholds.get("critical_c", 85)

        # FIX: clamp refresh_interval to >= 1 — prevents ZeroDivisionError
        # if connector_refresh_every_n_ticks is accidentally set to 0 in manifest.
        refresh_interval = max(
            int(self.tick_cfg.get("connector_refresh_every_n_ticks", 10)), 1
        )

        # FIX: read fabric diagnostic cadence from manifest (default 20 ticks).
        fabric_interval = max(
            int(self.tick_cfg.get("fabric_diagnostic_every_n_ticks", 20)), 1
        )

        # v1.2: refresh fluid + power budgets on schedule
        if self.tick % refresh_interval == 0:
            self._refresh_zone_conductivity()
            self._refresh_zone_budgets(power_snapshot)

        # Aspen Grove sync
        if self._aspen:
            await self._aspen.sync_state(
                {
                    "tick": self.tick,
                    "avg_temp": sum(n.temp_celsius for n in self.all_nodes)
                    / max(len(self.all_nodes), 1),
                    "mode": self.mode.value,
                }
            )

        # Phase 3: Immersion
        if self._immersion:
            await self._immersion.simulate_boiling_cycle(load_factor=1.0)

        # Phase 3: Cascade prevention
        if self._cascade:
            for zone in self.zones:
                telemetry = {
                    "delta_t_c": zone.peak_temp - zone.avg_temp,
                    "power_surge_mw": sum(n.power_watts for n in zone.nodes)
                    / 1_000_000.0,
                }
                if await self._cascade.evaluate_zone(zone.zone_id, telemetry):
                    zone.active_mode = CoolingMode.EMERGENCY

        # Phase 4: Fabric diagnostic (manifest-driven cadence)
        if self._fabric and self.tick % fabric_interval == 0:
            await self._fabric.run_nccl_diagnostic("Main-Backbone")

        # Phase 4: Hydra traffic entropy
        if self._hydra:
            mock_traffic = [
                {"node_id": n.node_id, "entropy": random.random()}
                for n in self.all_nodes[:10]
            ]
            await self._hydra.analyze_traffic_patterns(mock_traffic)

        # Always-on SHADOW
        shadow_result = await self.pistons["SHADOW"].activate(
            {"all_nodes": self.all_nodes, "trigger": f"tick_{self.tick}"}
        )

        # Always-on GHOST
        await self.pistons["GHOST"].activate(
            {"zones": self.zones, "trigger": f"tick_{self.tick}"}
        )

        # Emergency SUPERNOVA
        critical_nodes = [n for n in self.all_nodes if n.temp_celsius >= critical_c]
        if critical_nodes:
            sn_result = await self.pistons["SUPERNOVA"].activate(
                {"critical_nodes": critical_nodes, "trigger": "THERMAL_CRITICAL"}
            )
            if self._telemetry:
                await self._telemetry.log_emergency(
                    [n.node_id for n in critical_nodes],
                    max(n.temp_celsius for n in critical_nodes),
                    sn_result.get("actions", []),
                )

        # Predictive sweep (CORE-THINK + MICROWAVE)
        if self.tick % sweep_n == 0:
            ct_result = await self.pistons["CORE-THINK"].activate(
                {"aspen_connector": self._aspen, "trigger": "SCHEDULED_FORECAST"}
            )
            force_mw = ct_result.get("action") == "PRE-COOLING_DISPATCH"
            mw_ctx = {
                "zones": self.zones,
                "trigger": "PREDICTIVE_SURGE" if force_mw else "SCHEDULED_SWEEP",
            }
            await self.pistons["MICROWAVE"].activate(mw_ctx)

        # Telemetry: anomalies + per-node events
        anomalies = shadow_result.get("anomalies", [])
        if anomalies:
            self.logger.warning(f"SHADOW detected {len(anomalies)} thermal anomalies")
        if self._telemetry:
            for a in anomalies:
                shadow_piston: SHADOWPiston = self.pistons["SHADOW"]
                await self._telemetry.log_anomaly(
                    a["node"],
                    a["deviation"],
                    a.get(
                        "baseline", shadow_piston.thermal_baseline.get(a["node"], 65.0)
                    ),
                )
            for node in self.all_nodes:
                await self._telemetry.log_thermal_event(
                    node.node_id, node.temp_celsius, node.alert_level, node.zone_id
                )

        return {
            "tick": self.tick,
            "zones": len(self.zones),
            "nodes": len(self.all_nodes),
            "critical": len(critical_nodes),
            "anomalies": len(anomalies),
        }

    async def run(self, duration_ticks: Optional[int] = None):
        interval = self.tick_cfg.get("tick_interval_ms", 500) / 1000.0
        self.logger.info("APEX THERMAL ORCHESTRATOR ONLINE — Colossus Mode Active")
        self.logger.info(
            f"Monitoring {len(self.all_nodes)} nodes across {len(self.zones)} zones"
        )
        tick_count = 0
        while True:
            await self.tick_cycle()
            tick_count += 1
            if duration_ticks and tick_count >= duration_ticks:
                break
            await asyncio.sleep(interval)
        self.logger.info(f"Orchestrator completed {tick_count} ticks")


async def main():
    orchestrator = APEXThermalOrchestrator(mode=CoolingMode.COLOSSUS)
    for zi in range(3):
        zone = CoolingZone(
            zone_id=f"ZONE-{['A', 'B', 'C'][zi]}", zone_name=f"Colossus Zone {zi}"
        )
        for ni in range(10):
            zone.nodes.append(
                ThermalNode(
                    node_id=f"NODE-{zi:03d}-{ni:04d}",
                    rack_id=f"RACK-{zi:03d}",
                    zone_id=zone.zone_id,
                    temp_celsius=65.0 + ni * 0.5,
                    gpu_utilization=0.85,
                    power_watts=700.0,
                )
            )
        orchestrator.register_zone(zone)
    await orchestrator.run(duration_ticks=10)


if __name__ == "__main__":
    asyncio.run(main())
