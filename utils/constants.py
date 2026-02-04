"""
Centralized constants for Claude Code hooks processing system.

This module consolidates all system constants, enums, and configuration values
into a single location for better maintainability and type safety.
"""

from enum import Enum
from typing import Literal
from pathlib import Path

# Re-export HookEvent for convenience
from utils.hooks_constants import HookEvent

__all__ = [
    "EventStatus",
    "ProcessingConstants",
    "DatabaseConstants",
    "DateTimeConstants",
    "NetworkConstants",
    "HTTPStatusConstants",
    "PathConstants",
    "SoundFiles",
    "EventSource",
    "HookEvent",
    "get_server_url",
]


class EventStatus(Enum):
    """
    Event processing status enumeration.

    Provides type safety and prevents typos when working with event status values.
    """

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

    def __str__(self) -> str:
        """Return the string value of the event status."""
        return self.value


class ProcessingConstants:
    """Constants related to event processing timing and behavior."""

    MAX_RETRY_COUNT = 3  # Maximum number of retry attempts for failed events
    RETRY_DELAY_SECONDS = 0.5
    NO_EVENTS_WAIT_SECONDS = 0.1
    ERROR_WAIT_SECONDS = 5
    DEFAULT_SLEEP_SECONDS = 0.01

    # Orphan cleanup thresholds
    ORPHAN_PROCESS_MIN_AGE_SECONDS = 2  # Minimum age to consider process orphaned


class DatabaseConstants:
    """Constants related to database operations and queries."""

    RECENT_EVENTS_LIMIT = 10


class DateTimeConstants:
    """Constants related to date and time formatting."""

    ISO_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class NetworkConstants:
    """Constants related to network operations."""

    DEFAULT_PORT = 12222
    DEFAULT_HOST = "0.0.0.0"
    LOCALHOST = "localhost"

    # Server discovery and port management
    PORT_DISCOVERY_START = 12222
    PORT_DISCOVERY_MAX_ATTEMPTS = 50  # Support up to 50 concurrent sessions
    SERVER_STARTUP_MAX_ATTEMPTS = 20
    SERVER_STARTUP_RETRY_DELAY = 0.5  # seconds
    PORT_RANGE_MIN = 1024  # Minimum valid port for user applications
    PORT_RANGE_MAX = 65535  # Maximum valid TCP port

    # Request timeouts (seconds)
    HEALTH_CHECK_TIMEOUT = 0.5  # Fast probes for health/discovery
    SESSION_LOOKUP_TIMEOUT = 0.2  # Fast session lookup during hook calls
    API_REQUEST_TIMEOUT = 10  # Session register, delete, count
    EVENT_SUBMIT_TIMEOUT = 30  # Event POST (needs room for queue)
    SHUTDOWN_TIMEOUT = 5  # Shutdown requests
    LAST_EVENT_POLL_TIMEOUT = 2  # Polling for event completion
    GIT_COMMAND_TIMEOUT = 5  # Git commands (describe, rev-list)
    GIT_FETCH_TIMEOUT = 10  # Git fetch (network operation)


class HTTPStatusConstants:
    """HTTP status code constants for better maintainability."""

    OK = 200
    BAD_REQUEST = 400
    NOT_FOUND = 404
    INTERNAL_SERVER_ERROR = 500


class PathConstants:
    """
    File system path constants for cc-hooks data storage.

    All runtime data is stored in a shared directory (~/.claude/.cc-hooks/)
    to ensure persistence across plugin updates and support both standalone
    and plugin installation modes.
    """

    # Shared data directory (persists across plugin updates)
    SHARED_DATA_DIR = Path.home() / ".claude" / ".cc-hooks"

    # Subdirectories
    LOGS_DIR = SHARED_DATA_DIR / "logs"
    TTS_CACHE_DIR = SHARED_DATA_DIR / ".tts_cache"

    # Cache subdirectories by provider
    TTS_CACHE_PRERECORDED_DIR = TTS_CACHE_DIR / "prerecorded"
    TTS_CACHE_GTTS_DIR = TTS_CACHE_DIR / "gtts"
    TTS_CACHE_ELEVENLABS_DIR = TTS_CACHE_DIR / "elevenlabs"

    # Database path
    DATABASE_PATH = SHARED_DATA_DIR / "events.db"

    # Transcript tracking files (shared data dir for persistence across reboots)
    TRANSCRIPT_TRACKING_DIR = SHARED_DATA_DIR / "transcript-tracking"


class SoundFiles:
    """
    Sound effect file name constants.

    These files are located in the sound/ directory of the project.
    Using constants prevents typos and makes refactoring easier.
    """

    # Sound effects (short interaction sounds)
    TEK = "sound_effect_tek.mp3"
    CETEK = "sound_effect_cetek.mp3"
    KLEK = "sound_effect_klek.mp3"
    TUNG = "sound_effect_tung.mp3"

    # SessionStart announcements (prerecorded)
    SESSION_START_STARTUP = "session_start_startup.mp3"
    SESSION_START_CLEAR = "session_start_clear.mp3"
    SESSION_START_COMPACT = "session_start_compact.mp3"
    SESSION_START_RESUME = "session_start_resume.mp3"

    # SessionEnd announcements (prerecorded)
    SESSION_END_LOGOUT = "session_end_logout.mp3"
    SESSION_END_CLEAR = "session_end_clear.mp3"
    SESSION_END_PROMPT_INPUT_EXIT = "session_end_prompt_input_exit.mp3"
    SESSION_END_OTHER = "session_end_other.mp3"

    # PreToolUse announcements (prerecorded)
    PRE_TOOL_USE_TOOL_RUNNING = "pre_tool_use_tool_running.mp3"
    PRE_TOOL_USE_COMMAND_BLOCKED = "pre_tool_use_command_blocked.mp3"

    # PostToolUse announcements (prerecorded)
    POST_TOOL_USE_TOOL_COMPLETED = "post_tool_use_tool_completed.mp3"

    # Notification announcements (prerecorded)
    NOTIFICATION_GENERAL = "notification_general.mp3"
    NOTIFICATION_PERMISSION = "notification_permission.mp3"
    NOTIFICATION_WAITING = "notification_waiting.mp3"

    # Stop announcements (prerecorded)
    STOP_TASK_COMPLETED = "stop_task_completed.mp3"

    # SubagentStop announcements (prerecorded)
    SUBAGENT_STOP_AGENT_COMPLETED = "subagent_stop_agent_completed.mp3"

    # PreCompact announcements (prerecorded)
    PRE_COMPACT_AUTO = "pre_compact_auto.mp3"
    PRE_COMPACT_MANUAL = "pre_compact_manual.mp3"

    # UserPromptSubmit announcements (prerecorded)
    USER_PROMPT_SUBMIT_PROMPT = "user_prompt_submit_prompt.mp3"


class EventSource:
    """
    Event source/reason identifier constants.

    These constants represent the source or reason for hook events,
    used in event data payloads to determine which variant of an event occurred.
    """

    # SessionStart sources
    class SessionStart:
        STARTUP = "startup"
        RESUME = "resume"
        CLEAR = "clear"
        COMPACT = "compact"
        UNKNOWN = "unknown"

    # SessionEnd sources
    class SessionEnd:
        CLEAR = "clear"
        LOGOUT = "logout"
        PROMPT_INPUT_EXIT = "prompt_input_exit"
        OTHER = "other"

    # PreToolUse sources
    class PreToolUse:
        TOOL_RUNNING = "tool_running"
        COMMAND_BLOCKED = "command_blocked"

    # PostToolUse sources
    class PostToolUse:
        TOOL_COMPLETED = "tool_completed"

    # Notification sources
    class Notification:
        GENERAL = "general"
        PERMISSION = "permission"
        WAITING = "waiting"

    # UserPromptSubmit sources
    class UserPromptSubmit:
        PROMPT = "prompt"

    # Stop sources
    class Stop:
        TASK_COMPLETED = "task_completed"

    # SubagentStop sources
    class SubagentStop:
        AGENT_COMPLETED = "agent_completed"

    # PreCompact sources
    class PreCompact:
        AUTO = "auto"
        MANUAL = "manual"


# Type alias for backward compatibility
EventStatusLiteral = Literal["pending", "processing", "completed", "failed"]


# Helper functions
def get_server_url(
    port: int = NetworkConstants.DEFAULT_PORT, endpoint: str = ""
) -> str:
    """
    Generate server URL for API calls.

    Args:
        port: Server port number (defaults to DEFAULT_PORT)
        endpoint: API endpoint path (should start with / if provided)

    Returns:
        Complete server URL with endpoint
    """
    return f"http://{NetworkConstants.LOCALHOST}:{port}{endpoint}"
