#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "gtts",
# ]
# ///
"""
Google Text-to-Speech provider for Claude Code hooks TTS system.

This provider generates speech using Google's TTS service and caches
the results for better performance and reduced API calls.
"""

import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from .base import TTSProvider
from .mappings import get_sound_file_for_event, get_audio_description

logger = logging.getLogger(__name__)

try:
    from gtts import gTTS

    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False
    logger.warning("gTTS not available. Install with: uv add gtts")


class GTTSProvider(TTSProvider):
    """TTS provider that uses Google Text-to-Speech service."""

    def __init__(self, language: str = "en", cache_enabled: bool = True):
        """
        Initialize the gTTS provider.

        Args:
            language (str): Language code for TTS (default: "en")
            cache_enabled (bool): Whether to enable caching (default: True)
        """
        self.language = language
        self.cache_enabled = cache_enabled
        self.cache_dir = self._get_cache_dir()

        if cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "gtts"

    def is_available(self) -> bool:
        """Check if gTTS is available and can be used."""
        return GTTS_AVAILABLE

    def generate_speech(
        self, hook_event_name: str, event_data: Dict[str, Any]
    ) -> Optional[Path]:
        """
        Generate speech using Google TTS for the given hook event.

        Args:
            hook_event_name (str): Name of the hook event
            event_data (dict): Hook event data from Claude Code

        Returns:
            Path or None: Path to generated audio file if successful, None otherwise
        """
        if not GTTS_AVAILABLE:
            logger.error("gTTS not available")
            return None

        try:
            # Get text to speak for this event
            text = self._get_text_for_event(hook_event_name, event_data)
            if not text:
                logger.warning(f"No text found for event: {hook_event_name}")
                return None

            # Generate cache key
            cache_key = self._generate_cache_key(text, self.language)
            cached_file = self.cache_dir / f"{cache_key}.mp3"

            # Return cached file if it exists
            if self.cache_enabled and cached_file.exists():
                logger.info(f"Using cached TTS file: {cached_file.name}")
                return cached_file

            # Generate new TTS file
            logger.info(f"Generating TTS for text: '{text}'")
            tts = gTTS(text=text, lang=self.language)

            if self.cache_enabled:
                # Save to cache
                tts.save(str(cached_file))
                logger.info(f"Saved TTS to cache: {cached_file.name}")
                return cached_file
            else:
                # Save to temporary file
                import tempfile

                temp_file = Path(tempfile.mktemp(suffix=".mp3"))
                tts.save(str(temp_file))
                logger.info(f"Generated temporary TTS file: {temp_file}")
                return temp_file

        except Exception as e:
            logger.error(f"Error generating gTTS speech: {e}")
            return None

    def cleanup(self) -> None:
        """Clean up temporary files if cache is disabled."""
        if not self.cache_enabled:
            # Could implement temp file cleanup here
            pass

    def _get_cache_dir(self) -> Path:
        """Get the cache directory for gTTS files."""
        return Path(__file__).parent.parent.parent / ".tts_cache" / "gtts"

    def _generate_cache_key(self, text: str, language: str) -> str:
        """
        Generate a cache key for the given text and language.

        Args:
            text (str): Text to generate key for
            language (str): Language code

        Returns:
            str: Cache key (MD5 hash)
        """
        cache_input = f"{text}_{language}".encode("utf-8")
        return hashlib.md5(cache_input).hexdigest()

    def _get_text_for_event(
        self, hook_event_name: str, event_data: Dict[str, Any]
    ) -> Optional[str]:
        """
        Get the text to speak for the given hook event.
        Uses OpenRouter service for context-aware text generation and translation.
        Falls back to static mappings if OpenRouter is unavailable.

        Args:
            hook_event_name (str): Name of the hook event
            event_data (dict): Hook event data from Claude Code

        Returns:
            str or None: Text to speak if found, None otherwise
        """
        # Get sound file name from shared mapping for fallback text
        sound_file = get_sound_file_for_event(hook_event_name, event_data)
        fallback_text = None

        if sound_file:
            # Get descriptive text for the sound file
            description = get_audio_description(sound_file)
            if description:
                fallback_text = description

        # Final fallback: use event name as text
        if not fallback_text:
            fallback_text = hook_event_name.replace("_", " ")

        # Apply OpenRouter context-aware generation and translation if available
        try:
            from utils.openrouter_service import translate_text_if_available

            # This will use existing context-aware translation prompts
            translated_text = translate_text_if_available(
                fallback_text, self.language, hook_event_name, event_data
            )
            return translated_text
        except ImportError:
            # OpenRouter service not available, use fallback text
            return fallback_text
