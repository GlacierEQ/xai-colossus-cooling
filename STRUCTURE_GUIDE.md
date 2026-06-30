# Repository Structure Guide

## `apex_core/` vs `apex-core/` — Canonical Source of Truth

> **TL;DR:** Import from `apex_core` (Python package). `apex-core/` is a legacy hyphenated directory — do NOT import from it. Only `apex_core/` is actively maintained.

---

## Directory Inventory

| Path | Role | Status |
|------|------|--------|
| `apex_core/` | **Canonical Python package** — full module set, actively maintained | ✅ USE THIS |
| `apex-core/` | Legacy alias — hyphenated name is NOT a valid Python module identifier | ⚠️ LEGACY — do not import |

### `apex_core/` — Full Module Set
```
apex_core/
├── __init__.py              # Package init (45 bytes — lightweight)
├── aspen_connector.py       # Aspen Grove memory integration
├── aspen_logger.py          # Structured telemetry logging
├── cascade_prevention.py    # Thermal cascade detection + circuit breaker
├── colossus_manifest.json   # Cluster topology (IDENTICAL to apex-core/ copy)
├── immersion_cooling.py     # Immersion tank physics + control
├── mcp_validator.py         # MCP schema validation layer
├── thermal_orchestrator.py  # PRIMARY: 27k+ LOC hierarchical RL orchestrator
└── __pycache__/             # Auto-generated — gitignored
```

### `apex-core/` — Legacy (3 files only)
```
apex-core/
├── __init__.py              # Richer init (1070 bytes) — consolidate into apex_core/__init__.py
├── colossus_manifest.json   # DUPLICATE — SHA identical to apex_core/colossus_manifest.json
└── thermal_orchestrator.py  # NEAR-DUPLICATE — 26,930 bytes vs apex_core/ 27,380 bytes
                              # apex_core/ version is 450 bytes newer — use apex_core/
```

---

## Deduplication Action Plan

### Step 1 — Merge `__init__.py` (manual)
`apex-core/__init__.py` (1070 bytes) has richer content than `apex_core/__init__.py` (45 bytes).  
Merge the useful exports from `apex-core/__init__.py` into `apex_core/__init__.py`, then delete `apex-core/__init__.py`.

### Step 2 — Delete duplicate `colossus_manifest.json`
Both copies are byte-identical (SHA: `80d673e1efa1ef48d644db75deadd8591047e66c`).  
Delete `apex-core/colossus_manifest.json`. The canonical copy lives in `apex_core/colossus_manifest.json`.

### Step 3 — Reconcile `thermal_orchestrator.py`
`apex_core/thermal_orchestrator.py` (27,380 bytes) is the newer, larger version.  
`apex-core/thermal_orchestrator.py` (26,930 bytes) is 450 bytes older/smaller.  
Diff the two, merge any unique logic from `apex-core/` into `apex_core/`, then delete `apex-core/thermal_orchestrator.py`.

### Step 4 — Remove `apex-core/` directory
Once Steps 1–3 are complete, `apex-core/` should be empty. Delete it.

---

## Import Reference

```python
# CORRECT
from apex_core.thermal_orchestrator import ThermalOrchestrator
from apex_core.cascade_prevention import CascadeCircuitBreaker
from apex_core.immersion_cooling import ImmersionTankController

# WRONG — will fail (hyphenated dirs cannot be Python packages)
from apex-core.thermal_orchestrator import ThermalOrchestrator  # SyntaxError
```

---

## Why This Matters for Reviewers

xAI and SpaceX engineering reviewers will inspect `import` paths and package structure.  
A single canonical `apex_core/` package signals production-grade hygiene vs prototype sprawl.
