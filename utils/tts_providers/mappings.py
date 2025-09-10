"""
Shared mappings and utilities for TTS providers.

This module contains the common data structures and utility functions
used by all TTS providers to avoid duplication and ensure consistency.
"""

from typing import Dict, Tuple, Optional, Any, Union
from utils.hooks_constants import HookEvent
from utils.colored_logger import setup_logger

logger = setup_logger(__name__)

# Mapping from event/source to appropriate MP3 files for Claude Code hook data
# Format: (hook_event_name, source) : "filename.mp3"
HOOK_EVENT_SOUND_MAP: Dict[Tuple[str, Optional[str]], str] = {
    # SessionStart events
    (HookEvent.SESSION_START.value, "startup"): "session_start_startup.mp3",
    (HookEvent.SESSION_START.value, "resume"): "session_start_resume.mp3",
    (HookEvent.SESSION_START.value, "clear"): "session_start_clear.mp3",
    (HookEvent.SESSION_START.value, "compact"): "session_start_compact.mp3",
    (HookEvent.SESSION_START.value, None): "session_start_startup.mp3",  # fallback
    (HookEvent.SESSION_START.value, "unknown"): "session_start_startup.mp3",  # fallback
    # SessionEnd events
    (HookEvent.SESSION_END.value, "clear"): "session_end_clear.mp3",
    (HookEvent.SESSION_END.value, "logout"): "session_end_logout.mp3",
    (
        HookEvent.SESSION_END.value,
        "prompt_input_exit",
    ): "session_end_prompt_input_exit.mp3",
    (HookEvent.SESSION_END.value, "other"): "session_end_other.mp3",
    (HookEvent.SESSION_END.value, None): "session_end_other.mp3",  # fallback
    # PreToolUse events
    (HookEvent.PRE_TOOL_USE.value, "tool_running"): "pre_tool_use_tool_running.mp3",
    (
        HookEvent.PRE_TOOL_USE.value,
        "command_blocked",
    ): "pre_tool_use_command_blocked.mp3",
    (HookEvent.PRE_TOOL_USE.value, None): "pre_tool_use_tool_running.mp3",  # fallback
    # PostToolUse events
    (
        HookEvent.POST_TOOL_USE.value,
        "tool_completed",
    ): "post_tool_use_tool_completed.mp3",
    (
        HookEvent.POST_TOOL_USE.value,
        None,
    ): "post_tool_use_tool_completed.mp3",  # fallback
    # Notification events
    (HookEvent.NOTIFICATION.value, "general"): "notification_general.mp3",
    (HookEvent.NOTIFICATION.value, "permission"): "notification_permission.mp3",
    (HookEvent.NOTIFICATION.value, "waiting"): "notification_waiting.mp3",
    (HookEvent.NOTIFICATION.value, None): "notification_general.mp3",  # fallback
    # UserPromptSubmit events
    (HookEvent.USER_PROMPT_SUBMIT.value, "prompt"): "user_prompt_submit_prompt.mp3",
    (
        HookEvent.USER_PROMPT_SUBMIT.value,
        None,
    ): "user_prompt_submit_prompt.mp3",  # fallback
    # Stop events
    (HookEvent.STOP.value, "task_completed"): "stop_task_completed.mp3",
    (HookEvent.STOP.value, None): "stop_task_completed.mp3",  # fallback
    # SubagentStop events
    (
        HookEvent.SUBAGENT_STOP.value,
        "agent_completed",
    ): "subagent_stop_agent_completed.mp3",
    (
        HookEvent.SUBAGENT_STOP.value,
        None,
    ): "subagent_stop_agent_completed.mp3",  # fallback
    # PreCompact events
    (HookEvent.PRE_COMPACT.value, "auto"): "pre_compact_auto.mp3",
    (HookEvent.PRE_COMPACT.value, "manual"): "pre_compact_manual.mp3",
    (HookEvent.PRE_COMPACT.value, None): "pre_compact_auto.mp3",  # fallback
}

# Audio descriptions mapping for sound files
# Maps sound file names to their descriptive content for UI/accessibility features
AUDIO_DESCRIPTIONS_MAP: Dict[str, str] = {
    "notification_general.mp3": "Notification",
    "notification_permission.mp3": "Permission required",
    "notification_waiting.mp3": "Waiting for input",
    "post_tool_use_tool_completed.mp3": "Tool completed",
    "pre_compact_auto.mp3": "Auto compacting conversation",
    "pre_compact_manual.mp3": "Compacting conversation",
    "pre_tool_use_command_blocked.mp3": "Command Blocked",
    "pre_tool_use_tool_running.mp3": "Running tool",
    "session_end_clear.mp3": "Session cleared",
    "session_end_logout.mp3": "Logout",
    "session_end_other.mp3": "Interrupted",
    "session_end_prompt_input_exit.mp3": "Session ended",
    "session_start_clear.mp3": "Fresh start",
    "session_start_compact.mp3": "Session refreshed",
    "session_start_resume.mp3": "Session resume",
    "session_start_startup.mp3": "Claude Code ready",
    "stop_task_completed.mp3": "Task completed successfully",
    "subagent_stop_agent_completed.mp3": "Agent completed successfully",
    "user_prompt_submit_prompt.mp3": "Prompt submitted",
}


def extract_source_from_event_data(
    hook_event_name: Union[str, HookEvent], event_data: Dict[str, Any]
) -> Optional[str]:
    """
    Extract source information from Claude Code hook event data.

    Args:
        hook_event_name (str): Name of the hook event
        event_data (dict): Hook event data from Claude Code

    Returns:
        str or None: Extracted source identifier
    """
    # Convert HookEvent to string if needed
    event_name = (
        hook_event_name.value
        if isinstance(hook_event_name, HookEvent)
        else hook_event_name
    )

    # Special handling for Notification events based on message content
    if event_name == HookEvent.NOTIFICATION.value and "message" in event_data:
        message = str(event_data["message"])

        if message.startswith("Claude needs your permission"):
            return "permission"
        elif message.startswith("Claude is waiting for your input"):
            return "waiting"
        else:
            return "general"

    # Special handling for PreToolUse/PostToolUse events - extract tool name for context
    if event_name in [HookEvent.PRE_TOOL_USE.value, HookEvent.POST_TOOL_USE.value]:
        tool_name = event_data.get("tool_name")
        if tool_name:
            return tool_name.lower()

    # Common source fields in Claude Code hook data
    source_fields = ["source", "reason", "trigger", "action", "type"]

    for field in source_fields:
        if field in event_data and event_data[field]:
            return str(event_data[field]).lower()

    return None


def get_sound_file_for_event(
    hook_event_name: Union[str, HookEvent], event_data: Dict[str, Any]
) -> Optional[str]:
    """
    Get the appropriate sound file name for a hook event.

    Args:
        hook_event_name (str): Name of the hook event
        event_data (dict): Hook event data from Claude Code

    Returns:
        str or None: Sound file name if found, None otherwise
    """
    try:
        # Convert HookEvent to string if needed
        event_name = (
            hook_event_name.value
            if isinstance(hook_event_name, HookEvent)
            else hook_event_name
        )

        # Extract source from event data
        source = extract_source_from_event_data(event_name, event_data)

        # Try exact match first: (event, source)
        mapping_key = (event_name, source)
        if mapping_key in HOOK_EVENT_SOUND_MAP:
            return HOOK_EVENT_SOUND_MAP[mapping_key]

        # Try fallback with None source: (event, None)
        fallback_key = (event_name, None)
        if fallback_key in HOOK_EVENT_SOUND_MAP:
            return HOOK_EVENT_SOUND_MAP[fallback_key]

        # No suitable sound found
        logger.info(f"No sound mapping for: {event_name} (source: {source})")
        return None

    except Exception as e:
        logger.error(f"Error getting sound file for event: {e}")
        return None


def get_audio_description(sound_file: str) -> Optional[str]:
    """
    Get descriptive text for a sound file.

    Args:
        sound_file (str): Name of the sound file (e.g., "session_start_startup.mp3")

    Returns:
        str or None: Description text if found, None otherwise
    """
    return AUDIO_DESCRIPTIONS_MAP.get(sound_file)
