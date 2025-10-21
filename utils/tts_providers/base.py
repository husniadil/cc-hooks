"""
Base abstract class for TTS providers in Claude Code hooks system.

Defines the common interface that all TTS providers must implement,
ensuring consistent behavior across different TTS services.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional


class TTSProvider(ABC):
    """Abstract base class for text-to-speech providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of this TTS provider."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if this provider is available and ready to use.

        Returns:
            bool: True if provider can be used, False otherwise
        """
        pass

    @abstractmethod
    def generate_speech(
        self, hook_event_name: str, event_data: Dict[str, Any]
    ) -> Optional[Path]:
        """
        Generate or retrieve audio for the given hook event.

        Args:
            hook_event_name (str): Name of the hook event (e.g., "SessionStart")
            event_data (dict): Hook event data from Claude Code

        Returns:
            Path or None: Path to audio file if successful, None otherwise
        """
        pass

    def cleanup(self) -> None:
        """
        Perform any cleanup operations for this provider.

        This is called when the provider is no longer needed.
        Override if your provider needs cleanup (e.g., cache cleanup).
        """
        pass

    def _get_text_for_event(
        self, hook_event_name: str, event_data: Dict[str, Any]
    ) -> Optional[str]:
        """
        Get the text to speak for the given hook event.
        Uses prepared text from event_data if available, falls back to event name.

        This is a shared helper method for text-based TTS providers.

        Args:
            hook_event_name (str): Name of the hook event
            event_data (dict): Hook event data from Claude Code

        Returns:
            str or None: Text to speak if found, None otherwise
        """
        # Check for prepared text from tts_announcer
        prepared_text = event_data.get("_prepared_text")
        if prepared_text:
            return prepared_text

        # Fallback: use event name as text
        return hook_event_name.replace("_", " ")
