# Database operations for Claude Code hooks event queue
# Handles SQLite storage, retrieval, and status tracking for hook events

import aiosqlite
import json
from typing import Dict, Any, Tuple, Optional, Literal
from config import config

DB_PATH = config.db_path
RECENT_EVENTS_LIMIT = 10

# Event status type definition
EventStatus = Literal["pending", "processing", "completed", "failed"]

# Event status constants
EVENT_STATUS_PENDING: EventStatus = "pending"
EVENT_STATUS_PROCESSING: EventStatus = "processing"
EVENT_STATUS_COMPLETED: EventStatus = "completed"
EVENT_STATUS_FAILED: EventStatus = "failed"

# Global variable to track server start time
_server_start_time: Optional[str] = None

# Configure logging
from utils.colored_logger import setup_logger

logger = setup_logger(__name__)


# Server start time management
async def set_server_start_time(start_time: str):
    """Set the server start time for filtering events"""
    global _server_start_time
    _server_start_time = start_time
    logger.info(f"Server start time set to: {start_time}")


def get_server_start_time() -> Optional[str]:
    """Get the current server start time"""
    return _server_start_time


# Database initialization
async def init_db():
    """Initialize the events database using migration system"""
    from app.migrations import run_migrations

    await run_migrations()
    logger.info("Database initialized")


# Event storage functions
async def queue_event(
    session_id: str,
    hook_event_name: str,
    event_data: Dict[Any, Any],
    arguments: Optional[Dict[str, Any]] = None,
    instance_id: Optional[str] = None,
) -> int:
    """
    Queue an event for processing by storing it in the database.
    Returns the event ID.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO events (session_id, hook_event_name, payload, arguments, instance_id) VALUES (?, ?, ?, ?, ?)",
            (
                session_id,
                hook_event_name,
                json.dumps(event_data),
                json.dumps(arguments) if arguments else None,
                instance_id,
            ),
        )
        await db.commit()
        event_id = cursor.lastrowid
        instance_info = f" (instance: {instance_id})" if instance_id else ""
        logger.info(
            f"Event queued successfully with ID {event_id}: {hook_event_name} for session {session_id}{instance_info}"
        )
        return event_id


# Event status and monitoring functions
async def get_events_status() -> Dict[str, Any]:
    """
    Get current status of events in the queue.
    Returns status summary and recent events.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        # Get status counts
        cursor = await db.execute(
            """
            SELECT status, COUNT(*) as count 
            FROM events 
            GROUP BY status
        """
        )
        status_counts = await cursor.fetchall()

        cursor = await db.execute(  # get latest events
            """
            SELECT id, session_id, hook_event_name, status, created_at, processed_at, error_message, instance_id
            FROM events 
            ORDER BY id DESC 
            LIMIT ?
        """,
            (RECENT_EVENTS_LIMIT,),
        )
        recent_events = await cursor.fetchall()

        return {
            "status_summary": {status: count for status, count in status_counts},
            "recent_events": [
                {
                    "id": row[0],
                    "session_id": row[1],
                    "hook_event_name": row[2],
                    "status": row[3],
                    "created_at": row[4],
                    "processed_at": row[5],
                    "error_message": row[6],
                    "instance_id": row[7],
                }
                for row in recent_events
            ],
        }


async def get_next_pending_event() -> (
    Optional[Tuple[int, str, str, str, int, Optional[str]]]
):
    """
    Get the next pending event from the queue.
    Only returns events created at or after server start time.
    Returns tuple of (event_id, session_id, hook_event_name, payload, retry_count, arguments) or None.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        server_start = get_server_start_time()

        if server_start:
            # Only process events created at or after server start time
            cursor = await db.execute(
                "SELECT id, session_id, hook_event_name, payload, retry_count, arguments FROM events WHERE status = ? AND created_at >= ? ORDER BY id LIMIT 1",
                (EVENT_STATUS_PENDING, server_start),
            )
        else:
            # Fallback to original behavior if start time not set (shouldn't happen in normal operation)
            logger.warning("Server start time not set, processing all pending events")
            cursor = await db.execute(
                "SELECT id, session_id, hook_event_name, payload, retry_count, arguments FROM events WHERE status = ? ORDER BY id LIMIT 1",
                (EVENT_STATUS_PENDING,),
            )
        return await cursor.fetchone()


async def mark_event_processing(event_id: int):
    """Mark an event as currently being processed"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE events SET status = ? WHERE id = ?",
            (EVENT_STATUS_PROCESSING, event_id),
        )
        await db.commit()


async def mark_event_completed(event_id: int, retry_count: int):
    """Mark an event as successfully completed"""
    from datetime import datetime, timezone

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE events SET status = ?, processed_at = ?, retry_count = ? WHERE id = ?",
            (
                EVENT_STATUS_COMPLETED,
                datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                retry_count,
                event_id,
            ),
        )
        await db.commit()


async def mark_event_failed(event_id: int, retry_count: int, error_message: str):
    """Mark an event as failed after max retries"""
    from datetime import datetime, timezone

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE events SET status = ?, error_message = ?, retry_count = ?, processed_at = ? WHERE id = ?",
            (
                EVENT_STATUS_FAILED,
                error_message,
                retry_count,
                datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                event_id,
            ),
        )
        await db.commit()


async def get_last_event_status_for_instance(instance_id: str) -> Optional[EventStatus]:
    """
    Get status of the last (most recent) event for a specific instance.
    Returns the status of the last event or None if no events found.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT status FROM events WHERE instance_id = ? ORDER BY id DESC LIMIT 1",
            (instance_id,),
        )
        result = await cursor.fetchone()
        return result[0] if result else None
