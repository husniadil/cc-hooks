# Configuration management for Claude Code hooks processing system
# Loads settings from environment variables with sensible defaults

import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class Config:
    """Configuration settings loaded from environment variables."""

    db_path: str = "events.db"
    host: str = "0.0.0.0"
    port: int = 12345
    max_retry_count: int = 3

    # TTS Configuration
    tts_providers: str = "prerecorded"
    tts_cache_enabled: bool = True
    tts_language: str = "en"

    # ElevenLabs Configuration
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # Rachel voice
    elevenlabs_model_id: str = "eleven_flash_v2_5"

    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables."""
        return cls(
            db_path=os.getenv("DB_PATH", "events.db"),
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "12345")),
            max_retry_count=int(os.getenv("MAX_RETRY_COUNT", "3")),
            # TTS Configuration
            tts_providers=os.getenv("TTS_PROVIDERS", "prerecorded"),
            tts_cache_enabled=os.getenv("TTS_CACHE_ENABLED", "true").lower() == "true",
            tts_language=os.getenv("TTS_LANGUAGE", "en"),
            # ElevenLabs Configuration
            elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY", ""),
            elevenlabs_voice_id=os.getenv(
                "ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"
            ),
            elevenlabs_model_id=os.getenv("ELEVENLABS_MODEL_ID", "eleven_flash_v2_5"),
        )

    def get_tts_providers_list(self) -> list:
        """Parse TTS providers string into ordered list (leftmost = highest priority)."""
        if not self.tts_providers:
            return ["prerecorded"]  # Default fallback
        return [p.strip() for p in self.tts_providers.split(",") if p.strip()]


config = Config.from_env()
