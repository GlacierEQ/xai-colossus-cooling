"""
conftest.py — root pytest configuration for xai-colossus-cooling

Solves the hyphenated-directory import problem:
  mastermind-fusion/  cannot be imported as `mastermind-fusion` in Python.
  We add it to sys.path as `mastermind_fusion` via a path alias.

Also adds project root and connectors to sys.path so all tests
can do `from connectors.x import Y` and `from mastermind_fusion.x import Y`
without installing the package.
"""

import sys
import types
from pathlib import Path

ROOT = Path(__file__).parent.resolve()

# Add root so `from connectors.x` and `from apex_core.x` work
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Alias mastermind-fusion/ -> mastermind_fusion module
_fusion_path = ROOT / 'mastermind-fusion'
if _fusion_path.exists() and str(_fusion_path) not in sys.path:
    sys.path.insert(0, str(_fusion_path.parent))
    # Create a module alias so `import mastermind_fusion` resolves to mastermind-fusion/
    import importlib.util
    _spec = importlib.util.spec_from_file_location(
        'mastermind_fusion',
        str(_fusion_path / '__init__.py'),
        submodule_search_locations=[str(_fusion_path)],
    )
    if _spec and _spec.loader:
        _mod = importlib.util.module_from_spec(_spec)
        sys.modules['mastermind_fusion'] = _mod
        # Also register submodules discovered so far
        for _sub in _fusion_path.glob('*.py'):
            if _sub.stem == '__init__':
                continue
            _sub_spec = importlib.util.spec_from_file_location(
                f'mastermind_fusion.{_sub.stem}',
                str(_sub),
            )
            if _sub_spec and _sub_spec.loader:
                _sub_mod = importlib.util.module_from_spec(_sub_spec)
                sys.modules[f'mastermind_fusion.{_sub.stem}'] = _sub_mod
        _spec.loader.exec_module(_mod)
