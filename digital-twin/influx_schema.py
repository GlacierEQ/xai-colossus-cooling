"""
InfluxDB Schema — Phase 7
Canonical measurements for Colossus digital twin.
"""

MEASUREMENTS = {
    "colossus_water_flow": {
        "tags": ["source", "status", "event_type"],
        "fields": ["volume_litres", "level_pct", "autonomy_hours", "drain_rate_lpm", "fill_rate_lpm", "leak_detected", "permeate_lpm", "product_tds_ppm", "rejection_pct", "diff_pressure_bar", "recovery_rate", "cip_active"],
    },
    "colossus_gpu_thermal": {
        "tags": ["scope", "zone_id", "node_id", "level"],
        "fields": ["total_nodes", "total_power_kw", "throttled_gpus", "alert_gpus", "mean_die_temp_c", "max_die_temp_c"],
    },
    "colossus_power": {
        "tags": ["scope", "source"],
        "fields": ["mw_active", "mw_available"],
    },
    "colossus_kpi": {
        "tags": ["kpi_name", "severity"],
        "fields": ["value", "target", "delta"],
    },
}
