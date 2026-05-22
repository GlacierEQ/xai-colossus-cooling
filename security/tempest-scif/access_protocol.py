"""
Colossus Access Control Protocol
=================================
Multi-factor physical access: biometric + RFID + mantrap interlock.
Zone clearance levels: PUBLIC(0) -> GREEN(1) -> AMBER(2) -> RED(3) -> SCIF(4)
All events emit to Kafka colossus.security.access + audit_logger.
"""
import asyncio, uuid, logging, hashlib, time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from typing import Optional, Callable, Dict

logger = logging.getLogger(__name__)


class ClearanceLevel(IntEnum):
    PUBLIC = 0
    GREEN  = 1
    AMBER  = 2
    RED    = 3
    SCIF   = 4


@dataclass
class AccessRequest:
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    person_id: str = ""
    badge_id: str = ""
    biometric_hash: str = ""   # SHA-256 of biometric template — never raw
    target_zone: ClearanceLevel = ClearanceLevel.GREEN
    door_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ip_address: str = ""
    workstation_id: str = ""


@dataclass
class AccessResult:
    request_id: str
    granted: bool
    reason: str
    clearance_level: ClearanceLevel
    door_id: str
    timestamp: str
    alert: bool = False
    alert_type: str = ""


class PersonnelRegistry:
    """In production: backed by LDAP/Active Directory + HSM-protected biometric vault."""
    def __init__(self):
        self._registry: Dict[str, dict] = {}

    def register(self, person_id: str, badge_id: str, biometric_hash: str,
                 clearance: ClearanceLevel, name: str = ""):
        self._registry[person_id] = {
            "badge_id": badge_id, "biometric_hash": biometric_hash,
            "clearance": clearance, "name": name, "active": True,
            "registered_at": datetime.now(timezone.utc).isoformat()
        }

    def get(self, person_id: str) -> Optional[dict]:
        return self._registry.get(person_id)

    def revoke(self, person_id: str):
        if person_id in self._registry:
            self._registry[person_id]["active"] = False
            logger.warning(f"[Access] Revoked: {person_id}")


class ManTrapController:
    """2-door mantrap: only one door may be open at a time. State machine."""
    def __init__(self, trap_id: str):
        self.trap_id = trap_id
        self._door_states = {"outer": False, "inner": False}  # False=closed
        self._lock = asyncio.Lock()

    async def request_outer(self) -> bool:
        async with self._lock:
            if self._door_states["inner"]:
                logger.warning(f"[ManTrap:{self.trap_id}] Outer denied — inner open")
                return False
            self._door_states["outer"] = True
            logger.info(f"[ManTrap:{self.trap_id}] Outer OPEN")
            return True

    async def request_inner(self) -> bool:
        async with self._lock:
            if not self._door_states["outer"]:
                logger.warning(f"[ManTrap:{self.trap_id}] Inner denied — outer not open")
                return False
            if self._door_states["inner"]:
                return True
            await self._close_outer()
            self._door_states["inner"] = True
            logger.info(f"[ManTrap:{self.trap_id}] Inner OPEN")
            return True

    async def _close_outer(self):
        self._door_states["outer"] = False
        logger.info(f"[ManTrap:{self.trap_id}] Outer auto-CLOSED")

    async def close_all(self):
        async with self._lock:
            self._door_states = {"outer": False, "inner": False}
            logger.info(f"[ManTrap:{self.trap_id}] All doors CLOSED")


class AccessControlSystem:
    """
    Multi-factor gate:
    1. Badge RFID check
    2. Biometric match
    3. Clearance level check
    4. ManTrap interlock (SCIF/RED zones)
    5. Audit log emit
    """
    def __init__(self, registry: PersonnelRegistry,
                 audit_callback: Optional[Callable] = None,
                 kafka_callback: Optional[Callable] = None):
        self.registry = registry
        self.audit_cb = audit_callback
        self.kafka_cb = kafka_callback
        self._mantraps: Dict[str, ManTrapController] = {}
        self._stats = {"granted": 0, "denied": 0, "alerts": 0}

    def register_mantrap(self, trap_id: str):
        self._mantraps[trap_id] = ManTrapController(trap_id)

    async def process(self, req: AccessRequest) -> AccessResult:
        person = self.registry.get(req.person_id)

        # Factor 1: badge
        if not person or person["badge_id"] != req.badge_id:
            return await self._deny(req, "invalid_badge", alert=True, alert_type="BADGE_MISMATCH")

        # Factor 2: active status
        if not person["active"]:
            return await self._deny(req, "revoked", alert=True, alert_type="REVOKED_ATTEMPT")

        # Factor 3: biometric
        if person["biometric_hash"] != req.biometric_hash:
            return await self._deny(req, "biometric_fail", alert=True, alert_type="BIO_MISMATCH")

        # Factor 4: clearance
        if person["clearance"] < req.target_zone:
            return await self._deny(req, "insufficient_clearance", alert=True, alert_type="CLEARANCE_VIOLATION")

        # Factor 5: mantrap for RED/SCIF
        if req.target_zone >= ClearanceLevel.RED and req.door_id in self._mantraps:
            trap = self._mantraps[req.door_id]
            if not await trap.request_inner():
                return await self._deny(req, "mantrap_interlock", alert=False)

        return await self._grant(req, person["clearance"])

    async def _grant(self, req: AccessRequest, clearance: ClearanceLevel) -> AccessResult:
        result = AccessResult(request_id=req.request_id, granted=True, reason="all_factors_passed",
                              clearance_level=clearance, door_id=req.door_id,
                              timestamp=datetime.now(timezone.utc).isoformat())
        self._stats["granted"] += 1
        logger.info(f"[Access] GRANTED {req.person_id} zone={req.target_zone.name} door={req.door_id}")
        await self._emit(result)
        return result

    async def _deny(self, req: AccessRequest, reason: str, alert: bool = False, alert_type: str = "") -> AccessResult:
        result = AccessResult(request_id=req.request_id, granted=False, reason=reason,
                              clearance_level=ClearanceLevel.PUBLIC, door_id=req.door_id,
                              timestamp=datetime.now(timezone.utc).isoformat(),
                              alert=alert, alert_type=alert_type)
        self._stats["denied"] += 1
        if alert: self._stats["alerts"] += 1
        level = logging.WARNING if alert else logging.INFO
        logger.log(level, f"[Access] DENIED {req.person_id} reason={reason} alert={alert_type}")
        await self._emit(result)
        return result

    async def _emit(self, result: AccessResult):
        payload = {"request_id": result.request_id, "granted": result.granted,
                   "reason": result.reason, "door_id": result.door_id,
                   "timestamp": result.timestamp, "alert": result.alert,
                   "alert_type": result.alert_type}
        if self.audit_cb:
            asyncio.create_task(self.audit_cb(payload))
        if self.kafka_cb:
            asyncio.create_task(self.kafka_cb("colossus.security.access", payload))

    def stats(self) -> dict:
        return self._stats
