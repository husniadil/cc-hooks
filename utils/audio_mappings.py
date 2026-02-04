from typing import Dict, Optional
from dataclasses import dataclass
from utils.constants import SoundFiles


@dataclass
class AudioConfig:
    """Audio configuration for a hook event."""

    sound_effect: Optional[str] = None
    has_announcement: bool = False


HOOK_AUDIO_MAPPINGS: Dict[str, AudioConfig] = {
    "SessionStart": AudioConfig(has_announcement=True),
    "SessionEnd": AudioConfig(has_announcement=True),
    "PreToolUse": AudioConfig(sound_effect=SoundFiles.TEK, has_announcement=True),
    "PostToolUse": AudioConfig(sound_effect=SoundFiles.CETEK),
    "UserPromptSubmit": AudioConfig(sound_effect=SoundFiles.KLEK),
    "Notification": AudioConfig(sound_effect=SoundFiles.TUNG),
    "Stop": AudioConfig(has_announcement=True),
    "SubagentStop": AudioConfig(sound_effect=SoundFiles.CETEK),
    "PreCompact": AudioConfig(has_announcement=True),
}


def get_audio_config(hook_event_name: str) -> AudioConfig:
    """Get audio configuration for a hook event. Returns default if unmapped."""
    return HOOK_AUDIO_MAPPINGS.get(hook_event_name, AudioConfig())


def should_play_sound_effect(
    hook_event_name: str, silent_effects: bool = False
) -> Optional[str]:
    """Return sound effect filename for this event, or None if silent/unmapped."""
    if silent_effects:
        return None
    return get_audio_config(hook_event_name).sound_effect


def should_play_announcement(
    hook_event_name: str,
    silent_announcements: bool = False,
    session_settings: dict | None = None,
) -> bool:
    """Check if TTS announcement should play. PreToolUse requires contextual mode."""
    if silent_announcements:
        return False

    if hook_event_name == "PreToolUse":
        return (
            bool(session_settings.get("openrouter_contextual_pretooluse", False))
            if session_settings
            else False
        )

    return get_audio_config(hook_event_name).has_announcement
