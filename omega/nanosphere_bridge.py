# Omega (How) — Controllers | Alpha (What) — Pure Physics | 1337.
"""
nanosphere_bridge.py
xai-colossus-cooling — Bridge to nanosphere circuit manifest

Reads the nanosphere-generated circuit manifest and enforces invariants
before allowing cooling orchestrator to run.

Invariants:
- Every active circuit must have status == "active".
- replacement_due must be False for all circuits.
- effective_conductivity_w_mk and degradation_pct must be present.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict
import json
import pathlib
import sys


NANOSPHERE_MANIFEST_PATH = pathlib.Path(
    "../xai-colossus-nanosphere/integration/circuit_manifest.json"
)


@dataclass
class CircuitFluidState:
    batch_id: str
    circuit_id: str
    nanoparticle: str
    volume_fraction_pct: float
    effective_conductivity_w_mk: float
    degradation_pct: float
    status: str
    replacement_due: bool


class NanosphereBridgeError(RuntimeError):
    pass


def load_circuit_manifest(
    path: pathlib.Path = NANOSPHERE_MANIFEST_PATH,
) -> Dict[str, CircuitFluidState]:
    if not path.exists():
        raise NanosphereBridgeError(f"Nanosphere circuit manifest not found at {path}")
    with path.open() as f:
        raw = json.load(f)

    circuits: Dict[str, CircuitFluidState] = {}
    for entry in raw.get("circuits", []):
        cid = entry.get("circuit_id")
        if not cid:
            continue
        circuits[cid] = CircuitFluidState(
            batch_id=entry["batch_id"],
            circuit_id=cid,
            nanoparticle=entry["nanoparticle"],
            volume_fraction_pct=entry["volume_fraction_pct"],
            effective_conductivity_w_mk=entry["effective_conductivity_w_mk"],
            degradation_pct=entry["degradation_pct"],
            status=entry.get("status", "unknown"),
            replacement_due=entry.get("replacement_due", False),
        )
    return circuits


def assert_coolant_invariants(circuits: Dict[str, CircuitFluidState]) -> None:
    """
    Hard gate before starting cooling orchestration.
    Raises NanosphereBridgeError if any circuit violates invariants.
    ALL violations are collected and reported together — never one-at-a-time.
    """
    violations = []

    for cid, state in circuits.items():
        if state.status not in {"active"}:
            violations.append(f"circuit {cid} status={state.status} (must be 'active')")
        if state.replacement_due:
            violations.append(
                f"circuit {cid} replacement_due=True (coolant batch must be replaced before startup)"
            )
        if state.degradation_pct > 15.0:
            violations.append(
                f"circuit {cid} degradation_pct={state.degradation_pct:.2f} (> 15%)"
            )
        if state.effective_conductivity_w_mk <= 0:
            violations.append(
                f"circuit {cid} effective_conductivity_w_mk={state.effective_conductivity_w_mk} (non-positive)"
            )

    if violations:
        message = "Nanosphere coolant invariants violated:\n  - " + "\n  - ".join(
            violations
        )
        raise NanosphereBridgeError(message)


def load_and_validate_coolant() -> Dict[str, CircuitFluidState]:
    """
    Convenience entry-point for cooling orchestrator:
    - loads manifest
    - enforces invariants
    - returns validated map of circuit_id -> CircuitFluidState

    Usage in thermal_orchestrator.py::

        from nanosphere_bridge import load_and_validate_coolant, NanosphereBridgeError

        try:
            circuits = load_and_validate_coolant()
        except NanosphereBridgeError as e:
            logger.critical("COOLING STARTUP BLOCKED: %s", e)
            raise SystemExit(1)

        conductivity_map = {
            cid: state.effective_conductivity_w_mk
            for cid, state in circuits.items()
        }
    """
    circuits = load_circuit_manifest()
    assert_coolant_invariants(circuits)
    return circuits


if __name__ == "__main__":
    try:
        circuits = load_and_validate_coolant()
    except NanosphereBridgeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    else:
        print(
            f"Loaded {len(circuits)} coolant circuits from nanosphere. All invariants satisfied."
        )
        for cid, state in circuits.items():
            print(
                f"{cid}: k={state.effective_conductivity_w_mk:.4f} W/m\u00b7K, "
                f"deg={state.degradation_pct:.2f}%, repl_due={state.replacement_due}"
            )
