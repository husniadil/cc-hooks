# Background event processor for Claude Code hooks
# Handles asynchronous processing of hook events with retry logic and error handling

import asyncio
import json
from typing import Optional
from pathlib import Path
from config import config
from app.event_db import (
    get_next_pending_event,
    mark_event_processing,
    mark_event_completed,
    mark_event_failed,
)
from utils.tts_announcer import announce_event
from utils.constants import HookEvent, ProcessingConstants
from utils.hooks_constants import is_valid_hook_event

from utils.colored_logger import setup_logger, configure_root_logging

configure_root_logging()
logger = setup_logger(__name__)


async def process_events(instance_id: Optional[str] = None):
    """Background task for processing events."""
    # Get current instance ID from parameter or environment
    if instance_id is None:
        import os

        instance_id = os.getenv("CC_INSTANCE_ID")

    if not instance_id:
        logger.warning(
            "instance_id not provided - event processor will handle all events"
        )
    else:
        logger.info(f"Starting event processor for instance: {instance_id}")

    logger.info("Starting event processor")
    while True:
        try:
            # Get next pending event using database module with instance filter
            row = await get_next_pending_event(instance_id)

            if row:
                (
                    event_id,
                    session_id,
                    hook_event_name,
                    payload,
                    retry_count,
                    arguments_json,
                ) = row
                logger.info(
                    f"Processing event {event_id}: {hook_event_name} for session {session_id} (attempt {retry_count + 1}/{config.max_retry_count})"
                )

                # Mark as processing
                await mark_event_processing(event_id)

                # Prepare event data
                event_data = json.loads(payload)
                event_data["session_id"] = session_id
                event_data["hook_event_name"] = hook_event_name

                # Parse arguments if present
                arguments = None
                if arguments_json:
                    try:
                        arguments = json.loads(arguments_json)
                    except json.JSONDecodeError as e:
                        logger.warning(
                            f"Failed to parse arguments JSON for event {event_id}: {e}"
                        )
                        arguments = None

                # Retry loop
                current_retry = retry_count
                success = False
                last_error = None

                while current_retry < config.max_retry_count and not success:
                    try:
                        await process_single_event(event_data, arguments)
                        success = True

                        # Mark as completed
                        await mark_event_completed(event_id, current_retry)
                        logger.info(
                            f"Event {event_id} processed successfully after {current_retry + 1} attempt(s)"
                        )

                    except Exception as e:
                        current_retry += 1
                        last_error = str(e)
                        logger.warning(
                            f"Event {event_id} failed (attempt {current_retry}/{config.max_retry_count}): {e}"
                        )

                        if current_retry < config.max_retry_count:
                            # Small delay before retry
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
            logger.error(f"Error in event processor: {e}")
            await asyncio.sleep(ProcessingConstants.ERROR_WAIT_SECONDS)


# Sound effect processing
async def play_sound(sound_file: str):
    """Play sound using the sound player utility (BLOCKING - waits for completion)."""
    try:
        script_dir = Path(__file__).parent.parent  # Go up from app/ to project root
        sound_player_path = script_dir / "utils" / "sound_player.py"

        if not sound_player_path.exists():
            logger.warning(f"Sound player script not found: {sound_player_path}")
            return False

        # Run sound player synchronously (blocking - wait for completion)
        process = await asyncio.create_subprocess_exec(
            "uv",
            "run",
            str(sound_player_path),
            sound_file,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Wait for sound to finish playing before continuing
        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            logger.info(f"Sound played successfully: {sound_file}")
            return True
        else:
            logger.warning(
                f"Sound player failed with return code {process.returncode}: {stderr.decode()}"
            )
            return False

    except Exception as e:
        logger.warning(f"Failed to play sound {sound_file}: {e}")
        return False


# TTS announcement processing
async def play_announcement_sound(
    hook_event_name: str, event_data: dict, volume: float = 0.5
):
    """Play appropriate announcement sound based on hook event context."""
    try:
        # Use synchronous announce_event in a thread to avoid blocking
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(
            None, announce_event, hook_event_name, event_data, volume
        )

        if success:
            logger.info(f"Announced {hook_event_name} event successfully")
        else:
            logger.warning(f"Failed to announce {hook_event_name} event")

        return success

    except Exception as e:
        logger.warning(f"Failed to play announcement for {hook_event_name}: {e}")
        return False


# Your custom event processing logic
async def process_single_event(event_data: dict, arguments: Optional[dict] = None):
    """
    Process events based on hook_event_name.
    Expected fields: session_id, hook_event_name
    Optional arguments: sound_effect, etc.
    """
    # Validate required fields
    if "session_id" not in event_data:
        raise ValueError("Missing required field: session_id")
    if "hook_event_name" not in event_data:
        raise ValueError("Missing required field: hook_event_name")

    session_id = event_data["session_id"]
    hook_event_name = event_data["hook_event_name"]

    logger.info(f"Processing {hook_event_name} event for session {session_id}")

    # Prepare audio tasks for parallel execution
    audio_tasks = []

    # Check for announcement request (new intelligent mapping)
    if arguments and "announce" in arguments:
        # Volume can be specified, default to 0.5
        volume = 0.5
        if isinstance(arguments["announce"], (int, float)):
            volume = float(arguments["announce"])
        elif arguments["announce"] is True:
            volume = 0.5  # Default volume for --announce flag

        logger.info(f"Announcement requested for {hook_event_name} (volume: {volume})")
        audio_tasks.append(play_announcement_sound(hook_event_name, event_data, volume))

    # Check for sound effect argument (backward compatibility)
    if arguments and "sound_effect" in arguments:
        sound_file = arguments["sound_effect"]
        logger.info(f"Sound effect requested: {sound_file}")
        audio_tasks.append(play_sound(sound_file))

    # Run all audio tasks in parallel if any exist
    if audio_tasks:
        logger.info(f"Running {len(audio_tasks)} audio task(s) in parallel")
        audio_results = await asyncio.gather(*audio_tasks, return_exceptions=True)

        # Log results for debugging
        for i, result in enumerate(audio_results):
            if isinstance(result, Exception):
                logger.warning(f"Audio task {i+1} failed: {result}")
            else:
                logger.info(f"Audio task {i+1} completed: {result}")

        # Check if any audio task failed
        failed_tasks = [r for r in audio_results if isinstance(r, Exception)]
        if failed_tasks:
            logger.warning(
                f"{len(failed_tasks)}/{len(audio_tasks)} audio task(s) failed"
            )
        else:
            logger.info(f"All {len(audio_tasks)} audio task(s) completed successfully")

    # Check if hook event is valid first
    if not is_valid_hook_event(hook_event_name):
        logger.info(
            f"Skipping processing for unknown hook event: {hook_event_name} (session: {session_id})"
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


async def handle_generic_event(hook_event_name: str, session_id: str, event_data: dict):
    """Generic handler for all event types with configurable behavior."""
    config = EVENT_CONFIGS.get(hook_event_name, {})

    # Build log message with dynamic parameters
    log_params = {"session_id": session_id}
    if config.get("use_tool_name"):
        log_params["tool_name"] = event_data.get("tool_name", "unknown")
    if config.get("use_message"):
        log_params["message"] = event_data.get("message", "")

    log_message = config.get(
        "log_message", f"Session {session_id}: {hook_event_name} event"
    )
    logger.info(log_message.format(**log_params))

    # Handle special behaviors
    if config.get("clear_tracking"):
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

    if config.get("cleanup_old_files"):
        try:
            from utils.transcript_parser import cleanup_old_processed_files

            cleanup_old_processed_files(max_age_hours=24)
            logger.debug("Cleaned up old processed files")
        except Exception as e:
            logger.warning(f"Failed to cleanup old processed files: {e}")

    await asyncio.sleep(ProcessingConstants.DEFAULT_SLEEP_SECONDS)
