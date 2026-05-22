"""
Twin State Composer — Phase 7
Aggregates snapshots from water, GPU, and power agents into one state document.
"""
from datetime import datetime, timezone


class TwinStateComposer:
    def compose(self, water=None, gpu=None, power=None):
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "water": water or {},
            "gpu": gpu or {},
            "power": power or {},
        }
