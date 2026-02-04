# Database operations for Claude Code hooks event queue
# Handles SQLite storage, retrieval, and status tracking for hook events

import aiosqlite
import json
from typing import Dict, Any, Tuple, Optional, List
from config import config
from utils.constants import EventStatus, DateTimeConstants
from app.types import SessionRow

# Global variable to track server start time
_server_start_time: Optional[str] = None

from utils.colored_logger import setup_logger  # noqa: E402

logger = setup_logger(__name__)


# Server start time management
async def set_server_start_time(start_time: str) -> None:
    """Set the server start time for filtering events."""
    global _server_start_time
    _server_start_time = start_time
    logger.info(f"Server start time set to: {start_time}")


def get_server_start_time() -> Optional[str]:
    """Get the current server start time."""
    return _server_start_time


# Database initialization
async def init_db() -> None:
    """Initialize the events database using migration system."""
    from app.migrations import run_migrations

    await run_migrations()
    logger.debug("Database initialized")


# Event storage functions
async def queue_event(
    session_id: str,
    hook_event_name: str,
    event_data: Dict[Any, Any],
    instance_id: Optional[str] = None,
) -> int:
    """
    Queue an event for processing by storing it in the database.
    Returns the event ID.

    Args:
        session_id: Claude session ID
        hook_event_name: Name of the hook event
        event_data: Event payload data
        instance_id: Optional instance identifier in "claude_pid:server_port" format
    """
    async with aiosqlite.connect(config.db_path) as db:
        cursor = await db.execute(
            "INSERT INTO events (session_id, hook_event_name, payload, instance_id) VALUES (?, ?, ?, ?)",
            (
                session_id,
                hook_event_name,
                json.dumps(event_data),
                instance_id,
            ),
        )
        await db.commit()
        event_id = cursor.lastrowid
        logger.debug(
            f"Event queued with ID {event_id}: {hook_event_name} for session {session_id}"
            + (f" (instance: {instance_id})" if instance_id else "")
        )
        return event_id or 0


# Event status and monitoring functions
async def get_next_pending_event() -> Optional[Tuple[int, str, str, str, int]]:
    """
    Get the next pending event from the queue.
    Only returns events created at or after server start time.
    Returns tuple of (event_id, session_id, hook_event_name, payload, retry_count) or None.

    Event isolation is handled by checking session ownership in the event processor
    (via server_port filter), not during database query.
    """

    async with aiosqlite.connect(config.db_path) as db:
        server_start = get_server_start_time()

        # Require server start time for temporal filtering
        if not server_start:
            error_msg = "Server start time not set - cannot process events without temporal filtering"
            logger.critical(error_msg)
            raise RuntimeError(error_msg)

        # Process ALL events created at or after server start time
        # Event filtering by session ownership happens in event processor
        cursor = await db.execute(
            "SELECT id, session_id, hook_event_name, payload, retry_count FROM events WHERE status = ? AND created_at >= ? ORDER BY id LIMIT 1",
            (EventStatus.PENDING.value, server_start),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return (row[0], row[1], row[2], row[3], row[4])  # type: ignore[return-value]


async def mark_event_processing(event_id: int) -> None:
    """Mark an event as currently being processed."""
    async with aiosqlite.connect(config.db_path) as db:
        await db.execute(
            "UPDATE events SET status = ? WHERE id = ?",
            (EventStatus.PROCESSING.value, event_id),
        )
        await db.commit()


async def mark_event_completed(event_id: int, retry_count: int) -> None:
    """Mark an event as successfully completed."""
    from datetime import datetime, timezone

    async with aiosqlite.connect(config.db_path) as db:
        await db.execute(
            "UPDATE events SET status = ?, processed_at = ?, retry_count = ? WHERE id = ?",
            (
                EventStatus.COMPLETED.value,
                datetime.now(timezone.utc).strftime(
                    DateTimeConstants.ISO_DATETIME_FORMAT
                ),
                retry_count,
                event_id,
            ),
        )
        await db.commit()


async def mark_event_pending(event_id: int, retry_count: int) -> None:
    """Reset an event back to pending status for later retry.

    Used when an event was picked up but can't be processed yet
    (e.g., session not found yet, or belongs to a different server).
    """
    async with aiosqlite.connect(config.db_path) as db:
        await db.execute(
            "UPDATE events SET status = ?, retry_count = ? WHERE id = ?",
            (EventStatus.PENDING.value, retry_count, event_id),
        )
        await db.commit()


async def mark_event_failed(
    event_id: int, retry_count: int, error_message: str
) -> None:
    """Mark an event as failed after max retries."""
    from datetime import datetime, timezone

    async with aiosqlite.connect(config.db_path) as db:
        await db.execute(
            "UPDATE events SET status = ?, error_message = ?, retry_count = ?, processed_at = ? WHERE id = ?",
            (
                EventStatus.FAILED.value,
                error_message,
                retry_count,
                datetime.now(timezone.utc).strftime(
                    DateTimeConstants.ISO_DATETIME_FORMAT
                ),
                event_id,
            ),
        )
        await db.commit()


async def query_events(
    hook_event_name: Optional[str] = None,
    session_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Query events with optional filters.

    Args:
        hook_event_name: Filter by hook event name (e.g., "SessionEnd")
        session_id: Filter by session ID
        status: Filter by status (e.g., "completed", "failed", "pending")
        limit: Maximum number of results to return

    Returns:
        List of event dictionaries
    """
    async with aiosqlite.connect(config.db_path) as db:
        db.row_factory = aiosqlite.Row

        # Build query dynamically based on filters
        query = "SELECT id, session_id, hook_event_name, status, created_at, processed_at, error_message FROM events WHERE 1=1"
        params: list[str | int] = []

        if hook_event_name:
            query += " AND hook_event_name = ?"
            params.append(hook_event_name)

        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()

        # Convert rows to dictionaries
        events = []
        for row in rows:
            events.append(dict(row))

        return events


# Session management functions (unified sessions table)
async def store_session(
    session_id: str,
    claude_pid: int,
    server_port: int,
    tts_language: Optional[str] = None,
    tts_providers: Optional[str] = None,
    tts_cache_enabled: bool = True,
    elevenlabs_voice_id: Optional[str] = None,
    elevenlabs_model_id: Optional[str] = None,
    silent_announcements: bool = False,
    silent_effects: bool = False,
    openrouter_enabled: bool = False,
    openrouter_model: Optional[str] = None,
    openrouter_contextual_stop: bool = False,
    openrouter_contextual_pretooluse: bool = False,
) -> bool:
    """
    Store session info with settings in unified sessions table.
    Returns True if successful, False otherwise.
    """
    try:
        async with aiosqlite.connect(config.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO sessions
                (session_id, claude_pid, server_port, tts_language, tts_providers, tts_cache_enabled,
                 elevenlabs_voice_id, elevenlabs_model_id, silent_announcements, silent_effects,
                 openrouter_enabled, openrouter_model, openrouter_contextual_stop, openrouter_contextual_pretooluse)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    claude_pid,
                    server_port,
                    tts_language,
                    tts_providers,
                    1 if tts_cache_enabled else 0,
                    elevenlabs_voice_id,
                    elevenlabs_model_id,
                    1 if silent_announcements else 0,
                    1 if silent_effects else 0,
                    1 if openrouter_enabled else 0,
                    openrouter_model,
                    1 if openrouter_contextual_stop else 0,
                    1 if openrouter_contextual_pretooluse else 0,
                ),
            )
            await db.commit()
            logger.info(
                f"Stored session {session_id} for claude_pid {claude_pid} on port {server_port}"
            )
            return True
    except Exception as e:
        logger.error(f"Failed to store session {session_id}: {e}")
        return False


def _parse_session_row(result: Any) -> SessionRow:
    """Parse a database row tuple into a SessionRow TypedDict.

    Args:
        result: Tuple from database query result

    Returns:
        SessionRow TypedDict with parsed session data
    """
    return {
        "session_id": result[0],
        "claude_pid": result[1],
        "server_port": result[2],
        "tts_language": result[3],
        "tts_providers": result[4],
        "tts_cache_enabled": bool(result[5]),
        "elevenlabs_voice_id": result[6],
        "elevenlabs_model_id": result[7],
        "silent_announcements": bool(result[8]),
        "silent_effects": bool(result[9]),
        "openrouter_enabled": bool(result[10]),
        "openrouter_model": result[11],
        "openrouter_contextual_stop": bool(result[12]),
        "openrouter_contextual_pretooluse": bool(result[13]),
        "created_at": result[14],
    }


async def get_session_by_id(session_id: str) -> Optional[SessionRow]:
    """
    Get session by session_id.
    Returns session dict or None if not found.
    """
    try:
        async with aiosqlite.connect(config.db_path) as db:
            cursor = await db.execute(
                """
                SELECT session_id, claude_pid, server_port, tts_language, tts_providers, tts_cache_enabled,
                       elevenlabs_voice_id, elevenlabs_model_id, silent_announcements, silent_effects,
                       openrouter_enabled, openrouter_model, openrouter_contextual_stop, openrouter_contextual_pretooluse,
                       created_at
                FROM sessions
                WHERE session_id = ?
                """,
                (session_id,),
            )
            result = await cursor.fetchone()
            if result:
                return _parse_session_row(result)
            return None
    except Exception as e:
        logger.error(f"Failed to get session {session_id}: {e}")
        return None


async def get_session_by_pid(claude_pid: int) -> Optional[SessionRow]:
    """Get session by claude_pid.

    Returns session dict or None if not found.
    """
    try:
        async with aiosqlite.connect(config.db_path) as db:
            cursor = await db.execute(
                """
                SELECT session_id, claude_pid, server_port, tts_language, tts_providers, tts_cache_enabled,
                       elevenlabs_voice_id, elevenlabs_model_id, silent_announcements, silent_effects,
                       openrouter_enabled, openrouter_model, openrouter_contextual_stop, openrouter_contextual_pretooluse,
                       created_at
                FROM sessions
                WHERE claude_pid = ?
                """,
                (claude_pid,),
            )
            result = await cursor.fetchone()
            if result:
                return _parse_session_row(result)
            return None
    except Exception as e:
        logger.error(f"Failed to get session for PID {claude_pid}: {e}")
        return None


async def get_sessions_by_port(server_port: int) -> list[SessionRow]:
    """Get all sessions for a given server port.

    Returns list of session dicts (may be empty if no sessions found).
    """
    try:
        async with aiosqlite.connect(config.db_path) as db:
            cursor = await db.execute(
                """
                SELECT session_id, claude_pid, server_port, tts_language, tts_providers, tts_cache_enabled,
                       elevenlabs_voice_id, elevenlabs_model_id, silent_announcements, silent_effects,
                       openrouter_enabled, openrouter_model, openrouter_contextual_stop, openrouter_contextual_pretooluse,
                       created_at
                FROM sessions
                WHERE server_port = ?
                """,
                (server_port,),
            )
            results = await cursor.fetchall()
            return [_parse_session_row(row) for row in results]
    except Exception as e:
        logger.error(f"Failed to get sessions for port {server_port}: {e}")
        return []


async def delete_session(session_id: str) -> bool:
    """
    Delete session from database and cleanup related events.
    Returns True if successful, False otherwise.
    """
    try:
        async with aiosqlite.connect(config.db_path) as db:
            # Delete all events for this session
            cursor = await db.execute(
                "DELETE FROM events WHERE session_id = ?", (session_id,)
            )
            events_deleted = cursor.rowcount

            # Delete session record
            await db.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            await db.commit()

            logger.info(
                f"Deleted session {session_id} and cleaned up {events_deleted} event(s)"
            )
            return True
    except Exception as e:
        logger.error(f"Failed to delete session {session_id}: {e}")
        return False


async def delete_session_by_pid(claude_pid: int) -> bool:
    """
    Delete all sessions for a given claude_pid and cleanup related events.
    Returns True if any sessions were deleted, False otherwise.

    Useful for /clear command case where same PID starts new session.
    """
    try:
        async with aiosqlite.connect(config.db_path) as db:
            # First get all session_ids for this PID
            cursor = await db.execute(
                "SELECT session_id FROM sessions WHERE claude_pid = ?", (claude_pid,)
            )
            session_ids = [row[0] for row in await cursor.fetchall()]

            if not session_ids:
                return False

            # Delete events for all these sessions
            placeholders = ",".join(["?" for _ in session_ids])
            query = "DELETE FROM events WHERE session_id IN ({})".format(placeholders)
            events_cursor = await db.execute(query, session_ids)
            events_deleted = events_cursor.rowcount

            # Delete sessions
            sessions_cursor = await db.execute(
                "DELETE FROM sessions WHERE claude_pid = ?", (claude_pid,)
            )
            sessions_deleted = sessions_cursor.rowcount

            await db.commit()

            logger.info(
                f"Deleted {sessions_deleted} session(s) and {events_deleted} event(s) for claude_pid {claude_pid}"
            )
            return True
    except Exception as e:
        logger.error(f"Failed to delete sessions for PID {claude_pid}: {e}")
        return False


async def get_active_session_count(server_port: Optional[int] = None) -> int:
    """
    Get count of active Claude sessions.

    Args:
        server_port: Optional server port to filter sessions.
                    If provided, only counts sessions for that specific server.
                    If None, counts all sessions globally.

    Returns the number of rows in sessions table (optionally filtered by server_port).
    """
    try:
        async with aiosqlite.connect(config.db_path) as db:
            if server_port is not None:
                # Filter by server_port for per-instance count
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM sessions WHERE server_port = ?",
                    (server_port,),
                )
            else:
                # Global count (all servers)
                cursor = await db.execute("SELECT COUNT(*) FROM sessions")

            result = await cursor.fetchone()
            return result[0] if result else 0
    except Exception as e:
        logger.error(f"Failed to get active session count: {e}")
        return 0


def _is_process_running(pid: int) -> bool:
    """Check if a process with given PID exists.

    Delegates to shared utility in utils.process_utils.
    """
    from utils.process_utils import is_process_running

    return is_process_running(pid)


def _is_claude_process(pid: int) -> bool:
    """Check if a process with given PID is a Claude Code process.

    Delegates to shared utility in utils.process_utils.
    IMPORTANT: Returns True (conservative) when unable to determine.
    """
    from utils.process_utils import is_claude_process

    return is_claude_process(pid)


def _get_server_bound_ports() -> Dict[int, int]:
    """
    Get all server.py processes that have bound ports.
    Returns dict mapping server_pid -> bound_port.
    Uses lsof to find processes listening on ports.
    """
    import subprocess

    server_port_map: dict[int, int] = {}
    try:
        # Use lsof to find all listening TCP connections
        # -iTCP -sTCP:LISTEN shows only listening sockets
        # -n avoids DNS lookups, -P avoids port name lookups
        result = subprocess.run(
            ["lsof", "-iTCP", "-sTCP:LISTEN", "-n", "-P"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            logger.debug("lsof command returned non-zero")
            return server_port_map

        # Parse lsof output to find server.py processes
        # Format: COMMAND   PID   USER   FD   TYPE   DEVICE SIZE/OFF NODE NAME
        #         python3  1234  user   3u  IPv4   0x...   0t0     TCP *:12222 (LISTEN)
        for line in result.stdout.split("\n"):
            if "python3" in line and "LISTEN" in line:
                parts = line.split()
                if len(parts) >= 9:
                    try:
                        pid = int(parts[1])
                        # Find port from line more reliably
                        # Look for patterns like "*:12222" or "127.0.0.1:12222"
                        port = None
                        for field in parts:
                            if ":" in field and not field.startswith("0t"):
                                # Extract port from field, removing trailing parens
                                port_str = field.split(":")[-1].rstrip("()")
                                try:
                                    port = int(port_str)
                                    break
                                except ValueError:
                                    continue

                        if not port:
                            continue  # Skip this line if no valid port found

                        # Verify it's actually server.py by checking process with psutil
                        import psutil

                        try:
                            proc = psutil.Process(pid)
                            cmdline = " ".join(proc.cmdline())
                            if "server.py" in cmdline:
                                server_port_map[pid] = port
                                logger.debug(
                                    f"Found server.py PID {pid} bound to port {port}"
                                )
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            # Process no longer exists or we can't access it - skip
                            continue
                    except (ValueError, IndexError) as e:
                        logger.debug(f"Could not parse lsof line: {line} - {e}")
                        continue

        logger.debug(
            f"Found {len(server_port_map)} server.py process(es) with bound ports"
        )

    except FileNotFoundError:
        logger.warning("lsof command not found - port binding check unavailable")
    except Exception as e:
        logger.warning(f"Failed to get server bound ports: {e}")

    return server_port_map


def _get_all_server_processes() -> Dict[int, Tuple[int, int]]:
    """
    Find all server.py processes with their parent PIDs and elapsed time in seconds.
    Returns dict mapping server_pid -> (parent_pid, elapsed_seconds).
    """
    import psutil
    import time

    server_processes = {}
    try:
        # Use psutil to iterate over all processes
        for proc in psutil.process_iter(
            ["pid", "ppid", "name", "cmdline", "create_time"]
        ):
            try:
                # Check if this is a server.py process
                cmdline = proc.info["cmdline"]
                if cmdline and any("server.py" in arg for arg in cmdline):
                    # Also verify it's a Python process
                    name = proc.info["name"].lower()
                    if "python" in name:
                        server_pid = proc.info["pid"]
                        parent_pid = proc.info["ppid"]

                        # Calculate elapsed seconds from create_time
                        elapsed_seconds = int(time.time() - proc.info["create_time"])

                        server_processes[server_pid] = (parent_pid, elapsed_seconds)
                        logger.debug(
                            f"Found server.py PID {server_pid} with parent PID {parent_pid}, "
                            f"age {elapsed_seconds}s"
                        )
            except (psutil.NoSuchProcess, psutil.AccessDenied, KeyError):
                # Process disappeared or we don't have access - skip it
                continue

        logger.debug(f"Found {len(server_processes)} server.py process(es)")

    except Exception as e:
        logger.warning(f"Failed to find server processes: {e}")

    return server_processes


async def cleanup_orphaned_server_processes() -> int:
    """
    Kill orphaned server.py processes that don't have corresponding valid Claude sessions.
    A server is orphaned if:
    1. Its parent Claude process is dead or not a valid Claude process, AND
    2. It's NOT actively bound to a port (meaning it's not a legitimate running server)

    Port binding check prevents killing servers during registration race window.
    Returns count of killed processes.
    """
    import signal

    killed_count = 0
    try:
        # Get all server PIDs with parent PIDs and age
        server_processes = _get_all_server_processes()

        if not server_processes:
            logger.debug("No server processes found")
            return 0

        # Get servers that have successfully bound to ports
        bound_servers = _get_server_bound_ports()
        bound_pids = set(bound_servers.keys())

        logger.debug(f"Found {len(bound_pids)} server(s) with bound ports")

        # Get valid Claude PIDs and server ports from sessions table
        valid_claude_pids = set()
        valid_server_ports = set()
        async with aiosqlite.connect(config.db_path) as db:
            cursor = await db.execute(
                "SELECT DISTINCT claude_pid, server_port FROM sessions"
            )
            sessions = await cursor.fetchall()

            for pid, port in sessions:
                # Only keep if process is running AND is a Claude process
                if _is_process_running(pid) and _is_claude_process(pid):
                    valid_claude_pids.add(pid)
                    valid_server_ports.add(port)

        logger.debug(
            f"Found {len(valid_claude_pids)} valid Claude session(s) with {len(valid_server_ports)} server port(s)"
        )

        # Kill only orphaned servers
        for server_pid, (parent_pid, elapsed_seconds) in server_processes.items():
            # Check if server has bound port
            if server_pid in bound_pids:
                bound_port = bound_servers[server_pid]

                # Server bound to port BUT port not in valid sessions = orphaned!
                if bound_port not in valid_server_ports:
                    logger.info(
                        f"Server PID {server_pid} bound to port {bound_port} but no valid session - marking as orphaned"
                    )
                    # Don't skip - this is an orphaned server!
                else:
                    # Server bound to port AND port in valid sessions = legitimate
                    logger.debug(
                        f"Keeping server PID {server_pid} (bound to port {bound_port} with valid session)"
                    )
                    continue
            else:
                # Server not bound to any port yet - check parent PID
                pass

            # Skip processes younger than 10 seconds (may still be starting up)
            if elapsed_seconds < 10:
                logger.debug(
                    f"Skipping young server PID {server_pid} (age: {elapsed_seconds}s < 10s)"
                )
                continue

            # Check if parent (Claude) process is valid
            is_orphaned = parent_pid not in valid_claude_pids

            if is_orphaned:
                try:
                    import os

                    os.kill(server_pid, signal.SIGTERM)
                    killed_count += 1
                    logger.info(
                        f"Killed orphaned server process: PID {server_pid} "
                        f"(parent Claude PID {parent_pid} invalid/dead, age: {elapsed_seconds}s, no bound port)"
                    )
                except ProcessLookupError:
                    logger.debug(f"Process {server_pid} already terminated")
                except PermissionError:
                    logger.warning(f"No permission to kill process {server_pid}")
                except Exception as e:
                    logger.warning(f"Failed to kill process {server_pid}: {e}")
            else:
                logger.debug(
                    f"Keeping server PID {server_pid} (parent Claude PID {parent_pid} is valid, age: {elapsed_seconds}s)"
                )

        if killed_count > 0:
            logger.info(f"Killed {killed_count} orphaned server process(es)")
        else:
            logger.debug("No orphaned server processes to kill")

    except Exception as e:
        logger.error(f"Failed to cleanup orphaned server processes: {e}")

    return killed_count


async def get_last_event_status_for_instance(instance_id: str) -> Optional[str]:
    """
    Get status of the last (most recent) event for a specific instance.
    Returns the status of the last event or None if no events found.
    """
    async with aiosqlite.connect(config.db_path) as db:
        cursor = await db.execute(
            "SELECT status FROM events WHERE instance_id = ? ORDER BY id DESC LIMIT 1",
            (instance_id,),
        )
        result = await cursor.fetchone()
        return result[0] if result else None


async def cleanup_orphaned_sessions(exclude_sessions: list[str] | None = None) -> int:
    """
    Remove sessions for PIDs that no longer exist or are not Claude processes.
    Also cleans up related events.

    Args:
        exclude_sessions: List of session IDs to exclude from cleanup (e.g., for /clear)

    Returns count of cleaned up sessions.
    """
    cleaned_count = 0
    events_deleted = 0
    exclude_sessions = exclude_sessions or []

    try:
        async with aiosqlite.connect(config.db_path) as db:
            cursor = await db.execute("SELECT session_id, claude_pid FROM sessions")
            sessions = await cursor.fetchall()

            sessions_to_delete = []
            for session_id, pid in sessions:
                # Skip excluded sessions (e.g., /clear sessions we want to keep)
                if session_id in exclude_sessions:
                    logger.debug(f"Skipping cleanup for excluded session {session_id}")
                    continue

                should_delete = False

                if not _is_process_running(pid):
                    logger.info(
                        f"Cleaning orphaned session {session_id}: PID {pid} not running"
                    )
                    should_delete = True
                elif not _is_claude_process(pid):
                    logger.info(
                        f"Cleaning orphaned session {session_id}: PID {pid} is not a Claude process"
                    )
                    should_delete = True

                if should_delete:
                    sessions_to_delete.append(session_id)

            if sessions_to_delete:
                # Delete events for orphaned sessions
                placeholders = ",".join("?" * len(sessions_to_delete))
                events_cursor = await db.execute(
                    f"DELETE FROM events WHERE session_id IN ({placeholders})",
                    sessions_to_delete,
                )
                events_deleted = events_cursor.rowcount

                # Delete orphaned sessions
                sessions_cursor = await db.execute(
                    f"DELETE FROM sessions WHERE session_id IN ({placeholders})",
                    sessions_to_delete,
                )
                cleaned_count = sessions_cursor.rowcount

                await db.commit()
                logger.info(
                    f"Cleaned up {cleaned_count} orphaned session(s) and {events_deleted} event(s)"
                )
            else:
                logger.debug("No orphaned sessions to clean up")

    except Exception as e:
        logger.error(f"Failed to cleanup orphaned sessions: {e}")

    return cleaned_count
