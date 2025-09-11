# Configuration management for Claude Code hooks processing system
# Loads settings from environment variables with sensible defaults

import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def parse_bool_env(value: str, default: bool = False) -> bool:
    """Helper function to parse boolean environment variables consistently."""
    return value.lower() == "true" if value else default


@dataclass
class Config:
    """Configuration settings loaded from environment variables."""

    db_path: str = "events.db"
    max_retry_count: int = 3

    # TTS Configuration
    tts_providers: str = "prerecorded"
    tts_cache_enabled: bool = True
    tts_language: str = "en"

    # ElevenLabs Configuration
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # Rachel voice
    elevenlabs_model_id: str = "eleven_flash_v2_5"

    # OpenRouter Configuration
    openrouter_enabled: bool = False
    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4o-mini"
    openrouter_contextual_stop: bool = False
    openrouter_contextual_pretooluse: bool = False

    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables."""
        return cls(
            db_path=os.getenv("DB_PATH", "events.db"),
            max_retry_count=int(os.getenv("MAX_RETRY_COUNT", "3")),
            # TTS Configuration
            tts_providers=os.getenv("TTS_PROVIDERS", "prerecorded"),
            tts_cache_enabled=parse_bool_env(
                os.getenv("TTS_CACHE_ENABLED", "true"), True
            ),
            tts_language=os.getenv("CC_TTS_LANGUAGE")
            or os.getenv("TTS_LANGUAGE", "en"),
            # ElevenLabs Configuration
            elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY", ""),
            elevenlabs_voice_id=os.getenv("CC_ELEVENLABS_VOICE_ID")
            or os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"),
            elevenlabs_model_id=os.getenv("ELEVENLABS_MODEL_ID", "eleven_flash_v2_5"),
            # OpenRouter Configuration
            openrouter_enabled=parse_bool_env(os.getenv("OPENROUTER_ENABLED", "false")),
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
            openrouter_model=os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
            openrouter_contextual_stop=parse_bool_env(
                os.getenv("OPENROUTER_CONTEXTUAL_STOP", "false")
            ),
            openrouter_contextual_pretooluse=parse_bool_env(
                os.getenv("OPENROUTER_CONTEXTUAL_PRETOOLUSE", "false")
            ),
        )

    def get_tts_providers_list(self) -> list:
        """Parse TTS providers string into ordered list (leftmost = highest priority)."""
        if not self.tts_providers:
            return ["prerecorded"]  # Default fallback
        return [p.strip() for p in self.tts_providers.split(",") if p.strip()]


config = Config.from_env()


def initialize_openrouter_service_lazy():
    """Initialize OpenRouter service only when needed."""
    try:
        from utils.openrouter_service import initialize_openrouter_service

        initialize_openrouter_service(
            api_key=config.openrouter_api_key,
            model=config.openrouter_model,
            enabled=config.openrouter_enabled,
            contextual_stop=config.openrouter_contextual_stop,
            contextual_pretooluse=config.openrouter_contextual_pretooluse,
        )
        return True
    except ImportError:
        # OpenRouter service dependencies not available, service will be unavailable
        return False
