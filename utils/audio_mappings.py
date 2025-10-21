# Audio mappings for hook events
# Defines default sound effects and announcement behavior for each hook event type

from typing import Dict, Optional
from dataclasses import dataclass
from utils.constants import SoundFiles


@dataclass
class AudioConfig:
    """Audio configuration for a hook event."""

    sound_effect: Optional[str] = None  # Sound effect file to play
    has_announcement: bool = False  # Whether this event has TTS announcement


# Audio configuration for each hook event type
# Controls what audio plays for each event based on claude.sh flags
HOOK_AUDIO_MAPPINGS: Dict[str, AudioConfig] = {
    # Session lifecycle events - have announcements
    "SessionStart": AudioConfig(
        sound_effect=None,  # No additional sound effect
        has_announcement=True,  # Play TTS announcement
    ),
    "SessionEnd": AudioConfig(
        sound_effect=None,
        has_announcement=True,
    ),
    # Tool execution events
    # Note: PreToolUse announcement is CONDITIONAL - only plays if openrouter_contextual_pretooluse=True
    "PreToolUse": AudioConfig(
        sound_effect=SoundFiles.TEK,
        has_announcement=True,  # Conditional on OpenRouter setting (see should_play_announcement)
    ),
    "PostToolUse": AudioConfig(
        sound_effect=SoundFiles.CETEK,
        has_announcement=False,
    ),
    # User interaction events
    "UserPromptSubmit": AudioConfig(
        sound_effect=SoundFiles.KLEK,
        has_announcement=False,
    ),
    # Notification events
    "Notification": AudioConfig(
        sound_effect=SoundFiles.TUNG,
        has_announcement=False,
    ),
    # Task completion events - have announcements
    "Stop": AudioConfig(
        sound_effect=None,
        has_announcement=True,
    ),
    "SubagentStop": AudioConfig(
        sound_effect=SoundFiles.CETEK,
        has_announcement=False,
    ),
    # Context management
    "PreCompact": AudioConfig(
        sound_effect=None,
        has_announcement=True,
    ),
}


def get_audio_config(hook_event_name: str) -> AudioConfig:
    """
    Get audio configuration for a hook event.
    Returns default empty config if event has no audio mapping.
    """
    return HOOK_AUDIO_MAPPINGS.get(
        hook_event_name, AudioConfig(sound_effect=None, has_announcement=False)
    )


def should_play_sound_effect(
    hook_event_name: str, silent_effects: bool = False
) -> Optional[str]:
    """
    Determine if sound effect should be played for this event.
    Returns sound effect filename or None.
    """
    if silent_effects:
        return None

    config = get_audio_config(hook_event_name)
    return config.sound_effect


def should_play_announcement(
    hook_event_name: str,
    silent_announcements: bool = False,
    session_settings: dict = None,
) -> bool:
    """
    Determine if TTS announcement should be played for this event.

    For PreToolUse: Only announce if openrouter_contextual_pretooluse is True
    For other events: Use has_announcement config
    """
    if silent_announcements:
        return False

    # Special handling for PreToolUse - only announce if contextual mode enabled
    if hook_event_name == "PreToolUse":
        if session_settings:
            return session_settings.get("openrouter_contextual_pretooluse", False)
        return False

    config = get_audio_config(hook_event_name)
    return config.has_announcement
