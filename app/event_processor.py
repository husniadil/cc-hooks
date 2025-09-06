# Background event processor for Claude Code hooks
# Handles asynchronous processing of hook events with retry logic and error handling

import asyncio
import json
import logging
import subprocess
from typing import Literal, Optional
from pathlib import Path
from app.config import config
from app.event_db import (
    get_next_pending_event,
    mark_event_processing,
    mark_event_completed,
    mark_event_failed,
)

# Hook event name literals
HookEventName = Literal[
    "SessionStart",
    "SessionEnd",
    "PreToolUse",
    "PostToolUse",
    "Notification",
    "UserPromptSubmit",
    "Stop",
    "SubagentStop",
    "PreCompact",
]
HOOK_SESSION_START: HookEventName = "SessionStart"
HOOK_SESSION_END: HookEventName = "SessionEnd"
HOOK_PRE_TOOL_USE: HookEventName = "PreToolUse"
HOOK_POST_TOOL_USE: HookEventName = "PostToolUse"
HOOK_NOTIFICATION: HookEventName = "Notification"
HOOK_USER_PROMPT_SUBMIT: HookEventName = "UserPromptSubmit"
HOOK_STOP: HookEventName = "Stop"
HOOK_SUBAGENT_STOP: HookEventName = "SubagentStop"
HOOK_PRE_COMPACT: HookEventName = "PreCompact"

# Constants
RETRY_DELAY_SECONDS = 0.5
NO_EVENTS_WAIT_SECONDS = 1
ERROR_WAIT_SECONDS = 5
DEFAULT_SLEEP_SECONDS = 0.01

# Configure logging
logger = logging.getLogger(__name__)


async def process_events():
    """Background task for processing events."""
    logger.info("Starting event processor")
    while True:
        try:
            # Get next pending event using database module
            row = await get_next_pending_event()

            if row:
                event_id, session_id, hook_event_name, payload, retry_count, arguments_json = row
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
                        logger.warning(f"Failed to parse arguments JSON for event {event_id}: {e}")
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
                            await asyncio.sleep(RETRY_DELAY_SECONDS)

                if not success:
                    # Max retries exceeded, mark as failed
                    logger.error(
                        f"Event {event_id} failed after {config.max_retry_count} attempts. Skipping."
                    )
                    error_message = f"Max retries ({config.max_retry_count}) exceeded. Last error: {last_error}"
                    await mark_event_failed(event_id, current_retry, error_message)
            else:
                # No pending events, wait a bit
                await asyncio.sleep(NO_EVENTS_WAIT_SECONDS)

        except Exception as e:
            logger.error(f"Error in event processor: {e}")
            await asyncio.sleep(ERROR_WAIT_SECONDS)


# Sound effect processing
async def play_sound_effect(sound_file: str):
    """Play sound effect using the sound player utility."""
    try:
        script_dir = Path(__file__).parent.parent  # Go up from app/ to project root
        sound_player_path = script_dir / "utils" / "sound_player.py"
        
        if not sound_player_path.exists():
            logger.warning(f"Sound player script not found: {sound_player_path}")
            return False
            
        # Run sound player in background (non-blocking)
        process = await asyncio.create_subprocess_exec(
            "uv", "run", str(sound_player_path), sound_file,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        
        # Don't wait for completion, let it play in background
        logger.info(f"Triggered sound effect: {sound_file}")
        return True
        
    except Exception as e:
        logger.warning(f"Failed to play sound effect {sound_file}: {e}")
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
    
    # Check for sound effect argument
    if arguments and "sound_effect" in arguments:
        sound_file = arguments["sound_effect"]
        logger.info(f"Sound effect requested: {sound_file}")
        await play_sound_effect(sound_file)

    # Handle different hook event types
    if hook_event_name == HOOK_SESSION_START:
        await handle_session_start(session_id, event_data)
    elif hook_event_name == HOOK_SESSION_END:
        await handle_session_end(session_id, event_data)
    elif hook_event_name == HOOK_PRE_TOOL_USE:
        await handle_pre_tool_use(session_id, event_data)
    elif hook_event_name == HOOK_POST_TOOL_USE:
        await handle_post_tool_use(session_id, event_data)
    elif hook_event_name == HOOK_NOTIFICATION:
        await handle_notification(session_id, event_data)
    elif hook_event_name == HOOK_USER_PROMPT_SUBMIT:
        await handle_user_prompt_submit(session_id, event_data)
    elif hook_event_name == HOOK_STOP:
        await handle_stop(session_id, event_data)
    elif hook_event_name == HOOK_SUBAGENT_STOP:
        await handle_subagent_stop(session_id, event_data)
    elif hook_event_name == HOOK_PRE_COMPACT:
        await handle_pre_compact(session_id, event_data)
    else:
        logger.warning(f"Unknown hook_event_name: {hook_event_name}")


# Handler functions for each event type
async def handle_session_start(session_id: str, event_data: dict):
    """Handle SessionStart event"""
    logger.info(f"Session {session_id} started")
    # Add your SessionStart logic here
    await asyncio.sleep(DEFAULT_SLEEP_SECONDS)


async def handle_session_end(session_id: str, event_data: dict):
    """Handle SessionEnd event"""
    logger.info(f"Session {session_id} ended")
    # Add your SessionEnd logic here
    await asyncio.sleep(DEFAULT_SLEEP_SECONDS)


async def handle_pre_tool_use(session_id: str, event_data: dict):
    """Handle PreToolUse event"""
    tool_name = event_data.get("tool_name", "unknown")
    logger.info(f"Session {session_id}: Pre-tool use for {tool_name}")
    # Add your PreToolUse logic here
    await asyncio.sleep(DEFAULT_SLEEP_SECONDS)


async def handle_post_tool_use(session_id: str, event_data: dict):
    """Handle PostToolUse event"""
    tool_name = event_data.get("tool_name", "unknown")
    logger.info(f"Session {session_id}: Post-tool use for {tool_name}")
    # Add your PostToolUse logic here
    await asyncio.sleep(DEFAULT_SLEEP_SECONDS)


async def handle_notification(session_id: str, event_data: dict):
    """Handle Notification event"""
    message = event_data.get("message", "")
    logger.info(f"Session {session_id}: Notification - {message}")
    # Add your Notification logic here
    await asyncio.sleep(DEFAULT_SLEEP_SECONDS)


async def handle_user_prompt_submit(session_id: str, event_data: dict):
    """Handle UserPromptSubmit event"""
    prompt = event_data.get("prompt", "")
    logger.info(f"Session {session_id}: User submitted prompt")
    # Add your UserPromptSubmit logic here
    await asyncio.sleep(DEFAULT_SLEEP_SECONDS)


async def handle_stop(session_id: str, event_data: dict):
    """Handle Stop event"""
    logger.info(f"Session {session_id}: Stop event received")
    # Add your Stop logic here
    await asyncio.sleep(DEFAULT_SLEEP_SECONDS)


async def handle_subagent_stop(session_id: str, event_data: dict):
    """Handle SubagentStop event"""
    logger.info(f"Session {session_id}: Subagent stopped")
    # Add your SubagentStop logic here
    await asyncio.sleep(DEFAULT_SLEEP_SECONDS)


async def handle_pre_compact(session_id: str, event_data: dict):
    """Handle PreCompact event"""
    logger.info(f"Session {session_id}: Pre-compact event")
    # Add your PreCompact logic here
    await asyncio.sleep(DEFAULT_SLEEP_SECONDS)
