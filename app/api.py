# FastAPI endpoints for Claude Code hooks processing system
# Provides REST API for event submission, status monitoring, and migrations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging
from typing import Dict, Any, Optional
from app.event_db import queue_event, get_events_status as get_db_events_status
from app.migrations import get_migration_status

logger = logging.getLogger(__name__)


class Event(BaseModel):
    """Pydantic model for incoming events."""
    data: Dict[Any, Any]
    arguments: Optional[Dict[str, Any]] = None


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
                    status_code=400,
                    detail="Both session_id and hook_event_name are required",
                )

            # Queue event using database module
            event_id = await queue_event(session_id, hook_event_name, event.data, event.arguments)

            return {
                "status": "ok",
                "message": "Event queued for processing",
                "event_id": event_id,
            }

        except Exception as e:
            logger.error(f"Error queuing event: {e}")
            raise HTTPException(status_code=500, detail="Failed to queue event")

    @app.get("/events/status")
    async def get_events_status():
        """Get current status of events in the queue.
        
        Useful for monitoring and debugging.
        """
        try:
            return await get_db_events_status()
        except Exception as e:
            logger.error(f"Error getting events status: {e}")
            raise HTTPException(status_code=500, detail="Failed to get events status")

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
                status_code=500, detail="Failed to get migration status"
            )

    return app
