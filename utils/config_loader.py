"""Config file loader - loads YAML configuration from ~/.claude/.cc-hooks/config.yaml."""

import os
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


# Mapping from YAML keys to environment variable names
CONFIG_TO_ENV_MAP = {
    # Audio settings
    "audio.providers": "CC_TTS_PROVIDERS",
    "audio.language": "CC_TTS_LANGUAGE",
    "audio.cache_enabled": "CC_TTS_CACHE_ENABLED",
    # ElevenLabs
    "elevenlabs.voice_id": "CC_ELEVENLABS_VOICE_ID",
    "elevenlabs.model_id": "CC_ELEVENLABS_MODEL_ID",
    # Kokoro (local TTS server)
    "kokoro.base_url": "KOKORO_BASE_URL",
    "kokoro.voice": "KOKORO_VOICE",
    "kokoro.model": "KOKORO_MODEL",
    "kokoro.response_format": "KOKORO_RESPONSE_FORMAT",
    # Silent modes
    "silent.announcements": "CC_SILENT_ANNOUNCEMENTS",
    "silent.effects": "CC_SILENT_EFFECTS",
    # OpenRouter
    "openrouter.enabled": "CC_OPENROUTER_ENABLED",
    "openrouter.model": "CC_OPENROUTER_MODEL",
    "openrouter.contextual_stop": "CC_OPENROUTER_CONTEXTUAL_STOP",
    "openrouter.contextual_pretooluse": "CC_OPENROUTER_CONTEXTUAL_PRETOOLUSE",
}


def flatten_dict(
    d: Dict[str, Any], parent_key: str = "", sep: str = "."
) -> Dict[str, Any]:
    """
    Flatten nested dictionary into dot-notation keys.

    Example:
        {"audio": {"language": "id"}} → {"audio.language": "id"}
    """
    items: list[tuple[str, Any]] = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def load_config(config_path: Optional[Path] = None) -> Dict[str, str]:
    """
    Load YAML config file and return flattened key-value pairs.

    Args:
        config_path: Path to config file. If None, uses default location.

    Returns:
        Dictionary of flattened config values
    """
    if yaml is None:
        return {}

    if config_path is None:
        config_path = Path.home() / ".claude/.cc-hooks/config.yaml"

    if not config_path.exists():
        return {}

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        if not config:
            return {}

        # Flatten nested structure
        return flatten_dict(config)

    except Exception:
        # Silently fail - config is optional
        return {}


def apply_config_to_env(config: Optional[Dict[str, Any]] = None) -> None:
    """
    Load config and set environment variables (only if not already set).

    Args:
        config: Pre-loaded config dict. If None, loads from default location.
    """
    if config is None:
        config = load_config()

    if not config:
        return

    # Apply config values to environment
    for config_key, env_var in CONFIG_TO_ENV_MAP.items():
        if config_key in config and env_var not in os.environ:
            value = config[config_key]

            # Convert boolean to string
            if isinstance(value, bool):
                value = "true" if value else "false"
            else:
                value = str(value)

            os.environ[env_var] = value


def get_config_value(key: str, default: Any = None) -> Any:
    """
    Get a config value by key (dot notation).

    Priority: Environment variable > Config file > Default

    Args:
        key: Config key in dot notation (e.g., "audio.language")
        default: Default value if not found

    Returns:
        Config value
    """
    # Check environment variable first
    env_var = CONFIG_TO_ENV_MAP.get(key)
    if env_var and env_var in os.environ:
        return os.environ[env_var]

    # Check config file
    config = load_config()
    return config.get(key, default)


def create_example_config(output_path: Optional[Path] = None) -> None:
    """
    Create an example config file with all available settings.

    Args:
        output_path: Where to write the example. If None, uses default location.
    """
    if output_path is None:
        output_path = Path.home() / ".claude/.cc-hooks/config.yaml"

    example_config = """# cc-hooks Configuration
# This file provides default settings for audio feedback and AI features.
# Priority: CLI flags > Environment variables > This file > Defaults
#
# For terminal usage: CLI flags override these settings
#   Example: cld --language=es (uses Spanish, ignores config)
#
# For editors (Zed, etc.): This file provides the settings
#   Example: Edit this file once, Zed uses these settings automatically

# Audio Settings
audio:
  # TTS provider chain (comma-separated, left to right priority)
  # Options: prerecorded, gtts, elevenlabs, kokoro
  providers: prerecorded

  # Language code for TTS (ISO 639-1)
  # Examples: en, id, es, fr, de, ja, zh
  language: en

  # Enable TTS audio caching (faster, uses disk space)
  cache_enabled: true

# ElevenLabs Settings (requires API key in .env)
elevenlabs:
  # Voice ID (see https://elevenlabs.io/voice-library)
  voice_id: 21m00Tcm4TlvDq8ikWAM  # Rachel (default)

  # Model ID
  # Options: eleven_flash_v2_5, eleven_turbo_v2_5, eleven_multilingual_v2
  model_id: eleven_flash_v2_5

# Kokoro Settings (local TTS server with OpenAI-compatible API)
kokoro:
  # Base URL for Kokoro server (default: http://127.0.0.1:8880/v1)
  base_url: http://127.0.0.1:8880/v1

  # Voice to use (see https://github.com/remsky/Kokoro-FastAPI for full list)
  # American Female: af_sky, af_bella, af_sarah, af_nicole, af_nova, etc.
  # American Male: am_adam, am_echo, am_michael, am_onyx, etc.
  # British Female: bf_alice, bf_emma, bf_lily
  # British Male: bm_daniel, bm_george, bm_lewis
  voice: af_sky

  # Model (default: tts-1)
  model: tts-1

  # Audio format: mp3, opus, flac, wav, pcm (default: mp3)
  response_format: mp3

# Silent Modes
silent:
  # Disable TTS announcements (keeps sound effects)
  announcements: false

  # Disable sound effects (keeps TTS)
  effects: false

# OpenRouter (AI Features - requires API key in .env)
openrouter:
  # Enable OpenRouter integration
  enabled: false

  # Model to use for contextual messages
  # Examples: openai/gpt-4o-mini, google/gemini-2.5-flash-lite, anthropic/claude-haiku-4.5
  model: openai/gpt-4o-mini

  # Generate contextual completion messages on Stop event
  contextual_stop: false

  # Generate contextual messages before tool use (requires contextual_stop=true)
  contextual_pretooluse: false
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(example_config)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--create-example":
        create_example_config()
        print(
            f"Created example config at: {Path.home() / '.claude/.cc-hooks/config.yaml'}"
        )
    else:
        # Test loading
        config = load_config()
        if config:
            print("Loaded config:")
            for key, value in config.items():
                env_var = CONFIG_TO_ENV_MAP.get(key, "N/A")
                print(f"  {key} = {value} ({env_var})")
        else:
            print("No config file found or YAML not available")
