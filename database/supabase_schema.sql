-- ============================================================
-- APEX Colossus Cooling — Supabase Schema
-- GlacierEQ Sovereign Stack
-- Run this in your Supabase SQL Editor (Settings > SQL Editor)
-- ============================================================

-- 1. Thermal Events (main time-series table)
CREATE TABLE IF NOT EXISTS colossus_thermal_events (
    id            BIGSERIAL PRIMARY KEY,
    node_id       TEXT        NOT NULL,
    zone_id       TEXT        NOT NULL,
    temp_celsius  NUMERIC(5,2),
    alert_level   INTEGER     DEFAULT 0,
    power_kw      NUMERIC(6,2),
    gpu_util_pct  NUMERIC(5,2),
    timestamp     TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Anomalies (SHADOW piston detections)
CREATE TABLE IF NOT EXISTS colossus_anomalies (
    id                  BIGSERIAL PRIMARY KEY,
    node_id             TEXT        NOT NULL,
    deviation_celsius   NUMERIC(5,2),
    baseline_celsius    NUMERIC(5,2),
    severity            TEXT        DEFAULT 'LOW' CHECK (severity IN ('LOW','MEDIUM','HIGH')),
    resolved            BOOLEAN     DEFAULT FALSE,
    timestamp           TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Zone Snapshots (periodic zone-level summaries)
CREATE TABLE IF NOT EXISTS colossus_zone_snapshots (
    id                    BIGSERIAL PRIMARY KEY,
    zone_id               TEXT        NOT NULL,
    avg_temp_celsius      NUMERIC(5,2),
    peak_temp_celsius     NUMERIC(5,2),
    active_nodes          INTEGER,
    crac_units_active     INTEGER     DEFAULT 0,
    liquid_flow_lpm       NUMERIC(7,2) DEFAULT 0,
    cooling_mode          TEXT        DEFAULT 'STEADY_STATE',
    timestamp             TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Piston Activation Log
CREATE TABLE IF NOT EXISTS colossus_piston_log (
    id              BIGSERIAL PRIMARY KEY,
    piston          TEXT        NOT NULL,
    tier            TEXT        NOT NULL CHECK (tier IN ('APEX','BLACK','GREY')),
    trigger         TEXT,
    result_summary  TEXT,
    duration_ms     INTEGER,
    timestamp       TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Emergency Log
CREATE TABLE IF NOT EXISTS colossus_emergency_log (
    id                    BIGSERIAL PRIMARY KEY,
    critical_node_count   INTEGER,
    max_temp_celsius      NUMERIC(5,2),
    nodes                 JSONB,
    actions_taken         JSONB,
    resolved_at           TIMESTAMPTZ,
    timestamp             TIMESTAMPTZ DEFAULT NOW()
);

-- 6. PUE Log
CREATE TABLE IF NOT EXISTS colossus_pue_log (
    id              BIGSERIAL PRIMARY KEY,
    it_power_kw     NUMERIC(10,2),
    total_power_kw  NUMERIC(10,2),
    pue             NUMERIC(5,4),
    zone_id         TEXT,
    timestamp       TIMESTAMPTZ DEFAULT NOW()
);

-- ── Indexes for query performance ─────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_thermal_events_zone_ts   ON colossus_thermal_events(zone_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_thermal_events_node_ts   ON colossus_thermal_events(node_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_thermal_events_alert     ON colossus_thermal_events(alert_level) WHERE alert_level > 0;
CREATE INDEX IF NOT EXISTS idx_anomalies_node_ts        ON colossus_anomalies(node_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_anomalies_severity       ON colossus_anomalies(severity);
CREATE INDEX IF NOT EXISTS idx_piston_log_piston_ts     ON colossus_piston_log(piston, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_zone_snapshots_zone_ts   ON colossus_zone_snapshots(zone_id, timestamp DESC);

-- ── Row Level Security ─────────────────────────────────────────────────────
ALTER TABLE colossus_thermal_events  ENABLE ROW LEVEL SECURITY;
ALTER TABLE colossus_anomalies       ENABLE ROW LEVEL SECURITY;
ALTER TABLE colossus_zone_snapshots  ENABLE ROW LEVEL SECURITY;
ALTER TABLE colossus_piston_log      ENABLE ROW LEVEL SECURITY;
ALTER TABLE colossus_emergency_log   ENABLE ROW LEVEL SECURITY;
ALTER TABLE colossus_pue_log         ENABLE ROW LEVEL SECURITY;

-- Public read (dashboard can query without auth)
CREATE POLICY "public_read_thermal"  ON colossus_thermal_events  FOR SELECT USING (true);
CREATE POLICY "public_read_anomalies" ON colossus_anomalies       FOR SELECT USING (true);
CREATE POLICY "public_read_piston"   ON colossus_piston_log      FOR SELECT USING (true);
CREATE POLICY "public_read_zones"    ON colossus_zone_snapshots  FOR SELECT USING (true);

-- Service role write only
CREATE POLICY "service_write_thermal"   ON colossus_thermal_events  FOR INSERT WITH CHECK (true);
CREATE POLICY "service_write_anomalies" ON colossus_anomalies       FOR INSERT WITH CHECK (true);
CREATE POLICY "service_write_piston"    ON colossus_piston_log      FOR INSERT WITH CHECK (true);
CREATE POLICY "service_write_zones"     ON colossus_zone_snapshots  FOR INSERT WITH CHECK (true);
CREATE POLICY "service_write_emergency" ON colossus_emergency_log   FOR INSERT WITH CHECK (true);
CREATE POLICY "service_write_pue"       ON colossus_pue_log         FOR INSERT WITH CHECK (true);

-- ── Real-time subscriptions ────────────────────────────────────────────────
ALTER PUBLICATION supabase_realtime ADD TABLE colossus_thermal_events;
ALTER PUBLICATION supabase_realtime ADD TABLE colossus_anomalies;
ALTER PUBLICATION supabase_realtime ADD TABLE colossus_piston_log;

-- ── Seed demo data (optional — remove for production) ─────────────────────
INSERT INTO colossus_thermal_events (node_id, zone_id, temp_celsius, alert_level, power_kw)
SELECT
    'NODE-' || LPAD((gs % 100)::text, 4, '0') || '-' || LPAD((gs / 100)::text, 3, '0'),
    'ZONE-' || LPAD((gs % 6)::text, 3, '0'),
    60 + random() * 25,
    CASE WHEN random() > 0.9 THEN 2 WHEN random() > 0.7 THEN 1 ELSE 0 END,
    600 + random() * 200
FROM generate_series(1, 100) AS gs;
