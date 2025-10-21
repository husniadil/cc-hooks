"""
ElevenLabs Text-to-Speech provider for Claude Code hooks TTS system.

This provider generates high-quality speech using ElevenLabs API and caches
the results for better performance and reduced API calls.
"""

import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
from .base import TTSProvider
from utils.colored_logger import setup_logger

logger = setup_logger(__name__)

try:
    from elevenlabs.client import ElevenLabs

    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False
    logger.warning("ElevenLabs not available. Install with: uv add elevenlabs")


class ElevenLabsProvider(TTSProvider):
    """TTS provider that uses ElevenLabs API for high-quality speech generation."""

    def __init__(
        self,
        language: str = "en",
        cache_enabled: bool = True,
        api_key: Optional[str] = None,
        voice_id: Optional[str] = None,
        model_id: str = "eleven_flash_v2_5",
    ):
        """
        Initialize the ElevenLabs provider.

        Args:
            language (str): Language code for TTS (default: "en")
            cache_enabled (bool): Whether to enable caching (default: True)
            api_key (str): ElevenLabs API key (defaults to ELEVENLABS_API_KEY env var)
            voice_id (str): Voice ID to use (defaults to ELEVENLABS_VOICE_ID env var or Rachel)
            model_id (str): Model ID to use (default: "eleven_flash_v2_5" for speed)
        """
        self.language = language
        self.cache_enabled = cache_enabled
        self.api_key = api_key or ""
        self.voice_id = voice_id or "21m00Tcm4TlvDq8ikWAM"  # Rachel voice
        self.model_id = model_id
        self.cache_dir = self._get_cache_dir()

        self._client = None
        self._is_setup_complete = False

        if cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "elevenlabs"

    def is_available(self) -> bool:
        """Check if ElevenLabs is available and can be used."""
        if not ELEVENLABS_AVAILABLE:
            return False

        if not self.api_key:
            logger.warning(
                "ElevenLabs API key not provided. Set ELEVENLABS_API_KEY environment variable."
            )
            return False

        return self._setup_client()

    def _setup_client(self) -> bool:
        """Setup the ElevenLabs client and verify API access."""
        if self._is_setup_complete:
            return True

        try:
            self._client = ElevenLabs(api_key=self.api_key)

            # Test API access by getting voice info
            voice = self._client.voices.get(self.voice_id)
            logger.info(
                f"ElevenLabs setup successful. Using voice: {voice.name} ({voice.voice_id})"
            )
            self._is_setup_complete = True
            return True

        except Exception as e:
            logger.error(f"Error setting up ElevenLabs client: {e}")
            self._is_setup_complete = False
            return False

    def generate_speech(
        self, hook_event_name: str, event_data: Dict[str, Any]
    ) -> Optional[Path]:
        """
        Generate speech using ElevenLabs for the given hook event.

        Args:
            hook_event_name (str): Name of the hook event
            event_data (dict): Hook event data from Claude Code

        Returns:
            Path or None: Path to generated audio file if successful, None otherwise
        """
        if not self.is_available():
            logger.error("ElevenLabs provider not available")
            return None

        try:
            # Get text to speak for this event
            text = self._get_text_for_event(hook_event_name, event_data)
            if not text:
                logger.warning(f"No text found for event: {hook_event_name}")
                return None

            # Check if caching should be disabled for this event
            no_cache = event_data.get("_no_cache", False)

            # Generate cache key based on text, voice, model, and language
            cache_key = self._generate_cache_key(
                text, self.voice_id, self.model_id, self.language
            )
            cached_file = self.cache_dir / f"{cache_key}.mp3"

            # Return cached file if it exists, has valid content, and caching is enabled
            if self.cache_enabled and not no_cache and cached_file.exists():
                # Validate cache file has content (not empty/corrupted)
                if cached_file.stat().st_size > 0:
                    logger.info(f"Using cached ElevenLabs file: {cached_file.name}")
                    return cached_file
                else:
                    logger.warning(f"Removing corrupted cache file: {cached_file.name}")
                    cached_file.unlink()  # Remove corrupted empty file

            # Generate new TTS file
            logger.info(
                f"Generating ElevenLabs TTS for text: '{text}' with voice: {self.voice_id}"
                + (" (no-cache)" if no_cache else "")
            )

            # Generate audio using ElevenLabs
            audio = self._client.text_to_speech.convert(
                voice_id=self.voice_id, text=text, model_id=self.model_id
            )

            # Validate API response
            if not audio:
                logger.error("ElevenLabs API returned empty response")
                return None

            # Convert generator to list to validate content
            audio_chunks = list(audio)
            if not audio_chunks:
                logger.error("ElevenLabs API returned no audio data")
                return None

            # Calculate total size to ensure we have actual content
            total_size = sum(len(chunk) for chunk in audio_chunks)
            if total_size == 0:
                logger.error("ElevenLabs API returned empty audio data")
                return None

            logger.info(f"Received {total_size} bytes of audio data from ElevenLabs")

            if self.cache_enabled and not no_cache:
                # Save to cache with error handling
                try:
                    with open(cached_file, "wb") as f:
                        for chunk in audio_chunks:
                            f.write(chunk)

                    # Validate written file has content
                    if cached_file.stat().st_size > 0:
                        logger.info(
                            f"Saved ElevenLabs TTS to cache: {cached_file.name}"
                        )
                        return cached_file
                    else:
                        logger.error(
                            f"Cache file write resulted in empty file: {cached_file.name}"
                        )
                        cached_file.unlink()  # Remove empty file
                        return None

                except Exception as write_error:
                    logger.error(
                        f"Error writing cache file {cached_file.name}: {write_error}"
                    )
                    if cached_file.exists():
                        cached_file.unlink()  # Clean up partial file
                    return None
            else:
                # Save to temporary file
                import tempfile

                temp_file = Path(tempfile.mktemp(suffix=".mp3"))
                with open(temp_file, "wb") as f:
                    for chunk in audio_chunks:
                        f.write(chunk)
                logger.info(f"Generated temporary ElevenLabs TTS file: {temp_file}")
                return temp_file

        except Exception as e:
            logger.error(f"Error generating ElevenLabs speech: {e}")
            return None

    def cleanup(self) -> None:
        """Clean up temporary files if cache is disabled."""
        if not self.cache_enabled:
            # Could implement temp file cleanup here
            pass

    def _get_cache_dir(self) -> Path:
        """Get the cache directory for ElevenLabs files."""
        return Path(__file__).parent.parent.parent / ".tts_cache" / "elevenlabs"

    def _generate_cache_key(
        self, text: str, voice_id: str, model_id: str, language: str
    ) -> str:
        """
        Generate a cache key for the given parameters.

        Args:
            text (str): Text to generate key for
            voice_id (str): Voice ID used
            model_id (str): Model ID used
            language (str): Language code

        Returns:
            str: Cache key (MD5 hash)
        """
        cache_input = f"{text}_{voice_id}_{model_id}_{language}".encode("utf-8")
        return hashlib.md5(cache_input).hexdigest()
