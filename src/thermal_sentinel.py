import asyncio
from collections import deque
import statistics

class ThermalSentinel:
    """
    APEX Predictive Thermal Sentinel
    Simulates LSTM-based predictive ramping for Coolant Distribution Units (CDUs).
    """
    
    def __init__(self, rack_id):
        self.rack_id = rack_id
        self.history = deque(maxlen=60) # 1-minute window at 1Hz
        self.temp_threshold = 82.0
        self.is_ramping = False

    def ingest_telemetry(self, temp):
        """Receives 1ms telemetry from Nanosphere (simulated at 1Hz for model window)."""
        self.history.append(temp)

    def predict_throttle(self):
        """
        Simulates the LSTM inference.
        Predicts if a thermal throttle will occur in the next 10 minutes.
        """
        if len(self.history) < 10:
            return False
        
        # Simple linear projection as a proxy for LSTM forecasting
        recent = list(self.history)[-10:]
        trend = recent[-1] - recent[0]
        
        predicted_temp = recent[-1] + (trend * 2) # Crude 10-minute projection
        
        if predicted_temp > self.temp_threshold:
            return True
        return False

    async def ramp_cdu(self):
        """Sends command to the cooling loop hardware."""
        if not self.is_ramping:
            print(f"❄️ [PREDICTIVE] Ramping CDU for {self.rack_id} (Targeting PUE 1.15)")
            self.is_ramping = True
            await asyncio.sleep(0.5)

async def main():
    sentinel = ThermalSentinel("RACK_NVL72_01")
    print(f"🚀 APEX THERMAL SENTINEL ONLINE: {sentinel.rack_id}")
    
    # Simulate rising heat
    sim_temps = [65, 68, 72, 75, 78, 80, 81]
    for t in sim_temps:
        sentinel.ingest_telemetry(t)
        if sentinel.predict_throttle():
            await sentinel.ramp_cdu()
        await asyncio.sleep(0.5)

if __name__ == "__main__":
    asyncio.run(main())
