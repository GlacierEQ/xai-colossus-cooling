"""
Black-Start Sequencing — Phase 6 Power Hardening
Full black-start runbook: diesel gen → bus energisation → turbine train → UPS bypass → IT loads
Ref: IEEE C37.101, NERC TPL-001-5
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


BLACK_START_RUNBOOK: List[dict] = [
    {
        "step": 1,
        "action": "Diesel gen GTD-01 self-starts (no external power needed)",
        "target_s": 15,
        "owner": "auto",
    },
    {
        "step": 2,
        "action": "GTD-01 energises 480V house bus — controls & protection LV panels live",
        "target_s": 20,
        "owner": "auto",
    },
    {
        "step": 3,
        "action": "UPS string #1 initiates from battery — critical control bus protected",
        "target_s": 25,
        "owner": "auto",
    },
    {
        "step": 4,
        "action": "GTG-01 cranks on diesel pneumatic start — turbine ignition sequence",
        "target_s": 60,
        "owner": "auto",
    },
    {
        "step": 5,
        "action": "GTG-01 synchronised to 11 kV island bus — breaker close",
        "target_s": 90,
        "owner": "auto",
    },
    {
        "step": 6,
        "action": "GTG-02 through GTG-08 start in 45-second intervals — full fleet 6 min",
        "target_s": 360,
        "owner": "auto",
    },
    {
        "step": 7,
        "action": "ATS transfers cooling plant loads to turbine bus",
        "target_s": 380,
        "owner": "auto",
    },
    {
        "step": 8,
        "action": "Chiller plant sequence start (staggered 30 s between units)",
        "target_s": 480,
        "owner": "auto",
    },
    {
        "step": 9,
        "action": "GPU compute loads re-energised tier-by-tier — checkpoint resume",
        "target_s": 600,
        "owner": "auto",
    },
    {
        "step": 10,
        "action": "Utility grid synchronisation — parallel operation, soft handover",
        "target_s": 900,
        "owner": "operations",
    },
]


class BlackStartOrchestrator:
    def __init__(
        self, turbine_fleet, ats_controller, kafka_callback: Optional[Callable] = None
    ):
        self.turbines = turbine_fleet
        self.ats = ats_controller
        self.kafka_cb = kafka_callback
        self.active = False
        self.completed_steps: List[int] = []

    async def execute(self):
        self.active = True
        logger.critical("=== BLACK-START SEQUENCE INITIATED ===")
        await self._emit("black_start_initiated", {})

        for step in BLACK_START_RUNBOOK:
            n = step["step"]
            logger.info("[BS Step %02d] %s", n, step["action"])
            await asyncio.sleep(
                0.1
            )  # In production: await actual relay/SCADA confirmation
            self.completed_steps.append(n)
            await self._emit("black_start_step", {"step": n, "action": step["action"]})

        # Trigger turbine fleet black-start procedure
        await self.turbines.black_start()

        self.active = False
        logger.critical("=== BLACK-START COMPLETE — ALL LOADS RESTORED ===")
        await self._emit(
            "black_start_complete", {"steps_completed": len(self.completed_steps)}
        )

    def report(self):
        return {
            "active": self.active,
            "steps_completed": self.completed_steps,
            "total_steps": len(BLACK_START_RUNBOOK),
        }

    async def _emit(self, event: str, extra: dict):
        if self.kafka_cb:
            await self.kafka_cb(
                "colossus.power.blackstart",
                {
                    "event_id": str(uuid.uuid4()),
                    "event_type": event,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    **extra,
                },
            )
