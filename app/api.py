# FastAPI endpoints for Claude Code hooks processing system
# Provides REST API for event submission, status monitoring, and migrations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import os
import signal
from app.event_db import (
    queue_event,
    get_events_status as get_db_events_status,
    get_last_event_status_for_instance,
)
from app.migrations import get_migration_status
from utils.hooks_constants import is_valid_hook_event
from utils.colored_logger import setup_logger, configure_root_logging
from utils.constants import HTTPStatusConstants

configure_root_logging()
logger = setup_logger(__name__)


class Event(BaseModel):
    """Pydantic model for incoming events."""

    data: Dict[Any, Any]
    arguments: Optional[Dict[str, Any]] = None
    instance_id: Optional[str] = None


def create_app(lifespan=None) -> FastAPI:
    """Create FastAPI application with configured endpoints."""
    app = FastAPI(lifespan=lifespan)

    @app.get("/health")
    def health():
        """Health check endpoint."""
        return {"status": "ok"}

    @app.post("/events")
    async def create_event(event: Event):
        """Endpoint to receive JSON events and emit them asynchronously.

        Returns OK immediately after queuing the event for processing.
        """
        try:
            # Extract session_id and hook_event_name from event data
            session_id = event.data.get("session_id")
            hook_event_name = event.data.get("hook_event_name")

            # Reject events with missing required fields
            if not session_id or not hook_event_name:
                raise HTTPException(
                    status_code=HTTPStatusConstants.BAD_REQUEST,
                    detail="Both session_id and hook_event_name are required",
                )

            # Validate hook event name (warning only, still process unknown events)
            if not is_valid_hook_event(hook_event_name):
                logger.warning(
                    f"Unknown hook event received: {hook_event_name} (session: {session_id})"
                )

            # Queue event using database module
            event_id = await queue_event(
                session_id,
                hook_event_name,
                event.data,
                event.arguments,
                event.instance_id,
            )

            return {
                "status": "ok",
                "message": "Event queued for processing",
                "event_id": event_id,
            }

        except Exception as e:
            logger.error(f"Error queuing event: {e}")
            raise HTTPException(
                status_code=HTTPStatusConstants.INTERNAL_SERVER_ERROR,
                detail="Failed to queue event",
            )

    @app.get("/events/status")
    async def get_events_status(instance_id: str):
        """Get current status of events in the queue for a specific instance.

        Requires instance_id query parameter.
        Useful for monitoring and debugging per-instance events.
        """
        try:
            return await get_db_events_status(instance_id)
        except Exception as e:
            logger.error(f"Error getting events status for instance {instance_id}: {e}")
            raise HTTPException(
                status_code=HTTPStatusConstants.INTERNAL_SERVER_ERROR,
                detail="Failed to get events status",
            )

    @app.get("/migrations/status")
    async def get_migrations_status():
        """Get current database migration status.

        Shows applied migrations and pending count.
        """
        try:
            return await get_migration_status()
        except Exception as e:
            logger.error(f"Error getting migration status: {e}")
            raise HTTPException(
                status_code=HTTPStatusConstants.INTERNAL_SERVER_ERROR,
                detail="Failed to get migration status",
            )

    @app.get("/instances/{instance_id}/last-event")
    async def get_instance_last_event_status(instance_id: str):
        """Get status of last event for a specific instance.

        Useful for graceful shutdown logic to wait for the last event to complete.
        Returns the status of the most recent event or null if no events exist.
        """
        try:
            status = await get_last_event_status_for_instance(instance_id)
            has_pending = status in ("pending", "processing") if status else False

            return {
                "instance_id": instance_id,
                "last_event_status": status,
                "has_pending": has_pending,
            }
        except Exception as e:
            logger.error(
                f"Error getting last event status for instance {instance_id}: {e}"
            )
            raise HTTPException(
                status_code=HTTPStatusConstants.INTERNAL_SERVER_ERROR,
                detail="Failed to get last event status for instance",
            )

    @app.post("/shutdown")
    async def shutdown_server():
        """Shutdown the server gracefully.

        Triggers graceful shutdown sequence via SIGTERM signal.
        This allows the lifespan context manager to handle cleanup properly.
        """
        logger.info("Shutdown requested via API endpoint")
        try:
            # Send SIGTERM to current process to trigger graceful shutdown
            # This will be caught by the lifespan context manager
            os.kill(os.getpid(), signal.SIGTERM)

            return {"status": "ok", "message": "Server shutdown initiated"}
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            raise HTTPException(
                status_code=HTTPStatusConstants.INTERNAL_SERVER_ERROR,
                detail="Failed to shutdown server",
            )

    return app
