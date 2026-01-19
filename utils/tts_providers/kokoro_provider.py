"""
Kokoro Text-to-Speech provider for Claude Code hooks TTS system.

This provider generates high-quality speech using a local Kokoro server
running an OpenAI-compatible API, and caches the results for better performance.
"""

import hashlib
import os
from pathlib import Path
from typing import Dict, Any, Optional
from .base import TTSProvider
from utils.colored_logger import setup_logger

logger = setup_logger(__name__)

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    logger.warning("httpx not available. Install with: uv add httpx")


class KokoroProvider(TTSProvider):
    """TTS provider that uses a local Kokoro server for high-quality speech generation."""

    # Default Kokoro voices (American Female voices are most popular)
    DEFAULT_VOICE = "af_sky"

    # Available voice options for reference:
    # American Female: af_alloy, af_aoede, af_bella, af_heart, af_jadzia, af_jessica,
    #                  af_kore, af_nicole, af_nova, af_river, af_sarah, af_sky
    # American Male: am_adam, am_echo, am_eric, am_fenrir, am_liam, am_michael, am_onyx, am_puck
    # British Female: bf_alice, bf_emma, bf_lily
    # British Male: bm_daniel, bm_fable, bm_george, bm_lewis

    def __init__(
        self,
        language: str = "en",
        cache_enabled: bool = True,
        base_url: Optional[str] = None,
        voice: Optional[str] = None,
        model: str = "tts-1",
        response_format: str = "mp3",
    ):
        """
        Initialize the Kokoro provider.

        Args:
            language (str): Language code for TTS (default: "en")
            cache_enabled (bool): Whether to enable caching (default: True)
            base_url (str): Kokoro server base URL (defaults to KOKORO_BASE_URL env var or localhost:8880)
            voice (str): Voice to use (defaults to KOKORO_VOICE env var or af_sky)
            model (str): Model to use (default: "tts-1")
            response_format (str): Audio format (default: "mp3", options: mp3, opus, flac, wav, pcm)
        """
        self.language = language
        self.cache_enabled = cache_enabled
        self.base_url = base_url or os.getenv("KOKORO_BASE_URL", "http://127.0.0.1:8880/v1")
        self.voice = voice or os.getenv("KOKORO_VOICE", self.DEFAULT_VOICE)
        self.model = model
        self.response_format = response_format
        self.cache_dir = self._get_cache_dir()

        self._client = None
        self._is_setup_complete = False

        if cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "kokoro"

    def is_available(self) -> bool:
        """Check if Kokoro is available and can be used."""
        if not HTTPX_AVAILABLE:
            return False

        return self._setup_client()

    def _setup_client(self) -> bool:
        """Setup the HTTP client and verify Kokoro server is accessible."""
        if self._is_setup_complete:
            return True

        try:
            self._client = httpx.Client(timeout=30.0)

            # Test server connectivity by checking if it responds
            # Kokoro servers typically have a health endpoint or we can just try the models endpoint
            try:
                response = self._client.get(f"{self.base_url}/models")
                if response.status_code == 200:
                    logger.info(
                        f"Kokoro setup successful. Server at {self.base_url}, using voice: {self.voice}"
                    )
                    self._is_setup_complete = True
                    return True
            except httpx.RequestError:
                pass

            # Alternative: Try a minimal TTS request to verify
            try:
                response = self._client.post(
                    f"{self.base_url}/audio/speech",
                    json={
                        "model": self.model,
                        "input": "test",
                        "voice": self.voice,
                        "response_format": self.response_format,
                    },
                    timeout=10.0,
                )
                if response.status_code == 200:
                    logger.info(
                        f"Kokoro setup successful. Server at {self.base_url}, using voice: {self.voice}"
                    )
                    self._is_setup_complete = True
                    return True
            except httpx.RequestError as e:
                logger.warning(f"Kokoro server not responding at {self.base_url}: {e}")
                return False

            logger.warning(f"Kokoro server returned unexpected status at {self.base_url}")
            return False

        except Exception as e:
            logger.error(f"Error setting up Kokoro client: {e}")
            self._is_setup_complete = False
            return False

    def generate_speech(
        self, hook_event_name: str, event_data: Dict[str, Any]
    ) -> Optional[Path]:
        """
        Generate speech using Kokoro for the given hook event.

        Args:
            hook_event_name (str): Name of the hook event
            event_data (dict): Hook event data from Claude Code

        Returns:
            Path or None: Path to generated audio file if successful, None otherwise
        """
        if not self.is_available():
            logger.error("Kokoro provider not available")
            return None

        try:
            # Get text to speak for this event
            text = self._get_text_for_event(hook_event_name, event_data)
            if not text:
                logger.warning(f"No text found for event: {hook_event_name}")
                return None

            # Check if caching should be disabled for this event
            no_cache = event_data.get("_no_cache", False)

            # Generate cache key based on text, voice, model, and format
            cache_key = self._generate_cache_key(
                text, self.voice, self.model, self.response_format
            )
            file_ext = "ogg" if self.response_format == "opus" else self.response_format
            cached_file = self.cache_dir / f"{cache_key}.{file_ext}"

            # Return cached file if it exists, has valid content, and caching is enabled
            if self.cache_enabled and not no_cache and cached_file.exists():
                # Validate cache file has content (not empty/corrupted)
                if cached_file.stat().st_size > 0:
                    logger.info(f"Using cached Kokoro file: {cached_file.name}")
                    return cached_file
                else:
                    logger.warning(f"Removing corrupted cache file: {cached_file.name}")
                    cached_file.unlink()  # Remove corrupted empty file

            # Generate new TTS file
            logger.info(
                f"Generating Kokoro TTS for text: '{text[:50]}...' with voice: {self.voice}"
                + (" (no-cache)" if no_cache else "")
            )

            # Call Kokoro API
            response = self._client.post(
                f"{self.base_url}/audio/speech",
                json={
                    "model": self.model,
                    "input": text,
                    "voice": self.voice,
                    "response_format": self.response_format,
                },
                timeout=30.0,
            )

            if response.status_code != 200:
                logger.error(f"Kokoro API returned status {response.status_code}: {response.text}")
                return None

            audio_data = response.content
            if not audio_data:
                logger.error("Kokoro API returned empty response")
                return None

            logger.info(f"Received {len(audio_data)} bytes of audio data from Kokoro")

            if self.cache_enabled and not no_cache:
                # Save to cache with error handling
                try:
                    with open(cached_file, "wb") as f:
                        f.write(audio_data)

                    # Validate written file has content
                    if cached_file.stat().st_size > 0:
                        logger.info(
                            f"Saved Kokoro TTS to cache: {cached_file.name}"
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

                with tempfile.NamedTemporaryFile(suffix=f".{file_ext}", delete=False) as f:
                    f.write(audio_data)
                    temp_file = Path(f.name)
                logger.info(f"Generated temporary Kokoro TTS file: {temp_file}")
                return temp_file

        except Exception as e:
            logger.error(f"Error generating Kokoro speech: {e}")
            return None

    def cleanup(self) -> None:
        """Clean up resources."""
        if self._client:
            self._client.close()
            self._client = None
        self._is_setup_complete = False

    def _get_cache_dir(self) -> Path:
        """Get the cache directory for Kokoro files."""
        return Path(__file__).parent.parent.parent / ".tts_cache" / "kokoro"

    def _generate_cache_key(
        self, text: str, voice: str, model: str, response_format: str
    ) -> str:
        """
        Generate a cache key for the given parameters.

        Args:
            text (str): Text to generate key for
            voice (str): Voice used
            model (str): Model used
            response_format (str): Audio format

        Returns:
            str: Cache key (MD5 hash)
        """
        cache_input = f"{text}_{voice}_{model}_{response_format}".encode("utf-8")
        return hashlib.md5(cache_input).hexdigest()
