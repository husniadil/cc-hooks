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

# Shared data directory for persistence across plugin updates
# This directory stores database, logs, and other persistent data
SHARED_DATA_DIR = PathConstants.SHARED_DATA_DIR

# Load .env file from plugin directory first (if in plugin mode)
# Then load from current directory (standalone mode)
# DON'T override existing env vars (global env takes priority temporarily)
if os.getenv("CLAUDE_PLUGIN_ROOT"):
    load_dotenv(PROJECT_DIR / ".env")
load_dotenv()


def parse_bool_env(value: str, default: bool = False) -> bool:
    """
    Helper function to parse boolean environment variables consistently.

    Accepts multiple formats for better UX:
    - "true", "yes", "on", "1" → True
    - "false", "no", "off", "0" → False
    - Empty/None → default value

    Case-insensitive.
    """
    if not value:
        return default
    return value.lower() in ("true", "yes", "on", "1")


def resolve_api_key(env_var_name: str) -> str:
    """Resolve API key with priority: .env file (if not empty) > global env > empty string.

    Priority rules:
    1. If both .env and global env exist -> use .env
    2. If only global env exists (.env missing or empty) -> use global env
    3. If .env exists but global env is empty -> use .env
    4. If both are empty -> return empty string

    Args:
        env_var_name: Name of the environment variable (e.g., "OPENROUTER_API_KEY")

    Returns:
        Resolved API key string (may be empty if not configured)
    """
    # Read .env file directly without loading into os.environ
    env_file_path = PROJECT_DIR / ".env"
    dotenv_dict = dotenv_values(env_file_path) if env_file_path.exists() else {}

    # Get value from .env file (parsed but not loaded)
    dotenv_value = dotenv_dict.get(env_var_name, "").strip()

    # Get value from current environment (includes both global env and loaded .env)
    # Since we use load_dotenv() without override, global env takes priority in os.environ
    # We check if this came from global env or .env
    current_value = os.getenv(env_var_name, "").strip()

    # Priority logic:
    # 1. If .env has non-empty value -> use it (highest priority)
    if dotenv_value:
        return dotenv_value

    # 2. If global env has value -> use it (fallback)
    if current_value:
        return current_value

    # 3. Both empty -> return empty string
    return ""


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
        """Create configuration from environment variables.

        Note: CC_* environment variables are used by claude.sh to pass CLI arguments
        to SessionStart hooks. They are then stored in DB by hooks.py.
        .env file provides global defaults for server-wide settings.

        API Key Resolution Priority (for ELEVENLABS_API_KEY and OPENROUTER_API_KEY):
        1. If both .env and global env exist -> use .env (highest priority)
        2. If only global env exists (.env missing or empty) -> use global env
        3. If .env exists but global env is empty -> use .env
        4. If both are empty -> no API key (features disabled)
        """
        # Database path and retry count are hardcoded in constants (no configuration needed)
        # This ensures consistency and prevents misconfiguration
        db_path = str(PathConstants.DATABASE_PATH)
        max_retry_count = ProcessingConstants.MAX_RETRY_COUNT

        return cls(
            db_path=db_path,
            max_retry_count=max_retry_count,
            # TTS Configuration (global defaults from .env)
            tts_providers=os.getenv("TTS_PROVIDERS", "prerecorded"),
            tts_cache_enabled=parse_bool_env(
                os.getenv("TTS_CACHE_ENABLED", "true"), True
            ),
            tts_language=os.getenv("TTS_LANGUAGE", "en"),
            # ElevenLabs Configuration
            elevenlabs_api_key=resolve_api_key("ELEVENLABS_API_KEY"),
            elevenlabs_voice_id=os.getenv(
                "ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"
            ),
            elevenlabs_model_id=os.getenv("ELEVENLABS_MODEL_ID", "eleven_flash_v2_5"),
            # OpenRouter Configuration
            openrouter_enabled=parse_bool_env(os.getenv("OPENROUTER_ENABLED", "false")),
            openrouter_api_key=resolve_api_key("OPENROUTER_API_KEY"),
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
