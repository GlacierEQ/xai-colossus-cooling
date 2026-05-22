"""
AutomaticTransferSwitch (ATS)
==============================
Coordinates seamless transfer between utility grid and on-site generation.

Switch specs:
  - Technology: Solid-state static transfer switch (< 4ms)
  - Rating: 1,600A / 13.8 kV per switch
  - Units: 24x ATS units (one per distribution panel)
  - Control: SEL-300G generator protection relay
  - Test mode: Monthly no-load transfer test, quarterly load transfer

Transfer sequence:
  1. Grid loss detected by voltage/frequency relay (< 2 cycles)
  2. ATS signals UPS — UPS goes to battery (< 4ms)
  3. ATS signals Turbine Array — hot start sequence (~10 min)
  4. At 95% voltage + 59.9-60.1 Hz: ATS transfers to generator bus
  5. UPS returns to normal mode, begins recharging
  6. On grid restoration: retransfer after 5-min stability check
"""
import asyncio, logging, time, uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Callable

logger = logging.getLogger(__name__)

ATS_UNITS              = 24
TRANSFER_TIME_MS       = 4
GRID_RESTORE_HOLD_MIN  = 5
VOLTAGE_TOLERANCE_PCT  = 5.0
FREQ_TOLERANCE_HZ      = 0.1


class PowerSource(Enum):
    UTILITY = "utility"
    GENERATOR = "generator"
    BATTERY = "battery"
    NONE = "none"


class ATSState(Enum):
    UTILITY_NORMAL   = "utility_normal"
    TRANSFERRING     = "transferring"
    GENERATOR_ACTIVE = "generator_active"
    RETRANSFERRING   = "retransferring"
    TEST_MODE        = "test_mode"
    FAULT            = "fault"


@dataclass
class TransferEvent:
    event_id: str
    timestamp: str
    from_source: str
    to_source: str
    reason: str
    transfer_time_ms: float
    success: bool


class AutomaticTransferSwitch:
    def __init__(self,
                 turbine_array=None,
                 ups_manager=None,
                 kafka_callback: Optional[Callable] = None,
                 influx_sink=None):
        self.turbines  = turbine_array
        self.ups       = ups_manager
        self.kafka_cb  = kafka_callback
        self.influx    = influx_sink
        self._state    = ATSState.UTILITY_NORMAL
        self._source   = PowerSource.UTILITY
        self._running  = False
        self._transfer_log = []
        self._stats = {"transfers": 0, "retransfers": 0, "faults": 0}

    async def start(self, poll_interval_sec: float = 0.5):
        self._running = True
        logger.info(f"[ATS] {ATS_UNITS} static transfer switches active")
        while self._running:
            await self._monitor()
            await asyncio.sleep(poll_interval_sec)

    async def stop(self): self._running = False

    async def execute_transfer(self, reason: str = "grid_loss"):
        """Full transfer: utility -> battery bridge -> generator."""
        if self._state == ATSState.TRANSFERRING: return
        self._state = ATSState.TRANSFERRING
        start_ms = time.monotonic() * 1000
        logger.critical(f"[ATS] TRANSFER INITIATED: {reason}")
        if self.ups:
            await self.ups.switch_to_battery()
        if self.turbines:
            await self.turbines.activate_island_mode()
        # Wait for generators to come online (~10 min in real life, 0.1s here)
        await asyncio.sleep(0.1)
        self._source = PowerSource.GENERATOR
        self._state  = ATSState.GENERATOR_ACTIVE
        if self.ups:
            await self.ups.restore_utility()   # UPS returns to float charge via generator
        transfer_ms = round((time.monotonic() * 1000) - start_ms, 2)
        event = TransferEvent(
            event_id=str(uuid.uuid4()), timestamp=datetime.now(timezone.utc).isoformat(),
            from_source="utility", to_source="generator",
            reason=reason, transfer_time_ms=transfer_ms, success=True
        )
        self._transfer_log.append(event)
        self._stats["transfers"] += 1
        logger.critical(f"[ATS] Transfer complete: utility->generator in {transfer_ms}ms")
        if self.kafka_cb:
            asyncio.create_task(self.kafka_cb("colossus.power.alerts", {
                "event_id": event.event_id, "event_type": "ats_transfer",
                "from_source": event.from_source, "to_source": event.to_source,
                "reason": reason, "transfer_ms": transfer_ms,
                "timestamp": event.timestamp}))

    async def _monitor(self):
        """Stub — in production: monitors relay contacts and voltage/freq."""
        pass

    def status(self) -> dict:
        return {"state": self._state.value, "active_source": self._source.value,
                "ats_units": ATS_UNITS, "transfer_log_count": len(self._transfer_log),
                "stats": self._stats}
