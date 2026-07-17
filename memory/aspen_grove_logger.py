# Re-export — canonical implementation in src/
# Keeps import paths valid for apex_core and connectors that use:
#   from memory.aspen_grove_logger import AspenGroveLogger
import importlib.util
import os

_src_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "src",
    "memory",
    "aspen_grove_logger.py",
)
_spec = importlib.util.spec_from_file_location("_real_aspen_logger", _src_path)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
AspenGroveLogger = _mod.AspenGroveLogger
QUEUE_DEPTH_WARN = _mod.QUEUE_DEPTH_WARN
QUEUE_MAX_SIZE = _mod.QUEUE_MAX_SIZE

__all__ = ["AspenGroveLogger", "QUEUE_DEPTH_WARN", "QUEUE_MAX_SIZE"]
