"""
Pre-recorded sounds provider for Claude Code hooks TTS system.

This provider uses pre-recorded MP3 files stored in the sound/ directory,
providing the original behavior of the TTS announcement system.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional
from .base import TTSProvider
from .mappings import get_sound_file_for_event

logger = logging.getLogger(__name__)


class PrerecordedProvider(TTSProvider):
    """TTS provider that uses pre-recorded sound files."""

    def __init__(self, **kwargs):
        """
        Initialize the pre-recorded sounds provider.

        Args:
            **kwargs: Ignored for compatibility with other providers
        """
        self.sound_dir = self._get_sound_dir()

    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "prerecorded"

    def is_available(self) -> bool:
        """Check if sound directory exists and has sound files."""
        try:
            return self.sound_dir.exists() and any(
                f.suffix.lower() == ".mp3" for f in self.sound_dir.iterdir()
            )
        except Exception:
            return False

    def generate_speech(
        self, hook_event_name: str, event_data: Dict[str, Any]
    ) -> Optional[Path]:
        """
        Get the appropriate pre-recorded sound file for the hook event.
        Only returns a sound file if it actually exists on disk.

        This enforces that prerecorded provider only plays sounds for which
        we have actual audio files, ensuring fallback to TTS providers
        when translated text doesn't have corresponding prerecorded sounds.

        Args:
            hook_event_name (str): Name of the hook event
            event_data (dict): Hook event data from Claude Code

        Returns:
            Path or None: Path to sound file if found, None otherwise
        """
        try:
            # Get sound file name from shared mapping
            sound_file = get_sound_file_for_event(hook_event_name, event_data)

            if not sound_file:
                logger.info(f"No prerecorded sound mapping for: {hook_event_name}")
                return None

            # Get the full path to the sound file
            sound_path = self._get_sound_file_path(sound_file)

            if sound_path:
                logger.info(f"Found prerecorded sound: {sound_file}")
                return sound_path
            else:
                logger.warning(
                    f"Sound file not found: {sound_file} - falling back to TTS providers"
                )
                return None

        except Exception as e:
            logger.error(f"Error getting prerecorded sound: {e}")
            return None

    def _get_sound_dir(self) -> Path:
        """Get the sound directory path relative to the script location."""
        return Path(__file__).parent.parent.parent / "sound"

    def _get_sound_file_path(self, sound_file: str) -> Optional[Path]:
        """
        Get the full path to a sound file.

        Args:
            sound_file (str): Sound file name

        Returns:
            Path or None: Path to the sound file if it exists, None otherwise
        """
        sound_path = self.sound_dir / sound_file
        return sound_path if sound_path.exists() else None
