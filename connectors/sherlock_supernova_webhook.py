#!/usr/bin/env python3
"""
connectors/sherlock_supernova_webhook.py
GlacierEQ APEX Stack | APEX Ring -3
Author: Casey Barton

Wires SHERLOCK-SUPERNOVA anomaly detection to Supabase real-time webhooks.
Standalone pipeline -- no actuation, no Ring 0 side effects.
Observes, detects, and logs only. Physics gate is downstream.

Supabase project: GlacierEQ/mastermind
  READ:  colossus_thermal_events  (real-time subscription)
  WRITE: colossus_anomalies       (confirmed anomalies)

Deploy:
  python connectors/sherlock_supernova_webhook.py
  python connectors/sherlock_supernova_webhook.py --schema
"""

from __future__ import annotations
import logging
import os
import time
from datetime import datetime
from typing import Optional

import numpy as np
from sklearn.ensemble import IsolationForest

logger = logging.getLogger("SHERLOCK-SUPERNOVA")
logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] [%(name)s] %(levelname)s -- %(message)s"
)


def get_supabase_client():
    from supabase import create_client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise EnvironmentError(
            "Set SUPABASE_URL and SUPABASE_SERVICE_KEY env vars.\n"
            "Project: GlacierEQ/mastermind"
        )
    return create_client(url, key)


class SherlockSupernovaDetector:
    """
    Ring -3 anomaly hunter.
    IsolationForest primary + z-score statistical fallback.
    """

    SEVERITY_THRESHOLDS = {
        "CRITICAL": 5.0,
        "HIGH": 3.5,
        "MEDIUM": 2.5,
        "LOW": 1.5,
    }

    def __init__(self, contamination: float = 0.05, window_size: int = 100):
        self.contamination = contamination
        self.window_size = window_size
        self.model: Optional[IsolationForest] = None
        self.baseline_window: list = []
        self.trained = False

    def ingest(self, temp: float) -> None:
        self.baseline_window.append(temp)
        if len(self.baseline_window) > self.window_size:
            self.baseline_window.pop(0)

    def train(self) -> bool:
        if len(self.baseline_window) < 20:
            return False
        X = np.array(self.baseline_window).reshape(-1, 1)
        self.model = IsolationForest(
            contamination=self.contamination, random_state=42, n_estimators=100
        )
        self.model.fit(X)
        self.trained = True
        logger.info(f"IsolationForest trained on {len(self.baseline_window)} samples.")
        return True

    def detect(self, temp: float, node_id: str) -> Optional[dict]:
        baseline = (
            float(np.mean(self.baseline_window)) if self.baseline_window else temp
        )
        std = (
            float(np.std(self.baseline_window))
            if len(self.baseline_window) > 1
            else 0.0
        )
        deviation = abs(temp - baseline)
        z_score = deviation / std if std > 0 else 0.0

        severity = None
        for level in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            if z_score >= self.SEVERITY_THRESHOLDS[level]:
                severity = level
                break

        if_anomaly = False
        if self.trained and self.model:
            if_anomaly = self.model.predict([[temp]])[0] == -1

        if severity or if_anomaly:
            return {
                "node_id": node_id,
                "temp_celsius": temp,
                "baseline_celsius": round(baseline, 2),
                "deviation_celsius": round(deviation, 2),
                "z_score": round(z_score, 3),
                "severity": severity or "LOW",
                "isolation_forest_flag": if_anomaly,
                "root_cause_hypothesis": self._hypothesize(
                    temp, baseline, deviation, z_score
                ),
                "agent": "SHERLOCK-SUPERNOVA",
                "ring": -3,
                "timestamp": datetime.utcnow().isoformat(),
            }
        return None

    def _hypothesize(self, temp, baseline, deviation, z_score) -> str:
        if z_score > 5.0:
            return "CRITICAL thermal runaway -- immediate rack inspection required"
        if temp > baseline + 15:
            return (
                "Rack hotspot -- thermal gradient drift, possible rear airflow blockage"
            )
        if temp > baseline + 8:
            return (
                "Elevated thermal load -- check CDU supply valve position and flow rate"
            )
        if temp < baseline - 8:
            return "Overcooling anomaly -- possible valve stuck open or sensor drift"
        if deviation > 5:
            return (
                "Thermal oscillation -- possible pump bearing micro-vibration signature"
            )
        return "Statistical anomaly -- monitor for trend development"


class SherlockWebhookPipeline:
    """
    Subscribes to colossus_thermal_events via Supabase real-time.
    Every INSERT -> SherlockSupernovaDetector -> persist to colossus_anomalies.
    Observe only. No actuation.
    """

    def __init__(self):
        self.client = get_supabase_client()
        self.detector = SherlockSupernovaDetector()
        self.anomaly_count = 0
        logger.info("SherlockWebhookPipeline initialized -- GlacierEQ/mastermind")

    def _on_thermal_event(self, payload: dict) -> None:
        try:
            record = payload.get("record") or payload.get("new") or {}
            node_id = record.get("node_id", "unknown")
            temp = float(record.get("temp_celsius", 0))
            self.detector.ingest(temp)
            if len(self.detector.baseline_window) % 50 == 0:
                self.detector.train()
            anomaly = self.detector.detect(temp, node_id)
            if anomaly:
                self.anomaly_count += 1
                logger.warning(
                    f"[SHERLOCK] ANOMALY #{self.anomaly_count} -- "
                    f"{node_id} @ {temp}C | {anomaly['severity']} | "
                    f"{anomaly['root_cause_hypothesis']}"
                )
                self._persist_anomaly(anomaly)
            else:
                logger.debug(f"[SHERLOCK] Clean: {node_id} @ {temp:.2f}C")
        except Exception as e:
            logger.error(f"[SHERLOCK] Event processing error: {e}")

    def _persist_anomaly(self, anomaly: dict) -> None:
        try:
            self.client.table("colossus_anomalies").insert(
                {
                    "node_id": anomaly["node_id"],
                    "deviation_celsius": anomaly["deviation_celsius"],
                    "baseline_celsius": anomaly["baseline_celsius"],
                    "severity": anomaly["severity"],
                    "root_cause": anomaly["root_cause_hypothesis"],
                    "z_score": anomaly["z_score"],
                    "agent": "SHERLOCK-SUPERNOVA",
                    "timestamp": anomaly["timestamp"],
                }
            ).execute()
            logger.info(f"[SHERLOCK] Anomaly persisted: {anomaly['node_id']}")
        except Exception as e:
            logger.error(f"[SHERLOCK] Supabase persist failed: {e}")

    def subscribe(self) -> None:
        logger.info("[SHERLOCK] Subscribing to colossus_thermal_events...")
        try:
            (
                self.client.channel("sherlock-thermal-watch")
                .on(
                    "postgres_changes",
                    event="INSERT",
                    schema="public",
                    table="colossus_thermal_events",
                    callback=self._on_thermal_event,
                )
                .subscribe()
            )
            logger.info(
                "[SHERLOCK] Real-time subscription ACTIVE. Hunting anomalies..."
            )
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("[SHERLOCK] Pipeline stopped.")
        except Exception as e:
            logger.error(f"[SHERLOCK] Subscription error: {e}")


SUPABASE_SCHEMA_EXTENSION = """
-- GlacierEQ/mastermind -- Run in Supabase SQL editor
ALTER TABLE colossus_anomalies
  ADD COLUMN IF NOT EXISTS root_cause  TEXT,
  ADD COLUMN IF NOT EXISTS z_score     NUMERIC(8,4),
  ADD COLUMN IF NOT EXISTS agent       TEXT DEFAULT 'SHERLOCK-SUPERNOVA';

CREATE INDEX IF NOT EXISTS idx_anomalies_agent
  ON colossus_anomalies(agent, severity, timestamp DESC);
"""


if __name__ == "__main__":
    import sys

    if "--schema" in sys.argv:
        print(SUPABASE_SCHEMA_EXTENSION)
        sys.exit(0)
    pipeline = SherlockWebhookPipeline()
    pipeline.subscribe()
