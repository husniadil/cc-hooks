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
from contextlib import asynccontextmanager
from app.api import create_app
from app.event_db import init_db
from app.event_processor import process_events
from app.config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    """Manage application lifecycle for startup and shutdown."""
    # Startup
    await init_db()
    task = asyncio.create_task(process_events())
    logger.info("Server started successfully")
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
    uvicorn.run(app, host=config.host, port=config.port)
