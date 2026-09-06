"""Regression contract for removing the copied secret-bound promotion layer."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_keyed_promotion_artifacts_are_absent():
    assert not (ROOT / "src/promotion_authority.py").exists()
    assert not (ROOT / "machine/promotion_authority.json").exists()
    assert not (ROOT / "tests/test_promotion_authority.py").exists()


def test_state_is_append_only_and_keyless():
    state = json.loads((ROOT / "machine/excellence-state.json").read_text())
    assert "AUTHORITY_BOUND" not in state["gates"]
    assert state["gates"]["PROMOTION_LOCKOUT_REMOVED"]["status"] == "PASS"
    assert state["state"] == "PROMOTED"
    assert any(item["gate"] == "AUTHORITY_BOUND" for item in state["history"])
    assert any(item["gate"] == "PROMOTION_LOCKOUT_REMOVED" for item in state["history"])
