# 🔧 Water Plant Commissioning Sequence (6-Phase Deployment)

## Phase 1: Mechanical Assembly & Pressure Testing (Week 1)

### 1.1 Pump Station Assembly
- [ ] Install three 100% capacity centrifugal pumps in parallel configuration
- [ ] Mount each on independent baseplate with vibration isolators
- [ ] Connect suction lines (short, large-diameter) to return tank
- [ ] Connect discharge lines through check valves (prevent backflow)
- [ ] Install pressure relief valve (set to 5.0 bar, lock pin)
- [ ] Install isolation ball valves on each pump discharge

### 1.2 Pressure Testing
- [ ] Fill entire circuit with deionized water (50K liters)
- [ ] Manually pressurize to 2.0 bar via hand pump (check for leaks)
- [ ] Increase to 3.5 bar, inspect all joints and seals (24 hr hold test)
- [ ] Increase to 6.0 bar (relief valve activation test)
- [ ] Document all test points and pressures in log book
- [ ] Certificate of Compliance signed by test engineer

---

## Phase 2: Heat Exchanger Setup & Water Chemistry (Week 2)

### 2.1 HX Array Installation
- [ ] Mount 8 plate-frame heat exchangers in horizontal orientation
- [ ] Connect inlet manifold (all 8 units see same inlet pressure)
- [ ] Stagger outlet connections to common return header
- [ ] Flush both sides (water side and cooling medium side) with DI water
- [ ] Pressure test cooling medium side to 3.5 bar (verify gasket seals)

### 2.2 Water Chemistry Conditioning
- [ ] Add alkalinity buffer (pH 7.5-8.0 target)
- [ ] Dose microbial inhibitor (prevent algae/bacteria at 50°C+ temps)
- [ ] Add corrosion inhibitor (for aluminum/copper alloys in HX)
- [ ] Measure conductivity, particulates (< 10 ppm target)
- [ ] Run 6 hours at low flow (3,000 LPM) to condition surfaces

---

## Phase 3: Filtration System Commissioning (Week 2-3)

### 3.1 Filter Installation
- [ ] Install three cartridge stages (100µm, 25µm, 5µm) in housings
- [ ] Mount bypass valve (set to 2.0 bar cracking pressure)
- [ ] Connect inlet from HX array, outlet to manifold inlet
- [ ] Test bypass valve: gradually increase inlet pressure, confirm opens at 2.0 bar

### 3.2 Water Polishing (First-Pass Filtration)
- [ ] Run full system at 6,000 LPM for 2 hours (pre-filtration pass)
- [ ] Monitor pressure drop across filter (should be < 0.5 bar initially)
- [ ] Measure water quality every 30 min (particulate count)
- [ ] Target: < 5 ppm particles (confirmed via particle counter)
- [ ] Replace cartridges if saturation approaches 1.5 bar ΔP

---

## Phase 4: Manifold Balancing & Zone Testing (Week 3)

### 4.1 Flow Distribution Verification
- [ ] Install magnetic flow meters at each of 4 primary zone inlets
- [ ] Install pressure transducers at 12 measurement points (pump, HX, filter, zones, return)
- [ ] Set nominal flow to 12,000 LPM (all zones receiving 3,000 LPM each)
- [ ] Measure individual branch flows (sample 20 branches across each zone)
- [ ] Verify variance < 2% (target: 1.2%)

### 4.2 Pressure Drop Characterization
- [ ] Map pressure profile across entire system (document in commissioning log)
- [ ] Confirm rack inlet pressure > 2.5 bar (adequate for microchannel blocks)
- [ ] Test emergency isolation valves (each zone can be shut independently)
- [ ] Record baseline temperature rise across HX (should see ~10°C rise with thermal load)

---

## Phase 5: Thermal Load & Steady-State Validation (Week 4)

### 5.1 Mock Thermal Load (Pre-GPU Installation)
- [ ] Temporarily install resistance heaters equivalent to 1M GPU load (1.4 MW heat)
- [ ] Run system at nominal 12,000 LPM
- [ ] Record inlet/outlet temps, pressure, flow for 8 hours
- [ ] Verify outlet temp stabilizes (< 45°C with cooling medium @ 20°C ambient)
- [ ] Confirm no cavitation (no noise, pressure steady > 2.5 bar at racks)

### 5.2 Emergency Response Drills
- [ ] Simulate pump failure: shut down one active pump, confirm auto-failover
- [ ] Simulate flow surge: increase frequency demand 10%, monitor pressures
- [ ] Simulate filter bypass: artificially clog filter, confirm bypass opens
- [ ] Emergency shutdown: hit E-stop button, confirm all flow stops in < 5 seconds

---

## Phase 6: Final Handover & Operational Readiness (Week 4-5)

### 6.1 Documentation & Training
- [ ] Complete Commissioning Certificate of Completion
- [ ] Provide operations manual (pump curves, manifold maps, emergency procedures)
- [ ] Train facilities team on daily monitoring tasks
- [ ] Install permanent pressure/temperature gauges (analog backups)
- [ ] Calibrate all digital sensors (scope test against standards)

### 6.2 Long-Term Monitoring Setup
- [ ] Wire all sensors to SCADA/APEX control system
- [ ] Set alarm thresholds:
  - Pump discharge pressure < 3.5 bar → ALERT
  - Filter ΔP > 1.5 bar → ALERT (schedule cartridge replacement)
  - GPU rack outlet temp > 50°C → ALERT (thermal load check)
  - Return tank level < 40K liters → ALERT (leak detected)
- [ ] Confirm telemetry streaming to InfluxDB + Grafana dashboards

### 6.3 Operational Handover
- [ ] Facilities team signs off on readiness
- [ ] Publish daily monitoring checklist (30-min intervals initially)
- [ ] Schedule weekly pressure calibration checks
- [ ] Plan annual HX chemical cleaning + filter replacement
- [ ] Schedule 5-year major overhaul (pump reseals, HX replacement budget)

---

## Success Criteria

✅ **Phase 1:** Zero leaks at 6.0 bar pressure test  
✅ **Phase 2:** Water chemistry stable (pH 7.5-8.0, conductivity < 800 µS)  
✅ **Phase 3:** Particles < 5 ppm (confirmed via particle counter)  
✅ **Phase 4:** Flow variance < 1.2% across all zones  
✅ **Phase 5:** Outlet temp stable @ 45°C with 1.4 MW mock load  
✅ **Phase 6:** All sensors calibrated, telemetry confirmed live  

**Total Commissioning Time:** 4-5 weeks (with full-time dedicated team)

---

*Commissioning Plan v1.0 · GlacierEQ Water Plant Deployment*
