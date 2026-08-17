from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "receipt_bus",
    ROOT / "connectors" / "cooling-plant" / "receipt_bus.py",
)
assert _SPEC and _SPEC.loader
_MOD = importlib.util.module_from_spec(_SPEC)
sys.modules["receipt_bus"] = _MOD
_SPEC.loader.exec_module(_MOD)
ReceiptBus = _MOD.ReceiptBus
ReceiptBusError = _MOD.ReceiptBusError

SECRET = b"colossus-cooling-receipt-bus-v1-test-only"


def test_issue_and_execute_happy_path() -> None:
    bus = ReceiptBus(SECRET)
    intent = bus.issue(
        "chiller_1",
        "setpoint_adjust",
        preconditions=["plant_online", "temp_c<40"],
        abort_predicates=["emergency_stop"],
    )
    world = {"plant_online": True, "temp_c": 28.0, "emergency_stop": False}

    def handler(actuator: str, command: str, w: dict) -> dict:
        return {"actuator": actuator, "command": command, "new_setpoint_c": 22.0}

    receipt = bus.execute(intent, world=world, handler=handler)
    assert receipt.ok is True
    assert receipt.refuse is None
    assert receipt.postconditions["new_setpoint_c"] == 22.0
    assert len(bus.ledger()) == 1


def test_precondition_failure_refuses() -> None:
    bus = ReceiptBus(SECRET)
    intent = bus.issue("tower_1", "fan_up", preconditions=["temp_c<25"])
    world = {"temp_c": 33.0}
    receipt = bus.execute(intent, world=world, handler=lambda a, c, w: {"ran": True})
    assert receipt.ok is False
    assert receipt.refuse and receipt.refuse.startswith("PRECONDITION_FAILED")


def test_abort_predicate_refuses() -> None:
    bus = ReceiptBus(SECRET)
    intent = bus.issue(
        "chiller_1",
        "run",
        preconditions=["plant_online"],
        abort_predicates=["emergency_stop"],
    )
    world = {"plant_online": True, "emergency_stop": True}
    receipt = bus.execute(intent, world=world, handler=lambda a, c, w: {"ran": True})
    assert receipt.ok is False
    assert receipt.refuse and receipt.refuse.startswith("ABORT")


def test_forged_mac_refuses() -> None:
    bus = ReceiptBus(SECRET)
    intent = bus.issue("chiller_1", "run")
    forged = type(intent)(**{**intent.to_dict(), "mac": "00" * 32})
    receipt = bus.execute(forged, world={}, handler=lambda a, c, w: {"ran": True})
    assert receipt.ok is False
    assert receipt.refuse == "BAD_MAC"


def test_empty_secret_rejected() -> None:
    with pytest.raises(ReceiptBusError):
        ReceiptBus(b"")
