"""First-principles thermal tests for Colossus cooling reality module."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    import sys

    path = ROOT / "connectors" / "cooling-plant" / "thermal_reality.py"
    name = "thermal_reality"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = mod  # required for some py3.9 class machinery
    spec.loader.exec_module(mod)
    return mod


tr = _load()


class TestThermalReality(unittest.TestCase):
    def test_energy_balance_identity(self):
        # 1 kg/s water, ΔT=1K → Q = 4184 W = 0.004184 MW
        st = tr.ThermalState(
            it_load_mw=0.004184,
            coolant_flow_kg_s=1.0,
            inlet_c=25.0,
            outlet_c=26.0,
            cooling_electrical_mw=0.001,
        )
        self.assertAlmostEqual(st.heat_reject_mw, 0.004184, places=6)
        self.assertAlmostEqual(st.heat_margin_mw, 0.0, places=6)

    def test_required_flow(self):
        m = tr.required_flow_kg_s(1.0, 5.0)
        self.assertAlmostEqual(m, 1_000_000.0 / (4184.0 * 5.0), places=6)

    def test_assess_nominal(self):
        r = tr.assess_loop(
            it_load_mw=0.5,
            flow_lpm=5000.0,
            inlet_c=25.0,
            outlet_c=30.0,
            cooling_electrical_mw=0.05,
            throttle_margin_mw=0.01,
        )
        self.assertEqual(r["status"], "NOMINAL")
        self.assertGreater(r["heat_margin_mw"], 0)

    def test_assess_critical_insufficient(self):
        r = tr.assess_loop(
            it_load_mw=50.0,
            flow_lpm=10.0,
            inlet_c=25.0,
            outlet_c=26.0,
            cooling_electrical_mw=1.0,
        )
        self.assertEqual(r["status"], "CRITICAL")

    def test_pue(self):
        st = tr.ThermalState(10.0, 100.0, 20.0, 25.0, 1.0)
        self.assertAlmostEqual(st.pue_cooling, 1.1, places=6)


if __name__ == "__main__":
    unittest.main()
