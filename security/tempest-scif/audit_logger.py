"""
Tamper-Evident Audit Logger
============================
HMAC-SHA256 cryptographic event chain.
Each entry includes HMAC of (previous_hash + event_json) — any tampering
breaks the chain and is detected on verification.

Storage: async file sink + optional InfluxDB + optional Kafka.
Compliance: 7-year retention per COLD tier policy.
"""
import asyncio, hashlib, hmac, json, logging, time, uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

CHAIN_VERSION = "APEX-AUDIT-V1"


@dataclass
class AuditEntry:
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_type: str = ""
    actor_id: str = ""
    resource: str = ""
    action: str = ""
    outcome: str = ""  # granted | denied | error | info
    metadata: Dict[str, Any] = field(default_factory=dict)
    chain_hash: str = ""   # HMAC of (prev_hash + this_entry_json)
    prev_hash: str = ""
    sequence: int = 0


class TamperEvidentAuditLogger:
    """
    Append-only audit log with cryptographic chain.
    Secret key should be loaded from HSM / Vault in production.
    """
    def __init__(self, secret_key: bytes = b"CHANGE-IN-PRODUCTION-USE-HSM",
                 log_dir: str = "./audit_logs",
                 influx_sink=None,
                 kafka_callback=None):
        self._key = secret_key
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._chain_hash = "GENESIS"
        self._sequence = 0
        self._lock = asyncio.Lock()
        self._influx = influx_sink
        self._kafka_cb = kafka_callback
        self._stats = {"entries": 0, "chain_breaks_detected": 0, "errors": 0}
        self._log_file = self._log_dir / f"audit_{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"

    async def log(self, event_type: str, actor_id: str, resource: str,
                  action: str, outcome: str, metadata: Optional[Dict] = None) -> AuditEntry:
        async with self._lock:
            entry = AuditEntry(
                event_type=event_type, actor_id=actor_id, resource=resource,
                action=action, outcome=outcome, metadata=metadata or {},
                prev_hash=self._chain_hash, sequence=self._sequence
            )
            entry_json = json.dumps({
                "entry_id": entry.entry_id, "timestamp": entry.timestamp,
                "event_type": event_type, "actor_id": actor_id,
                "resource": resource, "action": action, "outcome": outcome,
                "metadata": entry.metadata, "sequence": entry.sequence
            }, sort_keys=True)
            mac_input = (self._chain_hash + entry_json).encode("utf-8")
            entry.chain_hash = hmac.new(self._key, mac_input, hashlib.sha256).hexdigest()
            self._chain_hash = entry.chain_hash
            self._sequence += 1
            self._stats["entries"] += 1
            await self._persist(entry, entry_json)
            await self._emit_influx(entry)
            await self._emit_kafka(entry)
            return entry

    async def _persist(self, entry: AuditEntry, entry_json: str):
        line = json.dumps({"entry_id": entry.entry_id, "timestamp": entry.timestamp,
                           "sequence": entry.sequence, "chain_hash": entry.chain_hash,
                           "prev_hash": entry.prev_hash, "event": json.loads(entry_json)}) + "\n"
        try:
            self._log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"[Audit] Persist error: {e}")

    async def verify_chain(self, entries: List[AuditEntry]) -> bool:
        """Verify the HMAC chain of a list of entries. Returns True if intact."""
        prev = "GENESIS"
        for entry in entries:
            entry_json = json.dumps({
                "entry_id": entry.entry_id, "timestamp": entry.timestamp,
                "event_type": entry.event_type, "actor_id": entry.actor_id,
                "resource": entry.resource, "action": entry.action,
                "outcome": entry.outcome, "metadata": entry.metadata,
                "sequence": entry.sequence
            }, sort_keys=True)
            mac_input = (prev + entry_json).encode("utf-8")
            expected = hmac.new(self._key, mac_input, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, entry.chain_hash):
                self._stats["chain_breaks_detected"] += 1
                logger.critical(f"[Audit] CHAIN BREAK at sequence={entry.sequence} entry={entry.entry_id}")
                return False
            prev = entry.chain_hash
        return True

    async def _emit_influx(self, entry: AuditEntry):
        if not self._influx: return
        try:
            await self._influx.write_reading(
                measurement="colossus_audit",
                tags={"event_type": entry.event_type, "outcome": entry.outcome, "actor_id": entry.actor_id},
                fields={"sequence": entry.sequence, "resource": entry.resource, "action": entry.action})
        except Exception as e:
            logger.warning(f"[Audit] InfluxDB emit failed: {e}")

    async def _emit_kafka(self, entry: AuditEntry):
        if not self._kafka_cb: return
        try:
            await self._kafka_cb("colossus.security.audit", {
                "entry_id": entry.entry_id, "sequence": entry.sequence,
                "event_type": entry.event_type, "outcome": entry.outcome,
                "chain_hash": entry.chain_hash[:16] + "..."})
        except Exception as e:
            logger.warning(f"[Audit] Kafka emit failed: {e}")

    def stats(self) -> dict:
        return {**self._stats, "current_sequence": self._sequence, "chain_version": CHAIN_VERSION}
