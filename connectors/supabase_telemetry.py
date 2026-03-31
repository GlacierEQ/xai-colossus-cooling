#!/usr/bin/env python3
"""
Supabase Telemetry Connector — xAI Colossus Cooling
GlacierEQ APEX Architecture

Persists all thermal telemetry to Supabase.
Prioritizes schema from database/supabase_schema.sql if available.
"""

import os
import json
import logging
from datetime import datetime, UTC
from typing import List, Dict, Optional

logger = logging.getLogger('CONNECTOR-SUPABASE')


class SupabaseTelemetryConnector:
    """
    Connects the APEX thermal orchestrator to Supabase.
    Streams thermal events as they happen — no batching delays.
    """
    
    TABLES = {
        'thermal_events':   'colossus_thermal_events',
        'anomalies':        'colossus_anomalies',
        'zone_snapshots':   'colossus_zone_snapshots',
        'piston_activations': 'colossus_piston_log',
        'emergency_log':    'colossus_emergency_log'
    }
    
    def __init__(self):
        self.url = os.getenv('SUPABASE_URL', '')
        self.key = os.getenv('SUPABASE_SERVICE_KEY', '')
        self.connected = False
        self._client = None
        self.schema = self._load_schema()
        logger.info('Supabase Telemetry Connector initialized')
    
    def _load_schema(self) -> str:
        """Load schema from SQL file or fallback to hardcoded string."""
        schema_path = os.path.join(os.path.dirname(__file__), '../database/supabase_schema.sql')
        if os.path.exists(schema_path):
            with open(schema_path, 'r') as f:
                return f.read()
        return DEFAULT_SUPABASE_SCHEMA

    def connect(self):
        try:
            from supabase import create_client
            self._client = create_client(self.url, self.key)
            self.connected = True
            logger.info('Supabase connected ✓')
        except Exception as e:
            logger.error(f'Supabase connection failed: {e}')
            self.connected = False
    
    async def log_thermal_event(self, node_id: str, temp: float, alert_level: int, zone_id: str):
        payload = {
            'node_id': node_id,
            'zone_id': zone_id,
            'temp_celsius': temp,
            'alert_level': alert_level,
            'timestamp': datetime.now(UTC).isoformat()
        }
        await self._insert(self.TABLES['thermal_events'], payload)
    
    async def log_anomaly(self, node_id: str, deviation: float, baseline: float):
        payload = {
            'node_id': node_id,
            'deviation_celsius': deviation,
            'baseline_celsius': baseline,
            'severity': 'HIGH' if deviation > 15 else 'MEDIUM' if deviation > 8 else 'LOW',
            'timestamp': datetime.now(UTC).isoformat()
        }
        await self._insert(self.TABLES['anomalies'], payload)
    
    async def log_piston_activation(self, piston_name: str, tier: str, trigger: str, result_summary: dict):
        payload = {
            'piston': piston_name,
            'tier': tier,
            'trigger': trigger,
            'result_summary': json.dumps(result_summary)[:500],
            'timestamp': datetime.now(UTC).isoformat()
        }
        await self._insert(self.TABLES['piston_activations'], payload)
    
    async def log_emergency(self, critical_nodes: List[str], max_temp: float, actions: List[dict]):
        payload = {
            'critical_node_count': len(critical_nodes),
            'max_temp_celsius': max_temp,
            'nodes': json.dumps(critical_nodes),
            'actions_taken': json.dumps(actions)[:1000],
            'timestamp': datetime.now(UTC).isoformat()
        }
        await self._insert(self.TABLES['emergency_log'], payload)
    
    async def _insert(self, table: str, payload: dict):
        if not self.connected or not self._client:
            logger.debug(f'[OFFLINE MODE] Would insert to {table}: {payload}')
            return
        try:
            self._client.table(table).insert(payload).execute()
        except Exception as e:
            logger.error(f'Supabase insert failed [{table}]: {e}')


# Fallback schema for Supabase setup
DEFAULT_SUPABASE_SCHEMA = """
-- colossus_thermal_events
CREATE TABLE IF NOT EXISTS colossus_thermal_events (
    id BIGSERIAL PRIMARY KEY,
    node_id TEXT NOT NULL,
    zone_id TEXT NOT NULL,
    temp_celsius NUMERIC(5,2),
    alert_level INTEGER DEFAULT 0,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);
"""
