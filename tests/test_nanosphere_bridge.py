"""
tests/test_nanosphere_bridge.py
xai-colossus-cooling

Pytest suite for nanosphere_bridge.py.
Uses fixture JSON files; does NOT require a live nanosphere repo clone.

Run with:
    pytest tests/test_nanosphere_bridge.py -v
"""

from __future__ import annotations

import json
import pathlib
import sys

import pytest

try:
    from nanosphere_bridge import (
        CircuitFluidState,
        NanosphereBridgeError,
        assert_coolant_invariants,
        load_circuit_manifest,
    )
except ImportError:
    try:
        from connectors.nanosphere_bridge import (
            CircuitFluidState,
            NanosphereBridgeError,
            assert_coolant_invariants,
            load_circuit_manifest,
        )
    except ImportError:
        from omega.nanosphere_bridge import (
            CircuitFluidState,
            NanosphereBridgeError,
            assert_coolant_invariants,
            load_circuit_manifest,
        )

FIXTURE_DIR = pathlib.Path(__file__).parent / "fixtures"
GOOD_MANIFEST = FIXTURE_DIR / "circuit_manifest.json"
BAD_MANIFEST = FIXTURE_DIR / "circuit_manifest_violations.json"


def _build_circuits(**overrides) -> dict[str, CircuitFluidState]:
    defaults = dict(
        batch_id="BATCH-2026-001",
        circuit_id="CIRCUIT-TEST",
        nanoparticle="Al2O3",
        volume_fraction_pct=0.5,
        effective_conductivity_w_mk=0.670,
        degradation_pct=2.0,
        status="active",
        replacement_due=False,
    )
    defaults.update(overrides)
    cid = defaults["circuit_id"]
    return {cid: CircuitFluidState(**defaults)}


class TestLoadManifest:
    def test_loads_good_manifest(self):
        circuits = load_circuit_manifest(GOOD_MANIFEST)
        assert len(circuits) == 5

    def test_keys_are_circuit_ids(self):
        circuits = load_circuit_manifest(GOOD_MANIFEST)
        assert "CIRCUIT-A1" in circuits
        assert "CIRCUIT-B2" in circuits

    def test_field_types(self):
        circuits = load_circuit_manifest(GOOD_MANIFEST)
        c = circuits["CIRCUIT-A1"]
        assert isinstance(c.batch_id, str)
        assert isinstance(c.effective_conductivity_w_mk, float)
        assert isinstance(c.replacement_due, bool)

    def test_missing_path_raises(self, tmp_path):
        with pytest.raises(NanosphereBridgeError, match="not found"):
            load_circuit_manifest(tmp_path / "nonexistent.json")

    def test_empty_circuits_list(self, tmp_path):
        p = tmp_path / "empty.json"
        p.write_text(json.dumps({"circuits": []}))
        circuits = load_circuit_manifest(p)
        assert circuits == {}

    def test_entry_without_circuit_id_is_skipped(self, tmp_path):
        p = tmp_path / "no_cid.json"
        p.write_text(json.dumps({"circuits": [{"batch_id": "X", "nanoparticle": "Al2O3"}]}))
        circuits = load_circuit_manifest(p)
        assert circuits == {}


class TestInvariants:
    def test_passes_all_good_circuits(self):
        circuits = load_circuit_manifest(GOOD_MANIFEST)
        assert_coolant_invariants(circuits)

    def test_fails_on_violation_manifest(self):
        circuits = load_circuit_manifest(BAD_MANIFEST)
        with pytest.raises(NanosphereBridgeError) as exc_info:
            assert_coolant_invariants(circuits)
        msg = str(exc_info.value)
        assert "replacement_due=True" in msg
        assert "non-positive" in msg
        assert "maintenance" in msg

    def test_inactive_status_raises(self):
        circuits = _build_circuits(status="maintenance")
        with pytest.raises(NanosphereBridgeError, match="status=maintenance"):
            assert_coolant_invariants(circuits)

    def test_replacement_due_raises(self):
        circuits = _build_circuits(replacement_due=True)
        with pytest.raises(NanosphereBridgeError, match="replacement_due=True"):
            assert_coolant_invariants(circuits)

    def test_degradation_over_15_raises(self):
        circuits = _build_circuits(degradation_pct=15.1)
        with pytest.raises(NanosphereBridgeError, match="degradation_pct=15.10"):
            assert_coolant_invariants(circuits)

    def test_degradation_exactly_15_passes(self):
        circuits = _build_circuits(degradation_pct=15.0)
        assert_coolant_invariants(circuits)

    def test_zero_conductivity_raises(self):
        circuits = _build_circuits(effective_conductivity_w_mk=0.0)
        with pytest.raises(NanosphereBridgeError, match="non-positive"):
            assert_coolant_invariants(circuits)

    def test_negative_conductivity_raises(self):
        circuits = _build_circuits(effective_conductivity_w_mk=-0.001)
        with pytest.raises(NanosphereBridgeError, match="non-positive"):
            assert_coolant_invariants(circuits)

    def test_multiple_violations_reported_together(self):
        """All violations must be reported in one raise, not one-at-a-time."""
        circuits = {
            "C1": CircuitFluidState(
                batch_id="B1", circuit_id="C1", nanoparticle="X",
                volume_fraction_pct=0.5, effective_conductivity_w_mk=0.5,
                degradation_pct=20.0, status="active", replacement_due=True,
            ),
            "C2": CircuitFluidState(
                batch_id="B2", circuit_id="C2", nanoparticle="Y",
                volume_fraction_pct=0.3, effective_conductivity_w_mk=-1.0,
                degradation_pct=5.0, status="offline", replacement_due=False,
            ),
        }
        with pytest.raises(NanosphereBridgeError) as exc_info:
            assert_coolant_invariants(circuits)
        msg = str(exc_info.value)
        assert "C1" in msg
        assert "C2" in msg
        assert msg.count("  - ") >= 3
