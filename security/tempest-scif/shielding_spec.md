# TEMPEST / SCIF Electromagnetic Shielding Specification
## xAI Colossus v2 — Phase 3 Security Layer

---

## Regulatory Basis
- **NSA TEMPEST Suite 300** — emanation suppression for classified computing environments
- **ICD 705** — SCIF construction requirements
- **IEEE 299-2006** — shielding effectiveness measurement standard
- **MIL-STD-461G** — equipment EMI/EMC requirements

---

## 7-Layer Physical Security + EMI Shielding Stack

| Layer | Type | Specification | Attenuation |
|-------|------|--------------|-------------|
| **L1** | Perimeter fence | 3.6m anti-climb steel mesh, 15kV electrification zones | N/A |
| **L2** | Outer shell | 300mm reinforced concrete, Category 5 blast rating | 40 dB @ 1 GHz |
| **L3** | Faraday cage | 3mm cold-rolled steel continuous welded panels, floor-to-ceiling | 80 dB @ 1 GHz |
| **L4** | RF absorber lining | 50mm pyramidal carbon-loaded foam, 30 MHz – 18 GHz | +20 dB supplemental |
| **L5** | Power line filter | EMI filters on all mains entry points, 100 dB insertion loss @ 10 kHz–1 GHz | 100 dB |
| **L6** | Optical isolation | Fiber-only data ingress/egress, no copper beyond L3 boundary | Absolute |
| **L7** | Air gap enforcement | 1.2m minimum separation from external walls for all active equipment | N/A |

**Total achieved attenuation (L2+L3+L4): ≥ 100 dB @ 1 GHz**

---

## SCIF Construction Details

### Structural
- Walls: 200mm CMU + 12mm steel liner continuous weld
- Floor: 150mm reinforced concrete slab + copper mesh ground plane
- Ceiling: 150mm concrete + steel deck bonded to cage
- Penetrations: Zero copper — all conduits are non-conductive or waveguide-beyond-cutoff

### Doors / Access Points
- RF-tight vault doors: 120 dB shielding effectiveness, Class 5 vault rating
- Mantrap vestibule: 2-door interlock, only one door open at any time
- Emergency egress: Panic bar interior-only, alarmed

### HVAC Penetrations
- Waveguide honeycomb panels on all air ducts (cutoff frequency > 18 GHz)
- Diameter: 6mm cells, depth 50mm
- Pressure differential maintained: +25 Pa positive inside SCIF

### Grounding
- Single-point ground (SPG) system per MIL-HDBK-419A
- Ground resistance: < 1 Ω
- Isolated ground plane for signal circuits

---

## Emanation Control Zones

| Zone | Radius | Protection Level | Access |
|------|--------|-----------------|--------|
| RED (processing) | 0–15m from servers | TEMPEST Level I | Cleared personnel only |
| AMBER (support) | 15–50m | TEMPEST Level II | Escorted access |
| GREEN (perimeter) | 50–200m | Standard physical | Badged staff |
| BLACK (public) | >200m | None required | Public |

---

## Testing & Certification Schedule

- **Pre-commissioning sweep:** NSA-certified TEMPEST lab measurement
- **Annual recertification:** Full shielding effectiveness test per IEEE 299
- **Trigger-based retest:** Any structural modification, new penetration, or anomaly detection
- **Continuous monitoring:** 24/7 RF leakage sensors at all 6 faces, alert threshold -90 dBm
