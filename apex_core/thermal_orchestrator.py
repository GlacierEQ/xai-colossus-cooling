#!/usr/bin/env python3
"""Compatibility bridge for test and simulation imports.

The canonical implementation lives in `apex-core/thermal_orchestrator.py`, but
Python package imports in tests and the simulation harness use
`apex_core.thermal_orchestrator`.

This module loads the canonical file by path and re-exports its public runtime
symbols so CI, tests, and downstream code can keep a stable import surface.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_CANONICAL_PATH = Path(__file__).resolve().parent.parent / 'apex-core' / 'thermal_orchestrator.py'
_SPEC = importlib.util.spec_from_file_location('apex_core._canonical_thermal_orchestrator', _CANONICAL_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f'Unable to load canonical orchestrator from {_CANONICAL_PATH}')

_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

CoolingMode = _MODULE.CoolingMode
ThermalNode = _MODULE.ThermalNode
CoolingZone = _MODULE.CoolingZone
APEXPiston = _MODULE.APEXPiston
MICROWAVEPiston = _MODULE.MICROWAVEPiston
SUPERNOVAPiston = _MODULE.SUPERNOVAPiston
SHADOWPiston = _MODULE.SHADOWPiston
GHOSTPiston = _MODULE.GHOSTPiston
APEXThermalOrchestrator = _MODULE.APEXThermalOrchestrator
load_manifest = _MODULE.load_manifest

__all__ = [
    'CoolingMode',
    'ThermalNode',
    'CoolingZone',
    'APEXPiston',
    'MICROWAVEPiston',
    'SUPERNOVAPiston',
    'SHADOWPiston',
    'GHOSTPiston',
    'APEXThermalOrchestrator',
    'load_manifest',
]
