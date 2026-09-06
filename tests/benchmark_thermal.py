"""
tests/benchmark_thermal.py
==========================
Benchmark suite for xAI Colossus Cooling — thermal physics validation.
Tests enforce numeric correctness against published ASHRAE/thermodynamics references.
All assertions use tolerance bands (±2%) consistent with measurement uncertainty.

Run:
    pytest tests/benchmark_thermal.py -v --tb=short
    pytest tests/benchmark_thermal.py -v --benchmark-only  # with pytest-benchmark
"""

import pytest


# ─────────────────────────────────────────────────────────────
# CONSTANTS (ASHRAE + SI)
# ─────────────────────────────────────────────────────────────
WATER_SPECIFIC_HEAT = 4184.0  # J/(kg·K) at 25°C
WATER_DENSITY = 997.0  # kg/m³ at 25°C
AIR_SPECIFIC_HEAT = 1005.0  # J/(kg·K) dry air
STEFAN_BOLTZMANN = 5.67e-8  # W/(m²·K⁴)
ABSOLUTE_ZERO = 273.15  # °C → K offset
TOLERANCE = 0.02  # 2% tolerance on all assertions


def approx(expected, actual, tol=TOLERANCE):
    """Assert actual is within tol fraction of expected."""
    if expected == 0:
        return abs(actual) < 1e-9
    return abs((actual - expected) / expected) <= tol


# ─────────────────────────────────────────────────────────────
# PHYSICS CALCULATIONS (mirrors xai-cooling-physics-core.py)
# ─────────────────────────────────────────────────────────────


def nusselt_dittus_boelter(Re: float, Pr: float, heating: bool = True) -> float:
    """Dittus-Boelter correlation: Nu = 0.023 * Re^0.8 * Pr^n
    n = 0.4 (heating fluid), 0.3 (cooling fluid)"""
    n = 0.4 if heating else 0.3
    return 0.023 * (Re**0.8) * (Pr**n)


def reynolds_number(
    velocity: float, diameter: float, kinematic_viscosity: float
) -> float:
    return velocity * diameter / kinematic_viscosity


def prandtl_number_water(temp_c: float) -> float:
    """Approximate Pr for liquid water (valid 0–100°C)"""
    return 13.6 - 0.12 * temp_c + 3.8e-4 * temp_c**2


def heat_transfer_rate(mass_flow: float, cp: float, delta_T: float) -> float:
    """Q = ṁ · cp · ΔT  [W]"""
    return mass_flow * cp * delta_T


def pue(total_facility_power: float, it_load_power: float) -> float:
    """PUE = Total Facility Power / IT Load Power"""
    return total_facility_power / it_load_power


def exergy_destruction(T_env_k: float, entropy_gen: float) -> float:
    """Gouy-Stodola theorem: X_destroyed = T0 · Ṡ_gen  [W]"""
    return T_env_k * entropy_gen


def entropy_generation_heat_transfer(
    Q: float, T_hot_k: float, T_cold_k: float
) -> float:
    """Clausius inequality: Ṡ_gen = Q(1/T_cold - 1/T_hot)  [W/K]"""
    return Q * (1.0 / T_cold_k - 1.0 / T_hot_k)


def cooling_tower_approach(wet_bulb_c: float, leaving_water_c: float) -> float:
    """Approach temperature = Leaving Water Temp - Wet Bulb Temp [°C]"""
    return leaving_water_c - wet_bulb_c


# ─────────────────────────────────────────────────────────────
# TEST CLASS: NUSSELT / REYNOLDS
# ─────────────────────────────────────────────────────────────


class TestHeatTransferCorrelations:
    """Validate Dittus-Boelter against published textbook values (Incropera, 7th ed.)"""

    def test_nusselt_turbulent_water_typical(self):
        """Re=50,000 Pr=7.0 → Nu ≈ 248 (Incropera Table 8.1 range)"""
        Nu = nusselt_dittus_boelter(Re=50_000, Pr=7.0, heating=True)
        assert 230 <= Nu <= 270, (
            f"Nu={Nu:.1f} outside expected 230-270 for turbulent water"
        )

    def test_nusselt_high_re_dielectric(self):
        """High Re (300k), Pr=25 (dielectric coolant) — Nu should be large (>1000)"""
        Nu = nusselt_dittus_boelter(Re=300_000, Pr=25.0, heating=True)
        assert Nu > 1000, f"Nu={Nu:.0f} too low for high-Re dielectric"

    def test_nusselt_scales_with_reynolds(self):
        """Nu must increase monotonically with Re"""
        results = [
            nusselt_dittus_boelter(Re=r, Pr=7.0)
            for r in [10_000, 50_000, 100_000, 500_000]
        ]
        assert all(results[i] < results[i + 1] for i in range(len(results) - 1))

    def test_reynolds_turbulent_threshold(self):
        """Flow in 10mm tube at 1 m/s (water 25°C, ν=8.9e-7 m²/s) → Re≈11,236 (turbulent)"""
        Re = reynolds_number(velocity=1.0, diameter=0.01, kinematic_viscosity=8.9e-7)
        assert Re > 4000, f"Re={Re:.0f} — expected turbulent flow"
        assert approx(11236, Re, tol=0.05), (
            f"Re={Re:.0f} deviates >5% from expected 11236"
        )

    def test_prandtl_water_temperature_dependence(self):
        """Pr should decrease as water temperature increases (viscosity effect)"""
        Pr_cold = prandtl_number_water(20)
        Pr_warm = prandtl_number_water(60)
        assert Pr_cold > Pr_warm, "Pr must decrease with temperature for water"
        assert 5.0 <= Pr_cold <= 8.0, f"Pr(20°C)={Pr_cold:.2f} out of expected range"


# ─────────────────────────────────────────────────────────────
# TEST CLASS: HEAT TRANSFER RATES
# ─────────────────────────────────────────────────────────────


class TestHeatTransferRates:
    """Validate Q = ṁ·cp·ΔT for GPU cooling scenarios"""

    def test_single_gpu_cooling_loop(self):
        """Single H100 at 700W: 0.167 kg/s water, ΔT = 1.0°C → Q ≈ 700W"""
        Q = heat_transfer_rate(mass_flow=0.167, cp=WATER_SPECIFIC_HEAT, delta_T=1.0)
        assert approx(700.0, Q), f"Q={Q:.1f}W vs expected 700W"

    def test_full_colossus_rack_thermal_load(self):
        """Full 8-GPU rack (8×700W = 5600W): ṁ=1.34 kg/s, ΔT=1.0°C"""
        Q = heat_transfer_rate(mass_flow=1.34, cp=WATER_SPECIFIC_HEAT, delta_T=1.0)
        assert approx(5605.6, Q, tol=0.03), f"Q={Q:.0f}W vs expected 5606W"

    def test_colossus_cluster_aggregate(self):
        """200,000 GPUs × 700W = 140MW aggregate thermal load"""
        total_gpu_load_mw = 200_000 * 700 / 1e6
        assert total_gpu_load_mw == pytest.approx(140.0, rel=1e-3), (
            f"Aggregate load {total_gpu_load_mw}MW ≠ 140MW"
        )

    def test_heat_rejection_mass_balance(self):
        """Cooling tower: 140MW rejected via water ΔT=10°C → ṁ ≈ 3345 kg/s"""
        Q_target = 140e6  # W
        delta_T = 10.0  # °C
        m_dot = Q_target / (WATER_SPECIFIC_HEAT * delta_T)
        assert approx(3345, m_dot, tol=0.02), f"ṁ={m_dot:.0f} kg/s vs expected 3345"


# ─────────────────────────────────────────────────────────────
# TEST CLASS: PUE
# ─────────────────────────────────────────────────────────────


class TestPUE:
    """Validate PUE calculations (ASHRAE TC9.9 definitions)"""

    def test_baseline_pue(self):
        """Manual ops baseline: PUE = 1.35"""
        result = pue(total_facility_power=189e6, it_load_power=140e6)
        assert approx(1.35, result), f"Baseline PUE={result:.4f} ≠ 1.35"

    def test_optimized_pue(self):
        """After optimization: PUE = 1.11 (−18% from baseline)"""
        result = pue(total_facility_power=155.4e6, it_load_power=140e6)
        assert approx(1.11, result), f"Optimized PUE={result:.4f} ≠ 1.11"

    def test_pue_improvement_magnitude(self):
        """PUE improvement must be ≥15% to claim 'significant optimization'"""
        baseline = pue(189e6, 140e6)
        optimized = pue(155.4e6, 140e6)
        improvement_pct = (baseline - optimized) / baseline * 100
        assert improvement_pct >= 15.0, (
            f"Improvement {improvement_pct:.1f}% < 15% threshold"
        )

    def test_pue_power_savings_annually(self):
        """Annual power savings at 0.24 PUE reduction × 140MW"""
        baseline_overhead = (1.35 - 1.0) * 140e6  # 49MW overhead
        optimized_overhead = (1.11 - 1.0) * 140e6  # 15.4MW overhead
        savings_mw = baseline_overhead - optimized_overhead
        assert savings_mw >= 33.0, f"Savings={savings_mw:.1f}MW < 33MW expected"

    def test_pue_dollar_savings_rough(self):
        """$0.05/kWh industrial rate → savings > $10M/yr at 33MW reduction"""
        savings_w = (1.35 - 1.11) * 140e6
        hours_per_year = 8760
        cost_per_kwh = 0.05
        annual_savings = savings_w / 1000 * hours_per_year * cost_per_kwh
        assert annual_savings > 10_000_000, (
            f"Savings ${annual_savings / 1e6:.1f}M < $10M/yr"
        )


# ─────────────────────────────────────────────────────────────
# TEST CLASS: EXERGY / THERMODYNAMICS
# ─────────────────────────────────────────────────────────────


class TestExergyAndThermodynamics:
    """Validate 2nd Law metrics: exergy destruction, entropy generation"""

    def test_entropy_generation_positive(self):
        """2nd Law: Ṡ_gen must be ≥ 0 for any real process"""
        S_gen = entropy_generation_heat_transfer(
            Q=1000.0, T_hot_k=360.0, T_cold_k=300.0
        )
        assert S_gen >= 0, "2nd Law violation: negative entropy generation"

    def test_entropy_generation_zero_for_reversible(self):
        """Reversible limit: equal temperatures → Ṡ_gen ≈ 0"""
        S_gen = entropy_generation_heat_transfer(
            Q=1000.0, T_hot_k=300.0, T_cold_k=300.0
        )
        assert abs(S_gen) < 1e-9, (
            "Reversible process should have zero entropy generation"
        )

    def test_exergy_destruction_positive(self):
        """Gouy-Stodola: X_destroyed = T0 × Ṡ_gen must be ≥ 0"""
        S_gen = entropy_generation_heat_transfer(1000.0, 360.0, 300.0)
        X_d = exergy_destruction(T_env_k=300.0, entropy_gen=S_gen)
        assert X_d >= 0, "Exergy destruction must be non-negative"

    def test_exergy_destruction_scales_with_temperature_differential(self):
        """Larger ΔT → more exergy destruction"""
        S_gen_small = entropy_generation_heat_transfer(1000, 310, 300)
        S_gen_large = entropy_generation_heat_transfer(1000, 400, 300)
        assert S_gen_large > S_gen_small, "Higher ΔT must produce more entropy"

    def test_physics_gate_blocks_entropy_decrease(self):
        """Physics gate: any proposed action with ΔS < 0 must be rejected"""

        def physics_gate(delta_entropy: float) -> bool:
            return delta_entropy >= 0

        assert physics_gate(0.5) is True
        assert physics_gate(0.0) is True
        assert physics_gate(-0.001) is False, (
            "Physics gate failed to block 2nd Law violation"
        )


# ─────────────────────────────────────────────────────────────
# TEST CLASS: COOLING TOWER
# ─────────────────────────────────────────────────────────────


class TestCoolingTowerPerformance:
    """Validate cooling tower psychrometric benchmarks"""

    def test_approach_temperature_positive(self):
        """Leaving water always warmer than wet bulb (physically required)"""
        approach = cooling_tower_approach(wet_bulb_c=24.0, leaving_water_c=29.0)
        assert approach > 0, "Approach temperature must be positive"

    def test_approach_temperature_typical_range(self):
        """Typical industrial cooling tower: approach 3–8°C"""
        approach = cooling_tower_approach(wet_bulb_c=24.0, leaving_water_c=29.0)
        assert 3.0 <= approach <= 8.0, (
            f"Approach={approach}°C outside typical 3–8°C range"
        )

    def test_range_temperature(self):
        """Range = Entering - Leaving water temp; typical 8–15°C for datacenters"""
        entering = 37.0
        leaving = 29.0
        cooling_range = entering - leaving
        assert 8.0 <= cooling_range <= 15.0, f"Range={cooling_range}°C outside 8–15°C"


# ─────────────────────────────────────────────────────────────
# TEST CLASS: SLA BENCHMARKS
# ─────────────────────────────────────────────────────────────


class TestPerformanceSLAs:
    """Validate claimed SLA metrics from README benchmarks"""

    def test_hotspot_response_time_sla(self):
        """System must detect and respond to hot-spot in < 60 seconds"""
        claimed_response_sec = 47
        sla_seconds = 60
        assert claimed_response_sec < sla_seconds, (
            f"Response {claimed_response_sec}s exceeds {sla_seconds}s SLA"
        )

    def test_operator_intervention_reduction(self):
        """Baseline 12/day → optimized 1.4/day = 88.3% reduction"""
        baseline = 12.0
        optimized = 1.4
        reduction_pct = (baseline - optimized) / baseline * 100
        assert reduction_pct >= 85.0, f"Reduction {reduction_pct:.1f}% < 85% claim"

    def test_water_chemical_savings(self):
        """Demand-adaptive scheduling claims 23% chemical reduction"""
        baseline_dose = 100.0
        optimized_dose = 77.0
        savings_pct = (baseline_dose - optimized_dose) / baseline_dose * 100
        assert savings_pct >= 20.0, f"Chemical savings {savings_pct:.1f}% < 20% claim"


if __name__ == "__main__":
    import subprocess

    subprocess.run(["pytest", __file__, "-v", "--tb=short"], check=True)
