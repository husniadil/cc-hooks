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

# Main server entry point for Claude Code hooks processing system
# Manages FastAPI server lifecycle and event processing

import uvicorn
import asyncio
import os
import sys
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from app.api import create_app
from app.event_db import init_db, set_server_start_time
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

# Setup file logging if LOG_FILE environment variable is provided
log_file = os.getenv("LOG_FILE")
if log_file:
    # Extract claude_pid from log file name (format: logs/<claude_pid>.log)
    import re

    match = re.search(r"/(\d+)\.log$", log_file)
    if match:
        claude_pid = int(match.group(1))
        log_dir = os.path.dirname(log_file)
        setup_file_logging(claude_pid, log_dir)
        logger.debug(f"Server file logging configured: {log_file}")


@asynccontextmanager
async def lifespan(app):
    """Manage application lifecycle for startup and shutdown."""
    # Startup
    server_start_time = datetime.now(timezone.utc).strftime(
        DateTimeConstants.ISO_DATETIME_FORMAT
    )
    await init_db()
    await set_server_start_time(server_start_time)

    # Get server port from environment variable
    server_port = int(os.getenv("PORT", str(NetworkConstants.DEFAULT_PORT)))

    # Initialize TTS system
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

    # Log process information for debugging
    import psutil

    current_pid = os.getpid()
    current_process = psutil.Process(current_pid)
    parent_process = current_process.parent()

    logger.info(
        f"Server process info: PID={current_pid}, name={current_process.name()}"
    )
    if parent_process:
        logger.info(
            f"Parent process: PID={parent_process.pid}, name={parent_process.name()}, cmdline={' '.join(parent_process.cmdline()[:3])}"
        )

    # Start background tasks
    # 1. Event processor - processes queued events for this server's sessions
    # 2. PID monitor - checks if Claude process is alive, shutdown if gone
    event_processor_task = asyncio.create_task(process_events(server_port=server_port))
    pid_monitor_task = asyncio.create_task(monitor_claude_pid(server_port=server_port))
    logger.info(f"Server started successfully at {server_start_time}")
    yield
    # Shutdown
    event_processor_task.cancel()
    pid_monitor_task.cancel()
    try:
        await event_processor_task
    except asyncio.CancelledError:
        pass
    try:
        await pid_monitor_task
    except asyncio.CancelledError:
        pass

    # Cleanup TTS system
    if tts_manager:
        tts_manager.cleanup()
        logger.info("TTS system cleaned up")

    logger.info("Server shutdown complete")


app = create_app(lifespan=lifespan)

if __name__ == "__main__":
    try:
        # Check if we're in development mode (with --reload flag or specific argument)
        reload = "--reload" in sys.argv or "--dev" in sys.argv

        # Get port from environment variable (set by claude.sh) or default
        port = int(os.getenv("PORT", str(NetworkConstants.DEFAULT_PORT)))
        host = NetworkConstants.DEFAULT_HOST

        if reload:
            # Development mode with hot reload
            uvicorn.run(
                "server:app",  # Use string import for reload to work
                host=host,
                port=port,
                reload=True,
                reload_dirs=[".", "app", "utils"],  # Watch these directories
                reload_excludes=["*.db", "sound"],  # Ignore these
            )
        else:
            # Production mode without reload
            uvicorn.run(app, host=host, port=port, log_level="info")

    except KeyboardInterrupt:
        logger.info("Server stopped by user (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server failed to start: {e}", exc_info=True)
        sys.exit(1)
