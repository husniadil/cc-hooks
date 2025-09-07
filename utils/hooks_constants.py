"""
Hook event constants for Claude Code hooks system.

This module defines all supported hook event types as an Enum,
providing type safety and preventing magic string usage throughout the system.
"""

from enum import Enum


class HookEvent(Enum):
    """
    Enumeration of all Claude Code hook events.

    These correspond to the hook events that Claude Code can trigger.
    Each enum member has a string value that matches the actual hook event name.
    """

    SESSION_START = "SessionStart"
    SESSION_END = "SessionEnd"
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    NOTIFICATION = "Notification"
    USER_PROMPT_SUBMIT = "UserPromptSubmit"
    STOP = "Stop"
    SUBAGENT_STOP = "SubagentStop"
    PRE_COMPACT = "PreCompact"

    def __str__(self) -> str:
        """Return the string value of the hook event."""
        return self.value


def get_all_hook_events() -> list[str]:
    """
    Get all hook event names as strings.

    Returns:
        list[str]: List of all hook event names
    """
    return [event.value for event in HookEvent]


def is_valid_hook_event(event_name: str) -> bool:
    """
    Check if a string is a valid hook event name.

    Args:
        event_name (str): Event name to validate

    Returns:
        bool: True if valid hook event name, False otherwise
    """
    return event_name in get_all_hook_events()
