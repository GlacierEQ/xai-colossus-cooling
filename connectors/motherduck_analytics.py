#!/usr/bin/env python3
"""
MotherDuck Analytics Connector — xAI Colossus Cooling
GlacierEQ APEX Architecture

DuckDB-powered analytics engine for:
  - Historical thermal trend analysis
  - Anomaly pattern detection
  - PUE calculation and optimization
  - Capacity planning queries
  - Job scheduler thermal correlation
"""

import os
import logging
from datetime import datetime, UTC, timedelta
from typing import List, Dict, Optional

logger = logging.getLogger('CONNECTOR-MOTHERDUCK')


class MotherDuckAnalyticsConnector:
    """
    MotherDuck (DuckDB cloud) connector for thermal analytics.
    Enables SHERLOCK-ALPHA forensic queries on thermal history.
    """
    
    def __init__(self):
        self.token = os.getenv('MOTHERDUCK_TOKEN', '')
        self.db_name = os.getenv('MOTHERDUCK_DB', 'colossus_cooling')
        self.conn = None
        self.connected = False
        logger.info('MotherDuck Analytics Connector initialized')
    
    def connect(self):
        try:
            import duckdb
            self.conn = duckdb.connect(f'md:{self.db_name}?motherduck_token={self.token}')
            self.connected = True
            logger.info('MotherDuck connected ✓')
            self._init_schema()
        except Exception as e:
            logger.warning(f'MotherDuck offline — using in-memory DuckDB: {e}')
            import duckdb
            self.conn = duckdb.connect(':memory:')
            self._init_schema()
    
    def _init_schema(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS thermal_history (
                ts          TIMESTAMP,
                node_id     VARCHAR,
                zone_id     VARCHAR,
                temp_c      DOUBLE,
                power_kw    DOUBLE,
                alert_level INTEGER
            );
            CREATE TABLE IF NOT EXISTS pue_log (
                ts          TIMESTAMP,
                it_power_kw DOUBLE,
                total_power_kw DOUBLE,
                pue         DOUBLE
            );
        """)
    
    def ingest_thermal_batch(self, records: List[Dict]):
        """Bulk insert thermal records into DuckDB."""
        if not self.conn or not records:
            return
        rows = [
            (r.get('timestamp', datetime.now(UTC)),
             r['node_id'], r['zone_id'],
             r['temp_celsius'], r.get('power_kw', 0.0),
             r.get('alert_level', 0))
            for r in records
        ]
        self.conn.executemany(
            'INSERT INTO thermal_history VALUES (?, ?, ?, ?, ?, ?)', rows
        )
    
    def query_hot_zones(self, window_minutes: int = 60) -> List[Dict]:
        """SHERLOCK-ALPHA: Find zones with elevated temps in recent window."""
        result = self.conn.execute("""
            SELECT zone_id,
                   AVG(temp_c)  AS avg_temp,
                   MAX(temp_c)  AS peak_temp,
                   COUNT(*)     AS event_count
            FROM thermal_history
            WHERE ts > NOW() - INTERVAL '60 minutes'
              AND alert_level >= 1
            GROUP BY zone_id
            ORDER BY peak_temp DESC
        """).fetchall()
        return [{'zone_id': r[0], 'avg_temp': r[1], 'peak_temp': r[2], 'events': r[3]} for r in result]
    
    def query_pue_trend(self, days: int = 7) -> List[Dict]:
        """Calculate PUE trend over last N days."""
        result = self.conn.execute(f"""
            SELECT DATE_TRUNC('hour', ts) AS hour,
                   AVG(pue) AS avg_pue,
                   MIN(pue) AS best_pue
            FROM pue_log
            WHERE ts > NOW() - INTERVAL '{days} days'
            GROUP BY 1
            ORDER BY 1
        """).fetchall()
        return [{'hour': str(r[0]), 'avg_pue': r[1], 'best_pue': r[2]} for r in result]
    
    def query_anomaly_patterns(self) -> List[Dict]:
        """SHERLOCK forensic: find recurring anomaly patterns."""
        result = self.conn.execute("""
            SELECT node_id,
                   COUNT(*) AS anomaly_count,
                   AVG(temp_c) AS avg_temp_during_anomaly,
                   MAX(temp_c) AS peak_temp
            FROM thermal_history
            WHERE alert_level >= 2
            GROUP BY node_id
            HAVING COUNT(*) > 3
            ORDER BY anomaly_count DESC
            LIMIT 20
        """).fetchall()
        return [{'node': r[0], 'count': r[1], 'avg': r[2], 'peak': r[3]} for r in result]
