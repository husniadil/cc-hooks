# Configuration management for Claude Code hooks processing system
# Loads settings from environment variables with sensible defaults

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv, dotenv_values
from utils.constants import ProcessingConstants, PathConstants

# Project directory - supports both plugin and standalone modes
# Plugin mode: Use CLAUDE_PLUGIN_ROOT if available
# Standalone mode: Use script directory
PROJECT_DIR = Path(os.getenv("CLAUDE_PLUGIN_ROOT", Path(__file__).parent))

# Load .env file from plugin directory first (if in plugin mode), then from CWD (standalone mode)
if os.getenv("CLAUDE_PLUGIN_ROOT"):
    load_dotenv(PROJECT_DIR / ".env")
load_dotenv()


def parse_bool_env(value: str, default: bool = False) -> bool:
    """Parse boolean environment variable. Case-insensitive, accepts true/yes/on/1."""
    if not value:
        return default
    return value.lower() in ("true", "yes", "on", "1")


def resolve_api_key(env_var_name: str) -> str:
    """Resolve API key with priority: .env file > global env > empty string.

    Args:
        env_var_name: Name of the environment variable (e.g., "OPENROUTER_API_KEY")

    Returns:
        Resolved API key string (may be empty if not configured)
    """
    env_file_path = PROJECT_DIR / ".env"
    dotenv_dict = dotenv_values(env_file_path) if env_file_path.exists() else {}
    dotenv_value = (dotenv_dict.get(env_var_name) or "").strip()
    current_value = os.getenv(env_var_name, "").strip()

    return dotenv_value or current_value


def get_env_with_fallback(base_name: str, default: str = "") -> str:
    """Get environment variable with CC_ prefix priority fallback.

    Priority: CC_<base_name> > <base_name> > default
    """
    return os.getenv(f"CC_{base_name}") or os.getenv(base_name) or default


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
        db_path = str(PathConstants.DATABASE_PATH)
        max_retry_count = ProcessingConstants.MAX_RETRY_COUNT

        return cls(
            db_path=db_path,
            max_retry_count=max_retry_count,
            tts_providers=get_env_with_fallback("TTS_PROVIDERS", "prerecorded"),
            tts_cache_enabled=parse_bool_env(
                get_env_with_fallback("TTS_CACHE_ENABLED", "true"), True
            ),
            tts_language=get_env_with_fallback("TTS_LANGUAGE", "en"),
            elevenlabs_api_key=resolve_api_key("ELEVENLABS_API_KEY"),
            elevenlabs_voice_id=get_env_with_fallback(
                "ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"
            ),
            elevenlabs_model_id=get_env_with_fallback(
                "ELEVENLABS_MODEL_ID", "eleven_flash_v2_5"
            ),
            openrouter_enabled=parse_bool_env(
                get_env_with_fallback("OPENROUTER_ENABLED", "false")
            ),
            openrouter_api_key=resolve_api_key("OPENROUTER_API_KEY"),
            openrouter_model=get_env_with_fallback(
                "OPENROUTER_MODEL", "openai/gpt-4o-mini"
            ),
            openrouter_contextual_stop=parse_bool_env(
                get_env_with_fallback("OPENROUTER_CONTEXTUAL_STOP", "false")
            ),
            openrouter_contextual_pretooluse=parse_bool_env(
                get_env_with_fallback("OPENROUTER_CONTEXTUAL_PRETOOLUSE", "false")
            ),
        )

    def get_tts_providers_list(self) -> list:
        """Parse TTS providers string into ordered list (leftmost = highest priority)."""
        if not self.tts_providers:
            return ["prerecorded"]  # Default fallback
        return [p.strip() for p in self.tts_providers.split(",") if p.strip()]


config = Config.from_env()


def reload_config() -> None:
    """Reload config from environment variables.

    Call this after apply_config_to_env() to pick up CC_* variables
    that were set from config.yaml.
    """
    global config
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
