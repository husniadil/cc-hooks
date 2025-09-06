# Database operations for Claude Code hooks event queue
# Handles SQLite storage, retrieval, and status tracking for hook events

import aiosqlite
import json
import logging
from typing import Dict, Any, Tuple, Optional
from app.config import config

DB_PATH = config.db_path
RECENT_EVENTS_LIMIT = 10

# Configure logging
logger = logging.getLogger(__name__)


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
) -> int:
    """
    Queue an event for processing by storing it in the database.
    Returns the event ID.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO events (session_id, hook_event_name, payload, arguments) VALUES (?, ?, ?, ?)",
            (
                session_id,
                hook_event_name,
                json.dumps(event_data),
                json.dumps(arguments) if arguments else None,
            ),
        )
        await db.commit()
        event_id = cursor.lastrowid
        logger.info(
            f"Event queued successfully with ID {event_id}: {hook_event_name} for session {session_id}"
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
            SELECT id, session_id, hook_event_name, status, created_at, processed_at, error_message
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
                }
                for row in recent_events
            ],
        }


async def get_next_pending_event() -> (
    Optional[Tuple[int, str, str, str, int, Optional[str]]]
):
    """
    Get the next pending event from the queue.
    Returns tuple of (event_id, session_id, hook_event_name, payload, retry_count, arguments) or None.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id, session_id, hook_event_name, payload, retry_count, arguments FROM events WHERE status = ? ORDER BY id LIMIT 1",
            ("pending",),
        )
        return await cursor.fetchone()


async def mark_event_processing(event_id: int):
    """Mark an event as currently being processed"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE events SET status = ? WHERE id = ?", ("processing", event_id)
        )
        await db.commit()


async def mark_event_completed(event_id: int, retry_count: int):
    """Mark an event as successfully completed"""
    from datetime import datetime

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE events SET status = ?, processed_at = ?, retry_count = ? WHERE id = ?",
            ("completed", datetime.now().isoformat(), retry_count, event_id),
        )
        await db.commit()


async def mark_event_failed(event_id: int, retry_count: int, error_message: str):
    """Mark an event as failed after max retries"""
    from datetime import datetime

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE events SET status = ?, error_message = ?, retry_count = ?, processed_at = ? WHERE id = ?",
            (
                "failed",
                error_message,
                retry_count,
                datetime.now().isoformat(),
                event_id,
            ),
        )
        await db.commit()
