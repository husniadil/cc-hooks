#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "uvicorn",
#     "fastapi",
#     "aiosqlite",
#     "pydantic",
#     "python-dotenv",
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
from app.config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    """Manage application lifecycle for startup and shutdown."""
    # Startup
    server_start_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    await init_db()
    await set_server_start_time(server_start_time)
    task = asyncio.create_task(process_events())
    logger.info(f"Server started successfully at {server_start_time}")
    yield
    # Shutdown
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
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
