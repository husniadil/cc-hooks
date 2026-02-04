#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "uvicorn>=0.37.0,<0.38",
#     "fastapi>=0.118.0,<0.119",
#     "aiosqlite>=0.21.0,<0.22",
#     "pydantic>=2.11.10,<3",
#     "python-dotenv>=1.1.1,<2",
#     "gtts>=2.5.4,<3",
#     "elevenlabs>=2.16.0,<3",
#     "httpx>=0.28.0,<1",
#     "pygame>=2.6.1,<3",
#     "openai>=2.1.0,<3",
#     "requests>=2.32.5,<3",
#     "psutil>=6.1.1,<7",
# ]
# ///

import uvicorn
import asyncio
import os
import re
import sys
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from app.api import create_app
from app.event_db import init_db, set_server_start_time, close_persistent_db
from app.event_processor import process_events, monitor_claude_pid
from config import config
from utils.tts_announcer import initialize_tts
from utils.colored_logger import (
    setup_logger,
    configure_root_logging,
    setup_file_logging,
)
from utils.constants import DateTimeConstants, NetworkConstants

configure_root_logging()
logger = setup_logger(__name__)

if (log_file := os.getenv("LOG_FILE")) and (
    match := re.search(r"/(\d+)\.log$", log_file)
):
    setup_file_logging(int(match.group(1)), os.path.dirname(log_file))
    logger.debug(f"Server file logging configured: {log_file}")


@asynccontextmanager
async def lifespan(app):
    """Manage application lifecycle for startup and shutdown."""
    import psutil

    server_start_time = datetime.now(timezone.utc).strftime(
        DateTimeConstants.ISO_DATETIME_FORMAT
    )
    await init_db()
    await set_server_start_time(server_start_time)

    server_port = int(os.getenv("PORT", str(NetworkConstants.DEFAULT_PORT)))

    providers = config.get_tts_providers_list()
    tts_manager = initialize_tts(
        providers=providers,
        language=config.tts_language,
        cache_enabled=config.tts_cache_enabled,
        api_key=config.elevenlabs_api_key,
        voice_id=config.elevenlabs_voice_id,
        model_id=config.elevenlabs_model_id,
    )
    if tts_manager:
        logger.debug(f"TTS system initialized with providers: {providers}")
    else:
        logger.warning("TTS system initialization failed, continuing without TTS")

    current_process = psutil.Process(os.getpid())
    logger.info(
        f"Server process info: PID={current_process.pid}, name={current_process.name()}"
    )
    if parent := current_process.parent():
        logger.info(
            f"Parent process: PID={parent.pid}, name={parent.name()}, "
            f"cmdline={' '.join(parent.cmdline()[:3])}"
        )

    event_processor_task = asyncio.create_task(process_events(server_port=server_port))
    pid_monitor_task = asyncio.create_task(monitor_claude_pid(server_port=server_port))
    logger.info(f"Server started successfully at {server_start_time}")
    yield

    event_processor_task.cancel()
    pid_monitor_task.cancel()
    for i, result in enumerate(
        await asyncio.gather(
            event_processor_task, pid_monitor_task, return_exceptions=True
        )
    ):
        if isinstance(result, Exception) and not isinstance(
            result, asyncio.CancelledError
        ):
            logger.warning(f"Background task {i} raised during shutdown: {result}")

    await close_persistent_db()
    if tts_manager:
        tts_manager.cleanup()
    logger.info("Server shutdown complete")


app = create_app(lifespan=lifespan)

if __name__ == "__main__":
    try:
        reload = "--reload" in sys.argv or "--dev" in sys.argv
        port = int(os.getenv("PORT", str(NetworkConstants.DEFAULT_PORT)))
        host = NetworkConstants.DEFAULT_HOST

        if reload:
            uvicorn.run(
                "server:app",
                host=host,
                port=port,
                reload=True,
                reload_dirs=[".", "app", "utils"],
                reload_excludes=["*.db", "sound"],
            )
        else:
            uvicorn.run(app, host=host, port=port, log_level="info")
    except KeyboardInterrupt:
        logger.info("Server stopped by user (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server failed to start: {e}", exc_info=True)
        sys.exit(1)
