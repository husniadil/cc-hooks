import asyncio
import json
import os
import signal
from typing import Optional, Dict, Any
from pathlib import Path

import psutil

from config import config
from app.types import EventData
from app.event_db import (
    get_next_pending_event,
    get_session_by_id,
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

    Each server only processes events for sessions it owns (by server_port).
    """
    logger.info(
        f"Starting event processor for server port {server_port}"
        if server_port
        else "Starting event processor (processing all events)"
    )

    while True:
        try:
            row = await get_next_pending_event()

            if row:
                event_id, session_id, hook_event_name, payload, retry_count = row
                await mark_event_processing(event_id)

                if server_port:
                    session = await get_session_by_id(session_id)

                    if not session:
                        new_retry_count = retry_count + 1
                        logger.debug(
                            f"Session {session_id} not found for event {event_id} "
                            f"(attempt {new_retry_count}/{config.max_retry_count})"
                        )

                        if new_retry_count >= config.max_retry_count:
                            logger.error(
                                f"Session {session_id} not found after {config.max_retry_count} attempts"
                            )
                            await mark_event_failed(
                                event_id,
                                new_retry_count,
                                "Session not found after max retries",
                            )
                        else:
                            await mark_event_pending(event_id, new_retry_count)
                        continue

                    if session.get("server_port") != server_port:
                        logger.debug(
                            f"Skipping event {event_id} (belongs to port {session.get('server_port')}, we are {server_port})"
                        )
                        await mark_event_pending(event_id, retry_count)
                        continue

                logger.debug(
                    f"Processing event {event_id}: {hook_event_name} for session {session_id}"
                )

                event_data = json.loads(payload)
                event_data["session_id"] = session_id
                event_data["hook_event_name"] = hook_event_name

                current_retry = retry_count
                success = False
                last_error = None

                while current_retry < config.max_retry_count and not success:
                    try:
                        await process_single_event(event_data)
                        success = True
                        await mark_event_completed(event_id, current_retry)
                        logger.debug(f"Event {event_id} processed successfully")
                    except Exception as e:
                        current_retry += 1
                        last_error = str(e)
                        logger.warning(
                            f"Event {event_id} failed (attempt {current_retry}/{config.max_retry_count}): {e}",
                            exc_info=True,
                        )
                        if current_retry < config.max_retry_count:
                            await asyncio.sleep(ProcessingConstants.RETRY_DELAY_SECONDS)

                if not success:
                    logger.error(
                        f"Event {event_id} failed after {config.max_retry_count} attempts"
                    )
                    await mark_event_failed(
                        event_id,
                        current_retry,
                        f"Max retries ({config.max_retry_count}) exceeded. Last error: {last_error}",
                    )
            else:
                await asyncio.sleep(ProcessingConstants.NO_EVENTS_WAIT_SECONDS)

        except Exception as e:
            logger.error(
                f"Error in event processor main loop: {e}",
                exc_info=True,
                extra={"server_port": server_port},
            )
            await asyncio.sleep(ProcessingConstants.ERROR_WAIT_SECONDS)


async def play_sound(sound_file: str) -> bool:
    """Play sound using the sound player utility (blocking). Returns True on success."""
    try:
        script_dir = Path(__file__).parent.parent
        sound_player_path = script_dir / "utils" / "sound_player.py"

        if not sound_player_path.exists():
            logger.warning(f"Sound player script not found: {sound_player_path}")
            return False

        process = await asyncio.create_subprocess_exec(
            "uv",
            "run",
            str(sound_player_path),
            sound_file,
            cwd=script_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()

        if process.returncode == 0:
            logger.debug(f"Sound played successfully: {sound_file}")
            return True
        logger.warning(
            f"Sound player failed with return code {process.returncode}: {stderr.decode()}"
        )
        return False
    except Exception as e:
        logger.warning(f"Failed to play sound {sound_file}: {e}", exc_info=True)
        return False


async def play_announcement_sound(
    hook_event_name: str,
    event_data: Dict[str, Any],
    volume: float = 0.5,
    session_settings: Optional[Dict[str, Any]] = None,
) -> bool:
    """Play TTS announcement in a thread. Returns True on success."""
    try:
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(
            None, announce_event, hook_event_name, event_data, volume, session_settings
        )
        if not success:
            logger.warning(f"Failed to announce {hook_event_name} event")
        return success
    except Exception as e:
        logger.warning(
            f"Failed to play announcement for {hook_event_name}: {e}", exc_info=True
        )
        return False


async def process_single_event(event_data: EventData) -> None:
    """Process events based on hook_event_name."""
    if "session_id" not in event_data:
        raise ValueError("Missing required field: session_id")
    if "hook_event_name" not in event_data:
        raise ValueError("Missing required field: hook_event_name")

    session_id = event_data["session_id"]
    hook_event_name = event_data["hook_event_name"]
    logger.debug(f"Processing {hook_event_name} event for session {session_id}")

    session_settings = await get_session_by_id(session_id)
    if not session_settings:
        logger.warning(
            f"Session {session_id} not found in DB, using global config defaults"
        )

    silent_announcements = (
        bool(session_settings.get("silent_announcements"))
        if session_settings
        else False
    )
    silent_effects = (
        bool(session_settings.get("silent_effects")) if session_settings else False
    )

    audio_tasks = []

    if should_play_announcement(
        hook_event_name,
        silent_announcements,
        session_settings,  # type: ignore[arg-type]
    ):
        logger.debug(f"Queuing announcement for {hook_event_name}")
        audio_tasks.append(
            play_announcement_sound(
                hook_event_name,
                dict(event_data),
                0.5,
                session_settings,  # type: ignore[arg-type]
            )
        )
    elif silent_announcements:
        logger.debug(f"Silent mode — skipping announcement for {hook_event_name}")

    sound_file = should_play_sound_effect(hook_event_name, silent_effects)
    if sound_file:
        logger.debug(f"Queuing sound effect for {hook_event_name}: {sound_file}")
        audio_tasks.append(play_sound(sound_file))
    elif silent_effects:
        logger.debug(f"Silent mode — skipping sound effect for {hook_event_name}")

    if audio_tasks:
        logger.debug(f"Running {len(audio_tasks)} audio task(s) in parallel")
        audio_results = await asyncio.gather(*audio_tasks, return_exceptions=True)
        failed = [r for r in audio_results if isinstance(r, Exception)]
        if failed:
            logger.warning(f"{len(failed)}/{len(audio_tasks)} audio task(s) failed")
            for i, result in enumerate(audio_results):
                if isinstance(result, Exception):
                    logger.warning(f"Audio task {i + 1} failed: {result}")
        else:
            logger.debug(f"All {len(audio_tasks)} audio task(s) completed")

    if not is_valid_hook_event(hook_event_name):
        logger.debug(f"Skipping unknown hook event: {hook_event_name}")
        return

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

    if event_config.get("cleanup_orphaned"):
        try:
            from app.event_db import (
                cleanup_orphaned_server_processes,
                cleanup_orphaned_sessions,
            )

            exclude_sessions = (
                [session_id] if event_data.get("reason") == "clear" else []
            )
            killed_count = await cleanup_orphaned_server_processes()
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

    Periodically checks if the Claude process (parent) is still running.
    If Claude exits, triggers server shutdown to prevent orphaned servers.
    """
    from app.event_db import get_sessions_by_port, delete_session

    logger.info(f"Starting Claude PID monitor for server port {server_port}")
    check_interval = 30

    while True:
        try:
            await asyncio.sleep(check_interval)

            sessions = await get_sessions_by_port(server_port)
            if not sessions:
                continue

            for session in sessions:
                claude_pid = session.get("claude_pid")
                session_id = session.get("session_id")

                if not claude_pid or not session_id:
                    continue

                if not psutil.pid_exists(claude_pid):
                    logger.info(
                        f"Claude PID {claude_pid} (session {session_id}) no longer exists"
                    )

                    try:
                        if await delete_session(session_id):
                            logger.info(
                                f"Cleaned up session {session_id} before shutdown"
                            )
                    except Exception as e:
                        logger.warning(f"Failed to cleanup session {session_id}: {e}")

                    logger.info("Initiating graceful server shutdown")
                    os.kill(os.getpid(), signal.SIGTERM)
                    return

        except asyncio.CancelledError:
            logger.info("Claude PID monitor cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in Claude PID monitor: {e}", exc_info=True)
            await asyncio.sleep(check_interval)
