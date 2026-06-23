"""60db TTS provider with caching support.

Uses the 60db non-streaming REST API (POST /tts-synthesize), which returns
base64-encoded audio inside a JSON envelope. This mirrors the file-based
behaviour of the other providers: a complete .mp3 is produced, cached, and
played as a whole file (no streaming).
"""

import base64
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional

import requests

from .base import TTSProvider
from utils.colored_logger import setup_logger

logger = setup_logger(__name__)

# 60db API (see https://docs.60db.ai/api-reference/tts/text-to-speech)
SIXTYDB_BASE_URL = "https://api.60db.ai"
SIXTYDB_SYNTHESIZE_ENDPOINT = f"{SIXTYDB_BASE_URL}/tts-synthesize"
SIXTYDB_VOICES_ENDPOINT = f"{SIXTYDB_BASE_URL}/myvoices"
SIXTYDB_MAX_TEXT_LENGTH = 5000  # API hard limit per request
SIXTYDB_REQUEST_TIMEOUT = 30  # seconds


class SixtyDBProvider(TTSProvider):
    """TTS provider that uses the 60db REST API for speech generation."""

    def __init__(
        self,
        language: str = "en",
        cache_enabled: bool = True,
        api_key: Optional[str] = None,
        voice_id: Optional[str] = None,
    ):
        """
        Initialize the 60db provider.

        Args:
            language (str): Language code for TTS (default: "en"), used only in the cache key
            cache_enabled (bool): Whether to enable caching (default: True)
            api_key (str): 60db API key (defaults to SIXTYDB_API_KEY env var)
            voice_id (str): Voice ID to use (empty -> 60db system default voice)
        """
        self.language = language
        self.cache_enabled = cache_enabled
        self.api_key = api_key or ""
        self.voice_id = voice_id or ""  # empty -> let 60db pick its system default
        self.cache_dir = self._get_cache_dir()

        self._is_setup_complete = False

        if cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "60db"

    def is_available(self) -> bool:
        """Check if 60db is available and can be used."""
        if not self.api_key:
            logger.warning(
                "60db API key not provided. Set SIXTYDB_API_KEY environment variable."
            )
            return False

        return self._verify_access()

    def _verify_access(self) -> bool:
        """Verify API access once by hitting the voices endpoint."""
        if self._is_setup_complete:
            return True

        try:
            response = requests.get(
                SIXTYDB_VOICES_ENDPOINT,
                headers=self._auth_headers(),
                timeout=SIXTYDB_REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            logger.info("60db setup successful. API key verified.")
            self._is_setup_complete = True
            return True

        except Exception as e:
            logger.error(f"Error verifying 60db API access: {e}")
            self._is_setup_complete = False
            return False

    def _auth_headers(self) -> Dict[str, str]:
        """Build the Bearer auth + JSON headers for 60db requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def generate_speech(
        self, hook_event_name: str, event_data: Dict[str, Any]
    ) -> Optional[Path]:
        """
        Generate speech using 60db for the given hook event.

        Args:
            hook_event_name (str): Name of the hook event
            event_data (dict): Hook event data from Claude Code

        Returns:
            Path or None: Path to generated audio file if successful, None otherwise
        """
        if not self.is_available():
            logger.error("60db provider not available")
            return None

        try:
            # Get text to speak for this event
            text = self._get_text_for_event(hook_event_name, event_data)
            if not text:
                logger.warning(f"No text found for event: {hook_event_name}")
                return None

            if len(text) > SIXTYDB_MAX_TEXT_LENGTH:
                logger.warning(
                    f"Text exceeds 60db limit of {SIXTYDB_MAX_TEXT_LENGTH} chars, truncating"
                )
                text = text[:SIXTYDB_MAX_TEXT_LENGTH]

            # Check if caching should be disabled for this event
            no_cache = event_data.get("_no_cache", False)

            # Generate cache key based on text, voice, and language
            cache_key = self._generate_cache_key(text, self.voice_id, self.language)
            cached_file = self.cache_dir / f"{cache_key}.mp3"

            # Return cached file if it exists, has valid content, and caching is enabled
            if self.cache_enabled and not no_cache and cached_file.exists():
                if cached_file.stat().st_size > 0:
                    logger.info(f"Using cached 60db file: {cached_file.name}")
                    return cached_file
                else:
                    logger.warning(f"Removing corrupted cache file: {cached_file.name}")
                    cached_file.unlink()  # Remove corrupted empty file

            # Generate new TTS file
            logger.info(
                f"Generating 60db TTS for text: '{text}' with voice: {self.voice_id or 'system default'}"
                + (" (no-cache)" if no_cache else "")
            )

            audio_bytes = self._synthesize(text)
            if not audio_bytes:
                return None  # error already logged in _synthesize

            logger.info(f"Received {len(audio_bytes)} bytes of audio data from 60db")

            if self.cache_enabled and not no_cache:
                # Save to cache with error handling
                try:
                    with open(cached_file, "wb") as f:
                        f.write(audio_bytes)

                    if cached_file.stat().st_size > 0:
                        logger.info(f"Saved 60db TTS to cache: {cached_file.name}")
                        return cached_file
                    else:
                        logger.error(
                            f"Cache file write resulted in empty file: {cached_file.name}"
                        )
                        cached_file.unlink()
                        return None

                except Exception as write_error:
                    logger.error(
                        f"Error writing cache file {cached_file.name}: {write_error}"
                    )
                    if cached_file.exists():
                        cached_file.unlink()
                    return None
            else:
                # Save to temporary file
                import tempfile

                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                    tmp.write(audio_bytes)
                    temp_file = Path(tmp.name)
                logger.info(f"Generated temporary 60db TTS file: {temp_file}")
                return temp_file

        except Exception as e:
            logger.error(f"Error generating 60db speech: {e}")
            return None

    def _synthesize(self, text: str) -> Optional[bytes]:
        """Call the 60db synthesize endpoint and return decoded audio bytes."""
        payload: Dict[str, Any] = {"text": text, "output_format": "mp3"}
        if self.voice_id:
            payload["voice_id"] = self.voice_id

        try:
            response = requests.post(
                SIXTYDB_SYNTHESIZE_ENDPOINT,
                headers=self._auth_headers(),
                json=payload,
                timeout=SIXTYDB_REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            logger.error(f"60db synthesize request failed: {e}")
            return None

        if not data.get("success", False):
            logger.error(f"60db API error: {data.get('message', 'unknown error')}")
            return None

        audio_base64 = data.get("audio_base64")
        if not audio_base64:
            logger.error("60db API returned no audio_base64 data")
            return None

        try:
            audio_bytes = base64.b64decode(audio_base64)
        except Exception as e:
            logger.error(f"Failed to decode 60db audio_base64: {e}")
            return None

        if not audio_bytes:
            logger.error("60db API returned empty audio data")
            return None

        return audio_bytes

    def cleanup(self) -> None:
        """Clean up temporary files if cache is disabled."""
        if not self.cache_enabled:
            # Could implement temp file cleanup here
            pass

    def _get_cache_dir(self) -> Path:
        """Get the cache directory for 60db files (shared data dir)."""
        from utils.constants import PathConstants

        return PathConstants.TTS_CACHE_SIXTYDB_DIR

    def _generate_cache_key(self, text: str, voice_id: str, language: str) -> str:
        """
        Generate a cache key for the given parameters.

        Args:
            text (str): Text to generate key for
            voice_id (str): Voice ID used
            language (str): Language code

        Returns:
            str: Cache key (MD5 hash)
        """
        cache_input = f"{text}_{voice_id}_60db_{language}".encode("utf-8")
        return hashlib.md5(cache_input).hexdigest()
