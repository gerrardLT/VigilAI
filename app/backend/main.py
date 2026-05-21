"""
Application entry point for VigilAI.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
import logging
import os
import signal
import sys

import uvicorn

try:
    from settings import settings
except Exception as exc:
    print(f"Configuration validation failed: {exc}")
    sys.exit(1)

from agent_platform.artifact_service import ArtifactService
from agent_platform.conversation_engine import ConversationEngine
from agent_platform.memory_service import MemoryService
from agent_platform.reflection_service import ReflectionService
from agent_platform.repository import AgentPlatformRepository
from agent_platform.tool_router import ToolRouter, build_default_registry
from api import app
from config import APP_SCHEDULER_ENABLED, DATA_DIR, LOG_FORMAT
from data_manager import DataManager
from reward_opportunity.repository import RewardOpportunityRepository
from reward_opportunity.service import RewardOpportunityService
from scheduler import TaskScheduler

os.makedirs(DATA_DIR, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"{DATA_DIR}/vigilai.log", encoding="utf-8"),
    ],
)

logger = logging.getLogger(__name__)


class VigilAI:
    """Top-level application lifecycle manager."""

    def __init__(self) -> None:
        self.data_manager: DataManager | None = None
        self.scheduler: TaskScheduler | None = None
        self._shutdown_event = asyncio.Event()

    async def startup(self) -> None:
        logger.info("=" * 50)
        logger.info("VigilAI startup")
        logger.info("=" * 50)
        logger.info("Starting at %s", datetime.now().isoformat())

        logger.info("Initializing DataManager...")
        self.data_manager = DataManager()

        logger.info("Initializing TaskScheduler...")
        self.scheduler = TaskScheduler(self.data_manager)

        app.state.data_manager = self.data_manager
        app.state.scheduler = self.scheduler
        app.state.agent_platform_repository = AgentPlatformRepository(self.data_manager.db_path)
        app.state.agent_tool_router = ToolRouter(
            tool_registry=build_default_registry(data_manager=self.data_manager),
            registry_key=self.data_manager.db_path,
        )
        app.state.agent_conversation_engine = ConversationEngine(app.state.agent_tool_router)
        app.state.agent_artifact_service = ArtifactService(app.state.agent_platform_repository)
        app.state.agent_memory_service = MemoryService(app.state.agent_platform_repository)
        app.state.agent_reflection_service = ReflectionService(app.state.agent_platform_repository)
        app.state.reward_opportunity_repository = RewardOpportunityRepository(self.data_manager.db_path)
        app.state.reward_opportunity_service = RewardOpportunityService(app.state.reward_opportunity_repository)
        self.scheduler.reward_opportunity_service = app.state.reward_opportunity_service

        if APP_SCHEDULER_ENABLED:
            logger.info("Starting scheduler...")
            self.scheduler.start()
            logger.info("Scheduler enabled via APP_SCHEDULER_ENABLED=true")
        else:
            logger.info("Scheduler disabled via APP_SCHEDULER_ENABLED=false - manual refresh only")

        logger.info("VigilAI started successfully")
        logger.info("API available at http://%s:%s", settings.api_host, settings.api_port)

    async def _initial_refresh(self) -> None:
        try:
            await asyncio.sleep(2)
            if self.scheduler is not None:
                await self.scheduler.refresh_all()
        except Exception as exc:
            logger.error("Initial refresh failed: %s", exc)

    async def shutdown(self) -> None:
        logger.info("Shutting down VigilAI...")
        if self.scheduler is not None:
            self.scheduler.stop()
        logger.info("VigilAI shutdown complete")

    def handle_signal(self, sig: signal.Signals) -> None:
        logger.info("Received signal %s, initiating shutdown...", sig)
        self._shutdown_event.set()


async def main() -> None:
    vigilai = VigilAI()

    if sys.platform != "win32":
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda s=sig: vigilai.handle_signal(s))

    try:
        await vigilai.startup()

        config = uvicorn.Config(
            app,
            host=settings.api_host,
            port=settings.api_port,
            log_level="info",
            access_log=True,
        )
        server = uvicorn.Server(config)
        await server.serve()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as exc:
        logger.error("Application error: %s", exc)
        raise
    finally:
        await vigilai.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nVigilAI stopped by user")
    except Exception as exc:
        print(f"Fatal error: {exc}")
        sys.exit(1)
