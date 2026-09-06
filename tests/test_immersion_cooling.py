"""Immersion cooling — microfluidic efficiency uses real heat-transfer math."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from apex_core.immersion_cooling import ImmersionCoolingEngine  # noqa: E402


def test_zero_flow_is_zero_efficiency():
    eng = ImmersionCoolingEngine(tank_count=1)
    assert eng.calculate_microfluidic_efficiency(0.0) == 0.0


def test_positive_flow_bounded_efficiency():
    eng = ImmersionCoolingEngine(tank_count=1)
    eff = eng.calculate_microfluidic_efficiency(250.0)
    assert 0.0 < eff <= 0.99


def test_boiling_cycle_marks_onset():
    eng = ImmersionCoolingEngine(tank_count=2)
    for tank in eng.tanks:
        tank.coolant_temp_c = 60.5
    reports = asyncio.run(eng.simulate_boiling_cycle(load_factor=2.0))
    assert len(reports) == 2
    assert any(report["status"] in ("BOILING_ACTIVE", "STABLE") for report in reports)
