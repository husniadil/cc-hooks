#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "uvicorn",
#     "fastapi",
#     "aiosqlite",
#     "pydantic",
#     "python-dotenv",
#     "gtts",
#     "elevenlabs",
#     "pygame",
# ]
# ///

# Main server entry point for Claude Code hooks processing system
# Manages FastAPI server lifecycle and event processing

import uvicorn
import asyncio
import logging
import sys
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from app.api import create_app
from app.event_db import init_db, set_server_start_time
from app.event_processor import process_events
from config import config
from utils.tts_announcer import initialize_tts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    """Manage application lifecycle for startup and shutdown."""
    # Startup
    server_start_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    await init_db()
    await set_server_start_time(server_start_time)

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
        logger.info(f"TTS system initialized with providers: {providers}")
    else:
        logger.warning("TTS system initialization failed, continuing without TTS")

    task = asyncio.create_task(process_events())
    logger.info(f"Server started successfully at {server_start_time}")
    yield
    # Shutdown
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Cleanup TTS system
    if tts_manager:
        tts_manager.cleanup()
        logger.info("TTS system cleaned up")

    logger.info("Server shutdown complete")


app = create_app(lifespan=lifespan)

if __name__ == "__main__":
    # Check if we're in development mode (with --reload flag or specific argument)
    reload = "--reload" in sys.argv or "--dev" in sys.argv

    if reload:
        # Development mode with hot reload
        uvicorn.run(
            "server:app",  # Use string import for reload to work
            host=config.host,
            port=config.port,
            reload=True,
            reload_dirs=[".", "app", "utils"],  # Watch these directories
            reload_excludes=["*.db", ".claude-instances", "sound"],  # Ignore these
        )
    else:
        # Production mode without reload
        uvicorn.run(app, host=config.host, port=config.port)
