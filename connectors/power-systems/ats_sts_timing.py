"""
ATS / STS Transfer Timing — Phase 6 Power Hardening
Automatic Transfer Switch (ATS)  target: < 100 ms
Static Transfer Switch (STS)     target: < 4 ms (UPS-side)
Load-Shed Tier Orchestrator      5-tier priority scheme
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class PowerSource(Enum):
    GRID_A = "grid_a"
    GRID_B = "grid_b"
    TURBINE = "turbine"
    UPS = "ups"


# ---------------------------------------------------------------------------
# Load Shed Tiers — IEEE 1668 inspired priority scheme
# Tier 1 = critical compute — NEVER shed
# Tier 5 = non-essential — shed first
# ---------------------------------------------------------------------------
LOAD_SHED_TIERS: Dict[int, dict] = {
    1: {"label": "GPU SuperPod Compute", "shed_mw": 0, "trigger_deficit_mw": 9999},
    2: {"label": "Cooling Plant Primary", "shed_mw": 0, "trigger_deficit_mw": 9999},
    3: {"label": "Storage & Networking", "shed_mw": 40, "trigger_deficit_mw": 100},
    4: {"label": "Office / NOC / Ancillary", "shed_mw": 25, "trigger_deficit_mw": 60},
    5: {
        "label": "Lighting / HVAC Non-Critical",
        "shed_mw": 15,
        "trigger_deficit_mw": 40,
    },
}


@dataclass
class TransferEvent:
    event_id: str
    from_source: str
    to_source: str
    transfer_type: str  # "ATS" | "STS"
    duration_ms: float
    success: bool
    timestamp: str


class ATSSTSController:
    """
    Simulates ATS/STS transfer and records timing for validation reports.
    In production, this wraps actual relay/SCADA API calls.
    """

    ATS_TARGET_MS = 100.0
    STS_TARGET_MS = 4.0

    def __init__(self, kafka_callback: Optional[Callable] = None):
        self.kafka_cb = kafka_callback
        self.active_source = PowerSource.GRID_A
        self.transfer_log: List[TransferEvent] = []
        self.load_shed_active: List[int] = []  # active tier IDs
        self.stats = {"ats_transfers": 0, "sts_transfers": 0, "shed_events": 0}

    # ------------------------------------------------------------------
    # ATS transfer — mechanical; slower; used on main utility feed
    # ------------------------------------------------------------------
    async def ats_transfer(self, to_source: PowerSource) -> TransferEvent:
        t0 = time.perf_counter()
        await asyncio.sleep(
            0.080
        )  # Simulate 80 ms mechanical close + synchronise check
        duration_ms = (time.perf_counter() - t0) * 1000
        success = duration_ms <= self.ATS_TARGET_MS
        self.active_source = to_source
        self.stats["ats_transfers"] += 1
        ev = TransferEvent(
            event_id=str(uuid.uuid4()),
            from_source=self.active_source.value,
            to_source=to_source.value,
            transfer_type="ATS",
            duration_ms=round(duration_ms, 2),
            success=success,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.transfer_log.append(ev)
        await self._emit(
            "ats_transfer",
            {
                "duration_ms": ev.duration_ms,
                "success": success,
                "to_source": to_source.value,
            },
        )
        if not success:
            logger.error(
                "ATS transfer EXCEEDED target: %.1f ms (target %s ms)",
                duration_ms,
                self.ATS_TARGET_MS,
            )
        return ev

    # ------------------------------------------------------------------
    # STS transfer — solid-state; sub-cycle; used at UPS bypass bus
    # ------------------------------------------------------------------
    async def sts_transfer(self, to_source: PowerSource) -> TransferEvent:
        t0 = time.perf_counter()
        await asyncio.sleep(0.002)  # Simulate 2 ms IGBT switching
        duration_ms = (time.perf_counter() - t0) * 1000
        success = duration_ms <= self.STS_TARGET_MS
        self.active_source = to_source
        self.stats["sts_transfers"] += 1
        ev = TransferEvent(
            event_id=str(uuid.uuid4()),
            from_source=self.active_source.value,
            to_source=to_source.value,
            transfer_type="STS",
            duration_ms=round(duration_ms, 2),
            success=success,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.transfer_log.append(ev)
        await self._emit(
            "sts_transfer",
            {
                "duration_ms": ev.duration_ms,
                "success": success,
                "to_source": to_source.value,
            },
        )
        return ev

    # ------------------------------------------------------------------
    # Load shed — cascade through tiers until deficit closed
    # ------------------------------------------------------------------
    async def shed_load(self, deficit_mw: float):
        shed_total = 0.0
        for tier, spec in sorted(LOAD_SHED_TIERS.items(), reverse=True):
            if deficit_mw <= 0 or tier in self.load_shed_active:
                continue
            if deficit_mw >= spec["trigger_deficit_mw"]:
                continue
            self.load_shed_active.append(tier)
            shed_total += spec["shed_mw"]
            deficit_mw -= spec["shed_mw"]
            self.stats["shed_events"] += 1
            await self._emit(
                "load_shed_tier",
                {"tier": tier, "label": spec["label"], "shed_mw": spec["shed_mw"]},
            )
            logger.warning(
                "LOAD SHED Tier %d — %s — %.0f MW removed",
                tier,
                spec["label"],
                spec["shed_mw"],
            )
        return shed_total

    async def restore_load(self, tier: int):
        if tier in self.load_shed_active:
            self.load_shed_active.remove(tier)
            await self._emit("load_restore_tier", {"tier": tier})

    def transfer_report(self) -> dict:
        return {
            "transfers": len(self.transfer_log),
            "ats_within_target": sum(
                1 for e in self.transfer_log if e.transfer_type == "ATS" and e.success
            ),
            "sts_within_target": sum(
                1 for e in self.transfer_log if e.transfer_type == "STS" and e.success
            ),
            "load_shed_active_tiers": self.load_shed_active,
            "stats": self.stats,
        }

    async def _emit(self, event: str, extra: dict = {}):
        if self.kafka_cb:
            await self.kafka_cb(
                "colossus.power.transfer",
                {
                    "event_id": str(uuid.uuid4()),
                    "event_type": event,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    **extra,
                },
            )
