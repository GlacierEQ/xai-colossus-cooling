"""
apex-core/__init__.py  — MIGRATION SHIM

WARNING: This package (apex-core, hyphen) is DEPRECATED.
The canonical Python package is apex_core (underscore).

This shim re-exports everything from apex_core so that any legacy
code path still importing from `apex-core` (via sys.path tricks)
continues to work during the migration window.

Migration deadline: remove this directory entirely once all imports
have been updated to `from apex_core import ...`.

Do NOT add new code here. All new development goes in apex_core/.
"""

import warnings

warnings.warn(
    "Importing from apex-core (hyphen) is deprecated. "
    "Use apex_core (underscore) instead. "
    "This shim will be removed in a future release.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export canonical surface
from apex_core import *  # noqa: F401, F403
from apex_core import (
    aspen_connector,
    cascade_prevention,
    immersion_cooling,
    thermal_orchestrator,
)

__all__ = [
    "aspen_connector",
    "cascade_prevention",
    "immersion_cooling",
    "thermal_orchestrator",
]
