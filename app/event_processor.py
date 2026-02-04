# Background event processor for Claude Code hooks
# Handles asynchronous processing of hook events with retry logic and error handling

import asyncio
import json
import psutil
from typing import Optional, Dict, Any
from pathlib import Path
from config import config
from app.types import EventData
from app.event_db import (
    get_next_pending_event,
    mark_event_pending,
    mark_event_processing,
    mark_event_completed,
    mark_event_failed,
)
from utils.tts_announcer import announce_event
from utils.audio_mappings import should_play_sound_effect, should_play_announcement
from utils.constants import HookEvent, ProcessingConstants
from utils.hooks_constants import is_valid_hook_event

from utils.colored_logger import setup_logger, configure_root_logging

configure_root_logging()
logger = setup_logger(__name__)


async def process_events(server_port: Optional[int] = None) -> None:
    """Background task for processing events.

    Args:
        server_port: Port of this server, used to filter events by session ownership

    Each server only processes events for sessions it owns (by server_port).
    """
    if server_port:
        logger.info(f"Starting event processor for server port {server_port}")
    else:
        logger.info("Starting event processor (processing all events)")

    while True:
        try:
            # Get next pending event using database module
            row = await get_next_pending_event()

            if row:
                (
                    event_id,
                    session_id,
                    hook_event_name,
                    payload,
                    retry_count,
                ) = row

                # Mark as processing FIRST to prevent other processors from picking it up
                await mark_event_processing(event_id)

                # Filter: only process if session belongs to this server
                if server_port:
                    from app.event_db import get_session_by_id

                    session = await get_session_by_id(session_id)

                    if not session:
                        # Session not found - could be temporary (registration delay, DB lock)
                        # Increment retry count and check if we should fail or retry
                        new_retry_count = retry_count + 1

                        logger.debug(
                            f"Session {session_id} not found yet for event {event_id} "
                            f"(attempt {new_retry_count}/{config.max_retry_count}), will retry"
                        )

                        # Only mark as failed if we've exceeded max retries
                        if new_retry_count >= config.max_retry_count:
                            logger.error(
                                f"Session {session_id} not found after {config.max_retry_count} attempts, "
                                f"marking event {event_id} as failed"
                            )
                            await mark_event_failed(
                                event_id,
                                new_retry_count,
                                "Session not found after max retries",
                            )
                        else:
                            # Reset to PENDING with incremented retry count for later retry
                            await mark_event_pending(event_id, new_retry_count)
                            logger.debug(
                                f"Event {event_id} retry count updated to {new_retry_count}, will retry later"
                            )
                        continue

                    if session.get("server_port") != server_port:
                        logger.debug(
                            f"Skipping event {event_id} for session {session_id} "
                            f"(belongs to server port {session.get('server_port')}, we are {server_port})"
                        )
                        # Reset to PENDING so the correct server can process it
                        await mark_event_pending(event_id, retry_count)
                        continue

                logger.debug(
                    f"Processing event {event_id}: {hook_event_name} for session {session_id} (attempt {retry_count + 1}/{config.max_retry_count})"
                )

                # Prepare event data
                event_data = json.loads(payload)
                event_data["session_id"] = session_id
                event_data["hook_event_name"] = hook_event_name

                # Retry loop
                current_retry = retry_count
                success = False
                last_error = None

                while current_retry < config.max_retry_count and not success:
                    try:
                        await process_single_event(event_data)
                        success = True

                        # Mark as completed
                        await mark_event_completed(event_id, current_retry)
                        logger.debug(
                            f"Event {event_id} processed successfully after {current_retry + 1} attempt(s)"
                        )

                    except Exception as e:
                        current_retry += 1
                        last_error = str(e)
                        logger.warning(
                            f"Event {event_id} failed (attempt {current_retry}/{config.max_retry_count}): {e}",
                            exc_info=True,
                        )

                        if current_retry < config.max_retry_count:
                            # Delay before next retry attempt
                            await asyncio.sleep(ProcessingConstants.RETRY_DELAY_SECONDS)

                if not success:
                    # Max retries exceeded, mark as failed
                    logger.error(
                        f"Event {event_id} failed after {config.max_retry_count} attempts. Skipping."
                    )
                    error_message = f"Max retries ({config.max_retry_count}) exceeded. Last error: {last_error}"
                    await mark_event_failed(event_id, current_retry, error_message)
            else:
                # No pending events, wait a bit
                await asyncio.sleep(ProcessingConstants.NO_EVENTS_WAIT_SECONDS)

        except Exception as e:
            logger.error(
                f"Error in event processor main loop: {e}",
                exc_info=True,
                extra={"server_port": server_port},
            )
            await asyncio.sleep(ProcessingConstants.ERROR_WAIT_SECONDS)


# Sound effect processing
async def play_sound(sound_file: str) -> bool:
    """Play sound using the sound player utility (BLOCKING - waits for completion).

    Returns True if sound played successfully, False otherwise.
    """
    try:
        script_dir = Path(__file__).parent.parent  # Go up from app/ to project root
        sound_player_path = script_dir / "utils" / "sound_player.py"

        if not sound_player_path.exists():
            logger.warning(f"Sound player script not found: {sound_player_path}")
            return False

        # Run sound player synchronously (blocking - wait for completion)
        # Set cwd to project root so Python can resolve 'utils' module
        process = await asyncio.create_subprocess_exec(
            "uv",
            "run",
            str(sound_player_path),
            sound_file,
            cwd=script_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Wait for sound playback to complete
        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            logger.debug(f"Sound played successfully: {sound_file}")
            return True
        else:
            logger.warning(
                f"Sound player failed with return code {process.returncode}: {stderr.decode()}"
            )
            return False

    except Exception as e:
        logger.warning(f"Failed to play sound {sound_file}: {e}", exc_info=True)
        return False


# TTS announcement processing
async def play_announcement_sound(
    hook_event_name: str,
    event_data: Dict[str, Any],
    volume: float = 0.5,
    session_settings: Optional[Dict[str, Any]] = None,
) -> bool:
    """Play appropriate announcement sound based on hook event context with session-specific settings.

    Returns True if announcement played successfully, False otherwise.
    """
    try:
        # Use synchronous announce_event in a thread to avoid blocking
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(
            None, announce_event, hook_event_name, event_data, volume, session_settings
        )

        if success:
            logger.debug(f"Announced {hook_event_name} event successfully")
        else:
            logger.warning(f"Failed to announce {hook_event_name} event")

        return success

    except Exception as e:
        logger.warning(
            f"Failed to play announcement for {hook_event_name}: {e}", exc_info=True
        )
        return False


# Your custom event processing logic
async def process_single_event(event_data: EventData) -> None:
    """Process events based on hook_event_name.

    Expected fields: session_id, hook_event_name
    """
    # Validate required fields
    if "session_id" not in event_data:
        raise ValueError("Missing required field: session_id")
    if "hook_event_name" not in event_data:
        raise ValueError("Missing required field: hook_event_name")

    session_id = event_data["session_id"]
    hook_event_name = event_data["hook_event_name"]

    logger.debug(f"Processing {hook_event_name} event for session {session_id}")

    # Prepare audio tasks for parallel execution
    audio_tasks = []

    # Get session settings from DB (includes TTS config, silent modes, etc.)
    session_settings = None
    from app.event_db import get_session_by_id

    session_settings = await get_session_by_id(session_id)

    if not session_settings:
        logger.warning(
            f"Session {session_id} not found in DB, using global config defaults"
        )

    # Check granular silent mode flags (from session DB or fallback to config defaults)
    silent_announcements = (
        session_settings.get("silent_announcements") if session_settings else False
    )
    silent_effects = (
        session_settings.get("silent_effects") if session_settings else False
    )

    # Use audio mappings to determine what to play based on hook event type
    # Audio control is via claude.sh flags (--audio, --silent, etc.)

    # Check if this event should have announcement (pass session_settings for context)
    if should_play_announcement(
        hook_event_name,
        bool(silent_announcements),
        session_settings,  # type: ignore[arg-type]
    ):
        volume = 0.5  # Default volume
        logger.debug(f"Playing announcement for {hook_event_name} (volume: {volume})")
        audio_tasks.append(
            play_announcement_sound(
                hook_event_name,
                dict(event_data),
                volume,
                session_settings,  # type: ignore[arg-type]
            )
        )
    elif silent_announcements:
        logger.debug(
            f"Silent announcements mode - skipping announcement for {hook_event_name}"
        )

    # Check if this event should have sound effect
    sound_file = should_play_sound_effect(hook_event_name, bool(silent_effects))
    if sound_file:
        logger.debug(f"Playing sound effect for {hook_event_name}: {sound_file}")
        audio_tasks.append(play_sound(sound_file))
    elif silent_effects and should_play_sound_effect(hook_event_name, False):
        logger.debug(
            f"Silent effects mode - skipping sound effect for {hook_event_name}"
        )

    # Run all audio tasks in parallel if any exist
    if audio_tasks:
        logger.debug(f"Running {len(audio_tasks)} audio task(s) in parallel")
        audio_results = await asyncio.gather(*audio_tasks, return_exceptions=True)

        # Log results for debugging
        for i, result in enumerate(audio_results):
            if isinstance(result, Exception):
                logger.warning(f"Audio task {i + 1} failed: {result}")
            else:
                logger.debug(f"Audio task {i + 1} completed: {result}")

        # Check if any audio task failed
        failed_tasks = [r for r in audio_results if isinstance(r, Exception)]
        if failed_tasks:
            logger.warning(
                f"{len(failed_tasks)}/{len(audio_tasks)} audio task(s) failed"
            )
        else:
            logger.debug(f"All {len(audio_tasks)} audio task(s) completed successfully")

    # Check if hook event is valid first
    if not is_valid_hook_event(hook_event_name):
        logger.debug(
            f"Skipping unknown hook event: {hook_event_name} (session: {session_id})"
        )
        return  # Still process sound effects/announcements but skip event-specific logic

    # Handle all hook event types using generic handler
    await handle_generic_event(hook_event_name, session_id, event_data)


# Event-specific configurations for special handling
EVENT_CONFIGS = {
    HookEvent.SESSION_START.value: {
        "log_message": "Session {session_id} started",
    },
    HookEvent.SESSION_END.value: {
        "log_message": "Session {session_id} ended",
        "clear_tracking": True,
        "cleanup_old_files": True,
        "cleanup_orphaned": True,
    },
    HookEvent.PRE_TOOL_USE.value: {
        "log_message": "Session {session_id}: Pre-tool use for {tool_name}",
        "use_tool_name": True,
    },
    HookEvent.POST_TOOL_USE.value: {
        "log_message": "Session {session_id}: Post-tool use for {tool_name}",
        "use_tool_name": True,
    },
    HookEvent.NOTIFICATION.value: {
        "log_message": "Session {session_id}: Notification - {message}",
        "use_message": True,
    },
    HookEvent.USER_PROMPT_SUBMIT.value: {
        "log_message": "Session {session_id}: User submitted prompt",
    },
    HookEvent.STOP.value: {
        "log_message": "Session {session_id}: Stop event received",
        "clear_tracking": True,
    },
    HookEvent.SUBAGENT_STOP.value: {
        "log_message": "Session {session_id}: Subagent stopped",
    },
    HookEvent.PRE_COMPACT.value: {
        "log_message": "Session {session_id}: Pre-compact event",
    },
}


async def handle_generic_event(
    hook_event_name: str, session_id: str, event_data: EventData
) -> None:
    """Generic handler for all event types with configurable behavior."""
    event_config: Dict[str, Any] = EVENT_CONFIGS.get(hook_event_name, {})  # type: ignore[assignment]

    # Build log message with dynamic parameters
    log_params = {"session_id": session_id}
    if event_config.get("use_tool_name"):
        log_params["tool_name"] = event_data.get("tool_name") or "unknown"
    if event_config.get("use_message"):
        log_params["message"] = event_data.get("message") or ""

    log_message = event_config.get(
        "log_message", f"Session {session_id}: {hook_event_name} event"
    )
    logger.info(log_message.format(**log_params))

    # Handle special behaviors
    if event_config.get("cleanup_orphaned"):
        try:
            from app.event_db import (
                cleanup_orphaned_server_processes,
                cleanup_orphaned_sessions,
            )

            # For SessionEnd with reason="clear", exclude current session from cleanup
            end_reason = event_data.get("reason")
            exclude_sessions = []
            if end_reason == "clear":
                exclude_sessions = [session_id]
                logger.info(
                    f"SessionEnd with reason 'clear' - excluding session {session_id} from cleanup"
                )

            # Kill orphaned server processes first
            killed_count = await cleanup_orphaned_server_processes()
            # Then cleanup orphaned sessions from DB (excluding current session if /clear)
            cleaned_count = await cleanup_orphaned_sessions(
                exclude_sessions=exclude_sessions
            )

            if killed_count > 0 or cleaned_count > 0:
                logger.info(
                    f"{hook_event_name} cleanup: killed {killed_count} server(s), "
                    f"cleaned {cleaned_count} session(s)"
                )
        except Exception as e:
            logger.warning(f"Failed to cleanup orphaned resources: {e}")

    if event_config.get("clear_tracking"):
        try:
            from utils.transcript_parser import clear_last_processed_message

            clear_last_processed_message(session_id)
            logger.debug(
                f"Cleared last processed message tracking for session {session_id}"
            )
        except Exception as e:
            logger.warning(
                f"Failed to clear last processed message for session {session_id}: {e}"
            )

    if event_config.get("cleanup_old_files"):
        try:
            from utils.transcript_parser import cleanup_old_processed_files

            cleanup_old_processed_files(max_age_hours=24)
            logger.debug("Cleaned up expired processed files")
        except Exception as e:
            logger.warning(f"Failed to cleanup expired processed files: {e}")

    # Session deletion is handled by hooks.py after all events are processed.
    # This ensures session data remains available during event processing
    # and hooks.py can correctly check session count for shutdown decisions.

    await asyncio.sleep(ProcessingConstants.DEFAULT_SLEEP_SECONDS)


async def monitor_claude_pid(server_port: int) -> None:
    """Monitor if Claude process is still alive, shutdown if gone.

    Args:
        server_port: Port of this server, used to identify our session

    Periodically checks if the Claude process (parent) is still running.
    If Claude exits, triggers server shutdown to prevent orphaned servers.
    """
    from app.event_db import get_sessions_by_port
    import os
    import signal

    logger.info(f"Starting Claude PID monitor for server port {server_port}")

    check_interval = 30  # Check every 30 seconds

    while True:
        try:
            await asyncio.sleep(check_interval)

            # Get session(s) for this server port
            sessions = await get_sessions_by_port(server_port)

            if not sessions:
                logger.debug(
                    f"No sessions found for port {server_port}, continuing monitoring"
                )
                continue

            # Check each session's Claude PID
            for session in sessions:
                claude_pid = session.get("claude_pid")
                session_id = session.get("session_id")

                if not claude_pid:
                    logger.warning(f"Session {session_id} has no claude_pid, skipping")
                    continue

                # Check if Claude process exists
                if not psutil.pid_exists(claude_pid):
                    logger.info(
                        f"Claude PID {claude_pid} (session {session_id}) no longer exists, "
                        f"triggering server shutdown"
                    )

                    # Cleanup session before shutdown
                    try:
                        from app.event_db import delete_session

                        if not session_id:
                            continue
                        deleted = await delete_session(session_id)
                        if deleted:
                            logger.info(
                                f"Cleaned up session {session_id} before shutdown"
                            )
                    except Exception as e:
                        logger.warning(f"Failed to cleanup session {session_id}: {e}")

                    # Trigger graceful shutdown by sending SIGTERM to ourselves
                    # This allows FastAPI's lifespan to cleanup properly
                    logger.info("Initiating graceful server shutdown")
                    os.kill(os.getpid(), signal.SIGTERM)
                    return

        except asyncio.CancelledError:
            logger.info("Claude PID monitor cancelled, shutting down")
            raise
        except Exception as e:
            logger.error(f"Error in Claude PID monitor: {e}", exc_info=True)
            # Continue monitoring even on error
            await asyncio.sleep(check_interval)
