"""Type definitions for the application."""

from typing import TypedDict, Optional


class EventData(TypedDict, total=False):
    """Represents event data from hook events."""

    session_id: str  # Required
    hook_event_name: str  # Required
    transcript_path: Optional[str]
    tool_name: Optional[str]
    message: Optional[str]
    reason: Optional[str]
    cwd: Optional[str]
    source: Optional[str]
    # Allow arbitrary additional fields from hook events


class SessionRow(TypedDict):
    """Represents a session row from the database."""

    session_id: str
    claude_pid: int
    server_port: int
    tts_language: Optional[str]
    tts_providers: Optional[str]
    tts_cache_enabled: bool
    elevenlabs_voice_id: Optional[str]
    elevenlabs_model_id: Optional[str]
    silent_announcements: bool
    silent_effects: bool
    openrouter_enabled: bool
    openrouter_model: Optional[str]
    openrouter_contextual_stop: bool
    openrouter_contextual_pretooluse: bool
    created_at: str
