"""
UPS Manager — Phase 6
Monitors UPS strings and ride-through autonomy.
"""

from dataclasses import dataclass

UPS_STRINGS = 24
UPS_MINUTES_TARGET = 15


@dataclass
class UPSStatus:
    strings_online: int = UPS_STRINGS
    autonomy_minutes: float = UPS_MINUTES_TARGET
    discharge_active: bool = False


class UPSManager:
    def __init__(self):
        self.status = UPSStatus()

    def begin_discharge(self):
        self.status.discharge_active = True

    def end_discharge(self):
        self.status.discharge_active = False

    def snapshot(self):
        return vars(self.status)
