#!/usr/bin/env python3
"""Stable repository-root entrypoint for the cooling demonstration CLI.

The implementation remains owned by ``omega.apex_cli``.  Keeping this shim at
repository root preserves documented and CI call sites without duplicating CLI
logic.
"""

from omega.apex_cli import main


if __name__ == "__main__":
    main()
