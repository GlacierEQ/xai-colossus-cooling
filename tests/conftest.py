"""Test path bootstrap for host Python 3.9 + package layout.

Ensures apex_core, connectors.m2a_middleware, omega nanosphere_bridge,
alpha.sensors, and memory loggers import cleanly under pytest.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_PATHS = [
    _ROOT,
    _ROOT / "src",
    _ROOT / "omega",
    _ROOT / "alpha",
    _ROOT / "memory",
    _ROOT / "connectors",
]
for p in _PATHS:
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)
