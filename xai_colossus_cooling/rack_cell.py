from dataclasses import dataclass

@dataclass
class RackCell:
    cell_id: int
    current_temp: float = 45.0
    target_temp: float = 35.0
    autonomy_enabled: bool = True
    cooling_level: float = 0.5

    def check_temperature(self) -> bool:
        return self.current_temp <= self.target_temp

    def adjust_cooling(self, delta: float):
        if self.autonomy_enabled:
            self.current_temp = max(20.0, self.current_temp + delta)
            temp_diff = self.target_temp - self.current_temp
            self.cooling_level = min(1.0, max(0.0, 0.5 + temp_diff * 0.01))

    def sync_state(self, state: dict):
        self.target_temp = state.get('global_target_temp', 35.0)
        self.autonomy_enabled = state.get('enable_autonomy', True)

    def get_status(self):
        return {'cell_id': self.cell_id, 'current_temp': self.current_temp, 'target_temp': self.target_temp, 'healthy': self.check_temperature()}