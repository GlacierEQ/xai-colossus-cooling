# Omega (How) — Controllers | Alpha (What) — Pure Physics | 1337.
"""
main.py — xAI Colossus Cooling APEX Swarm Entrypoint
=====================================================
Wires together all agents:
  - WaterManagementController  (Phase 2)
  - GPUClusterAgent            (Phase 4)
  - GrokPreCoolingEngine       (AI integration)
  - M2A Swarm Router           (pillar routing)
  - Telemetry pipeline         (Kafka + InfluxDB)

Usage:
  python main.py
  python main.py --dry-run      # no external connections
  python main.py --zone zone-01 # single zone
"""
import asyncio, logging, os, argparse, signal
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S"
)
logger = logging.getLogger("colossus.main")

# ── Environment ──────────────────────────────────────────────
GROK_API_KEY       = os.getenv("GROK_API_KEY", "")
GROK_WS_URL        = os.getenv("GROK_WS_URL", "wss://api.x.ai/v1/realtime")
KAFKA_BOOTSTRAP    = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
INFLUX_URL         = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN       = os.getenv("INFLUX_TOKEN", "")
INFLUX_ORG         = os.getenv("INFLUX_ORG", "glaciereq")
INFLUX_BUCKET      = os.getenv("INFLUX_BUCKET", "colossus")
GPU_MODEL          = os.getenv("GPU_MODEL", "H200")


class ColossusOrchestrator:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self._agents = []
        self._shutdown = asyncio.Event()

    async def initialize(self):
        logger.info("=" * 60)
        logger.info(" xAI COLOSSUS v2 — APEX SWARM FABRIC STARTING")
        logger.info(f" Time: {datetime.now(timezone.utc).isoformat()}")
        logger.info(f" Mode: {'DRY-RUN' if self.dry_run else 'LIVE'}")
        logger.info("=" * 60)

        # Lazy imports to allow dry-run without all deps
        from connectors.gpu_cluster_agent.agent import GPUClusterAgent
        from connectors.water_management.controller import WaterManagementController
        from connectors.water_management.grok_precooling import GrokPreCoolingEngine

        kafka_cb = self._kafka_emit if not self.dry_run else self._noop
        influx   = None if self.dry_run else await self._make_influx()

        # Grok pre-cooling
        self.precooling = GrokPreCoolingEngine(
            api_key=GROK_API_KEY, ws_url=GROK_WS_URL
        )

        # Water management
        self.water_ctrl = WaterManagementController(
            kafka_callback=kafka_cb,
            influx_sink=influx,
            precooling_engine=self.precooling
        )

        # GPU cluster
        self.gpu_agent = GPUClusterAgent(
            kafka_callback=kafka_cb,
            influx_sink=influx,
            precooling_engine=self.precooling,
            gpu_model=GPU_MODEL
        )
        await self.gpu_agent.initialize()

        logger.info("[Main] All agents initialized")

    async def run(self):
        await self.initialize()
        tasks = [
            asyncio.create_task(self.water_ctrl.start(), name="water"),
            asyncio.create_task(self.gpu_agent.start(), name="gpu"),
            asyncio.create_task(self._health_loop(), name="health"),
            asyncio.create_task(self._shutdown_waiter(), name="shutdown"),
        ]
        logger.info("[Main] 🚀 All systems operational")
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for t in pending:
            t.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        logger.info("[Main] Shutdown complete")

    async def _health_loop(self):
        while not self._shutdown.is_set():
            await asyncio.sleep(60)
            water_status = self.water_ctrl.status()
            logger.info(f"[Health] Water={water_status['active_source']} "
                        f"GPU_snapshots={self.gpu_agent.stats().get('snapshots_published', 0)}")

    async def _shutdown_waiter(self):
        await self._shutdown.wait()

    def request_shutdown(self):
        logger.info("[Main] Shutdown requested")
        self._shutdown.set()

    async def _kafka_emit(self, topic: str, payload: dict):
        logger.debug(f"[Kafka] -> {topic}: {list(payload.keys())}")

    async def _noop(self, *args, **kwargs): pass

    async def _make_influx(self):
        """Returns None stub — replace with real InfluxDB client."""
        return None


def parse_args():
    p = argparse.ArgumentParser(description="xAI Colossus Cooling Orchestrator")
    p.add_argument("--dry-run", action="store_true", help="No external connections")
    p.add_argument("--zone", default=None, help="Limit to single zone")
    p.add_argument("--gpu-model", default="H200", choices=["H200", "GB200", "B200"])
    return p.parse_args()


async def main():
    args = parse_args()
    orchestrator = ColossusOrchestrator(dry_run=args.dry_run)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, orchestrator.request_shutdown)

    await orchestrator.run()


if __name__ == "__main__":
    asyncio.run(main())
