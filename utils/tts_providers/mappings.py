"""
Shared mappings and utilities for TTS providers.

This module contains the common data structures and utility functions
used by all TTS providers to avoid duplication and ensure consistency.
"""

from typing import Dict, Tuple, Optional, Any, Union
from utils.constants import HookEvent, SoundFiles, EventSource
from utils.colored_logger import setup_logger

logger = setup_logger(__name__)

# Mapping from event/source to appropriate MP3 files for Claude Code hook data
# Format: (hook_event_name, source) : "filename.mp3"
HOOK_EVENT_SOUND_MAP: Dict[Tuple[str, Optional[str]], str] = {
    # SessionStart events
    (
        HookEvent.SESSION_START.value,
        EventSource.SessionStart.STARTUP,
    ): SoundFiles.SESSION_START_STARTUP,
    (
        HookEvent.SESSION_START.value,
        EventSource.SessionStart.RESUME,
    ): SoundFiles.SESSION_START_RESUME,
    (
        HookEvent.SESSION_START.value,
        EventSource.SessionStart.CLEAR,
    ): SoundFiles.SESSION_START_CLEAR,
    (
        HookEvent.SESSION_START.value,
        EventSource.SessionStart.COMPACT,
    ): SoundFiles.SESSION_START_COMPACT,
    (HookEvent.SESSION_START.value, None): SoundFiles.SESSION_START_STARTUP,  # fallback
    (
        HookEvent.SESSION_START.value,
        EventSource.SessionStart.UNKNOWN,
    ): SoundFiles.SESSION_START_STARTUP,  # fallback
    # SessionEnd events
    (
        HookEvent.SESSION_END.value,
        EventSource.SessionEnd.CLEAR,
    ): SoundFiles.SESSION_END_CLEAR,
    (
        HookEvent.SESSION_END.value,
        EventSource.SessionEnd.LOGOUT,
    ): SoundFiles.SESSION_END_LOGOUT,
    (
        HookEvent.SESSION_END.value,
        EventSource.SessionEnd.PROMPT_INPUT_EXIT,
    ): SoundFiles.SESSION_END_PROMPT_INPUT_EXIT,
    (
        HookEvent.SESSION_END.value,
        EventSource.SessionEnd.OTHER,
    ): SoundFiles.SESSION_END_OTHER,
    (HookEvent.SESSION_END.value, None): SoundFiles.SESSION_END_OTHER,  # fallback
    # PreToolUse events
    (
        HookEvent.PRE_TOOL_USE.value,
        EventSource.PreToolUse.TOOL_RUNNING,
    ): SoundFiles.PRE_TOOL_USE_TOOL_RUNNING,
    (
        HookEvent.PRE_TOOL_USE.value,
        EventSource.PreToolUse.COMMAND_BLOCKED,
    ): SoundFiles.PRE_TOOL_USE_COMMAND_BLOCKED,
    (
        HookEvent.PRE_TOOL_USE.value,
        None,
    ): SoundFiles.PRE_TOOL_USE_TOOL_RUNNING,  # fallback
    # PostToolUse events
    (
        HookEvent.POST_TOOL_USE.value,
        EventSource.PostToolUse.TOOL_COMPLETED,
    ): SoundFiles.POST_TOOL_USE_TOOL_COMPLETED,
    (
        HookEvent.POST_TOOL_USE.value,
        None,
    ): SoundFiles.POST_TOOL_USE_TOOL_COMPLETED,  # fallback
    # Notification events
    (
        HookEvent.NOTIFICATION.value,
        EventSource.Notification.GENERAL,
    ): SoundFiles.NOTIFICATION_GENERAL,
    (
        HookEvent.NOTIFICATION.value,
        EventSource.Notification.PERMISSION,
    ): SoundFiles.NOTIFICATION_PERMISSION,
    (
        HookEvent.NOTIFICATION.value,
        EventSource.Notification.WAITING,
    ): SoundFiles.NOTIFICATION_WAITING,
    (HookEvent.NOTIFICATION.value, None): SoundFiles.NOTIFICATION_GENERAL,  # fallback
    # UserPromptSubmit events
    (
        HookEvent.USER_PROMPT_SUBMIT.value,
        EventSource.UserPromptSubmit.PROMPT,
    ): SoundFiles.USER_PROMPT_SUBMIT_PROMPT,
    (
        HookEvent.USER_PROMPT_SUBMIT.value,
        None,
    ): SoundFiles.USER_PROMPT_SUBMIT_PROMPT,  # fallback
    # Stop events
    (
        HookEvent.STOP.value,
        EventSource.Stop.TASK_COMPLETED,
    ): SoundFiles.STOP_TASK_COMPLETED,
    (HookEvent.STOP.value, None): SoundFiles.STOP_TASK_COMPLETED,  # fallback
    # SubagentStop events
    (
        HookEvent.SUBAGENT_STOP.value,
        EventSource.SubagentStop.AGENT_COMPLETED,
    ): SoundFiles.SUBAGENT_STOP_AGENT_COMPLETED,
    (
        HookEvent.SUBAGENT_STOP.value,
        None,
    ): SoundFiles.SUBAGENT_STOP_AGENT_COMPLETED,  # fallback
    # PreCompact events
    (
        HookEvent.PRE_COMPACT.value,
        EventSource.PreCompact.AUTO,
    ): SoundFiles.PRE_COMPACT_AUTO,
    (
        HookEvent.PRE_COMPACT.value,
        EventSource.PreCompact.MANUAL,
    ): SoundFiles.PRE_COMPACT_MANUAL,
    (HookEvent.PRE_COMPACT.value, None): SoundFiles.PRE_COMPACT_AUTO,  # fallback
}

# Audio descriptions mapping for sound files
# Maps sound file names to their descriptive content for UI/accessibility features
AUDIO_DESCRIPTIONS_MAP: Dict[str, str] = {
    SoundFiles.NOTIFICATION_GENERAL: "Notification",
    SoundFiles.NOTIFICATION_PERMISSION: "Permission required",
    SoundFiles.NOTIFICATION_WAITING: "Waiting for input",
    SoundFiles.POST_TOOL_USE_TOOL_COMPLETED: "Tool completed",
    SoundFiles.PRE_COMPACT_AUTO: "Auto compacting conversation",
    SoundFiles.PRE_COMPACT_MANUAL: "Compacting conversation",
    SoundFiles.PRE_TOOL_USE_COMMAND_BLOCKED: "Command Blocked",
    SoundFiles.PRE_TOOL_USE_TOOL_RUNNING: "Running tool",
    SoundFiles.SESSION_END_CLEAR: "Session cleared",
    SoundFiles.SESSION_END_LOGOUT: "Logout",
    SoundFiles.SESSION_END_OTHER: "Interrupted",
    SoundFiles.SESSION_END_PROMPT_INPUT_EXIT: "Session ended",
    SoundFiles.SESSION_START_CLEAR: "Fresh start",
    SoundFiles.SESSION_START_COMPACT: "Session refreshed",
    SoundFiles.SESSION_START_RESUME: "Session resume",
    SoundFiles.SESSION_START_STARTUP: "Claude Code ready",
    SoundFiles.STOP_TASK_COMPLETED: "Task completed successfully",
    SoundFiles.SUBAGENT_STOP_AGENT_COMPLETED: "Agent completed successfully",
    SoundFiles.USER_PROMPT_SUBMIT_PROMPT: "Prompt submitted",
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
            return EventSource.Notification.PERMISSION
        elif message.startswith("Claude is waiting for your input"):
            return EventSource.Notification.WAITING
        else:
            return EventSource.Notification.GENERAL

    # Special handling for PreToolUse/PostToolUse events - extract tool name for context
    if event_name in [HookEvent.PRE_TOOL_USE.value, HookEvent.POST_TOOL_USE.value]:
        tool_name = event_data.get("tool_name")
        if tool_name:
            return str(tool_name).lower()

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
    result: str | None = AUDIO_DESCRIPTIONS_MAP.get(sound_file)
    return result
