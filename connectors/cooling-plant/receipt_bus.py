"""Actuation Receipt Bus — signed intent with pre/post conditions for cooling cmds.

Every cooling/thermal command is a receipt-bound intent. Fail closed on missing
preconditions or forged receipts. Local plant-controller companion — not live
facility SCADA authority.

Mechanism: receipt_bus (Library of Links impact land — colossus cooling).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Callable


class ReceiptBusError(ValueError):
    """Receipt bus refused issuance or actuation."""


@dataclass(frozen=True)
class ActuationIntent:
    intent_id: str
    actuator: str
    command: str
    preconditions: tuple[str, ...]
    abort_predicates: tuple[str, ...]
    issued_at: float
    mac: str
    nonce: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "actuator": self.actuator,
            "command": self.command,
            "preconditions": list(self.preconditions),
            "abort_predicates": list(self.abort_predicates),
            "issued_at": self.issued_at,
            "mac": self.mac,
            "nonce": self.nonce,
        }


@dataclass(frozen=True)
class ActuationReceipt:
    intent_id: str
    ok: bool
    refuse: str | None
    postconditions: dict[str, Any]
    completed_at: float
    evidence_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "ok": self.ok,
            "refuse": self.refuse,
            "postconditions": self.postconditions,
            "completed_at": self.completed_at,
            "evidence_sha256": self.evidence_sha256,
        }


@dataclass
class ReceiptBus:
    """HMAC-bound command bus with precondition evaluation."""

    secret: bytes
    _ledger: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.secret:
            raise ReceiptBusError("secret required")

    def _mac(self, body: str) -> str:
        return hmac.new(self.secret, body.encode("utf-8"), hashlib.sha256).hexdigest()

    def issue(
        self,
        actuator: str,
        command: str,
        *,
        preconditions: list[str] | None = None,
        abort_predicates: list[str] | None = None,
        now: float | None = None,
    ) -> ActuationIntent:
        if not actuator.strip() or not command.strip():
            raise ReceiptBusError("actuator and command required")
        t = time.time() if now is None else float(now)
        nonce = secrets.token_hex(8)
        intent_id = f"ACT-{secrets.token_hex(5).upper()}"
        pre = tuple(preconditions or ())
        abort = tuple(abort_predicates or ())
        body = f"{intent_id}|{actuator}|{command}|{','.join(pre)}|{','.join(abort)}|{t:.6f}|{nonce}"
        return ActuationIntent(
            intent_id=intent_id,
            actuator=actuator.strip(),
            command=command.strip(),
            preconditions=pre,
            abort_predicates=abort,
            issued_at=t,
            mac=self._mac(body),
            nonce=nonce,
        )

    def _verify_mac(self, intent: ActuationIntent) -> bool:
        body = (
            f"{intent.intent_id}|{intent.actuator}|{intent.command}|"
            f"{','.join(intent.preconditions)}|{','.join(intent.abort_predicates)}|"
            f"{intent.issued_at:.6f}|{intent.nonce}"
        )
        return hmac.compare_digest(self._mac(body), intent.mac)

    def execute(
        self,
        intent: ActuationIntent,
        *,
        world: dict[str, Any],
        handler: Callable[[str, str, dict[str, Any]], dict[str, Any]],
        now: float | None = None,
    ) -> ActuationReceipt:
        """Evaluate preconditions, fire handler, record postcondition receipt."""
        t = time.time() if now is None else float(now)
        if not self._verify_mac(intent):
            return self._refuse(intent, "BAD_MAC", t)
        for pred in intent.preconditions:
            if not self._eval_predicate(pred, world):
                return self._refuse(intent, f"PRECONDITION_FAILED:{pred}", t)
        for pred in intent.abort_predicates:
            if self._eval_predicate(pred, world):
                return self._refuse(intent, f"ABORT:{pred}", t)
        try:
            post = handler(intent.actuator, intent.command, world)
        except Exception as exc:  # noqa: BLE001 — fail closed with evidence
            return self._refuse(intent, f"HANDLER_ERROR:{type(exc).__name__}", t)
        if not isinstance(post, dict):
            return self._refuse(intent, "HANDLER_NON_DICT", t)
        evidence = {
            "intent": intent.to_dict(),
            "post": post,
            "completed_at": t,
        }
        digest = hashlib.sha256(
            json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        receipt = ActuationReceipt(
            intent_id=intent.intent_id,
            ok=True,
            refuse=None,
            postconditions=post,
            completed_at=t,
            evidence_sha256=digest,
        )
        self._ledger.append(receipt.to_dict())
        return receipt

    def _refuse(self, intent: ActuationIntent, reason: str, t: float) -> ActuationReceipt:
        evidence = {"intent_id": intent.intent_id, "refuse": reason, "at": t}
        digest = hashlib.sha256(
            json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        receipt = ActuationReceipt(
            intent_id=intent.intent_id,
            ok=False,
            refuse=reason,
            postconditions={},
            completed_at=t,
            evidence_sha256=digest,
        )
        self._ledger.append(receipt.to_dict())
        return receipt

    @staticmethod
    def _eval_predicate(pred: str, world: dict[str, Any]) -> bool:
        """Minimal safe predicates: key truthiness or comparisons like temp_c<30."""
        p = pred.strip()
        if not p:
            return False
        if p in world:
            return bool(world[p])
        for op in ("<=", ">=", "<", ">", "=="):
            if op in p:
                left, right = p.split(op, 1)
                key = left.strip()
                try:
                    val = float(world.get(key))  # type: ignore[arg-type]
                    bound = float(right.strip())
                except (TypeError, ValueError):
                    return False
                if op == "<":
                    return val < bound
                if op == ">":
                    return val > bound
                if op == "<=":
                    return val <= bound
                if op == ">=":
                    return val >= bound
                return val == bound
        return False

    def ledger(self) -> list[dict[str, Any]]:
        return list(self._ledger)
