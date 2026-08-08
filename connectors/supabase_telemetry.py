#!/usr/bin/env python3
"""
Supabase Telemetry Connector — xAI Colossus Cooling
GlacierEQ APEX Architecture

Persists all thermal telemetry to Supabase for:
  - Time-series thermal data storage
  - Anomaly log persistence  
  - Real-time dashboard feeds
  - Historical trend analysis
"""

import os
import json
import logging
from datetime import datetime
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
        logger.info('Supabase Telemetry Connector initialized')
    
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
            'timestamp': datetime.utcnow().isoformat()
        }
        await self._insert(self.TABLES['thermal_events'], payload)
    
    async def log_anomaly(self, node_id: str, deviation: float, baseline: float):
        payload = {
            'node_id': node_id,
            'deviation_celsius': deviation,
            'baseline_celsius': baseline,
            'severity': 'HIGH' if deviation > 15 else 'MEDIUM' if deviation > 8 else 'LOW',
            'timestamp': datetime.utcnow().isoformat()
        }
        await self._insert(self.TABLES['anomalies'], payload)
    
    async def log_piston_activation(self, piston_name: str, tier: str, trigger: str, result: dict):
        payload = {
            'piston': piston_name,
            'tier': tier,
            'trigger': trigger,
            'result_summary': json.dumps(result)[:500],
            'timestamp': datetime.utcnow().isoformat()
        }
        await self._insert(self.TABLES['piston_activations'], payload)
    
    async def log_emergency(self, critical_nodes: List[str], max_temp: float, actions: List[dict]):
        payload = {
            'critical_node_count': len(critical_nodes),
            'max_temp_celsius': max_temp,
            'nodes': json.dumps(critical_nodes),
            'actions_taken': json.dumps(actions)[:1000],
            'timestamp': datetime.utcnow().isoformat()
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

# Note: The Supabase table schema is maintained in database/supabase_schema.sql


