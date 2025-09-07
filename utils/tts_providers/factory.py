"""
Factory for creating TTS providers based on configuration.

This module handles instantiation of different TTS providers
and provides a clean interface for provider creation.
"""

import logging
from typing import Dict, Type, Optional
from .base import TTSProvider
from .prerecorded_provider import PrerecordedProvider
from .gtts_provider import GTTSProvider
from .elevenlabs_provider import ElevenLabsProvider

logger = logging.getLogger(__name__)

# Registry of available providers
PROVIDER_REGISTRY: Dict[str, Type[TTSProvider]] = {
    "prerecorded": PrerecordedProvider,
    "gtts": GTTSProvider,
    "elevenlabs": ElevenLabsProvider,
}

# Provider configuration mapping (what parameters each provider supports)
PROVIDER_CONFIGS = {
    "prerecorded": {
        "supports_language": False,
        "supports_cache": False,
    },
    "gtts": {
        "supports_language": True,
        "supports_cache": True,
    },
    "elevenlabs": {
        "supports_language": True,
        "supports_cache": True,
        "supports_api_key": True,
        "supports_voice_id": True,
        "supports_model_id": True,
    },
}


def create_provider(provider_name: str, **kwargs) -> Optional[TTSProvider]:
    """
    Create a TTS provider instance with smart parameter passing.

    Only passes parameters that the provider actually supports.

    Args:
        provider_name (str): Name of the provider to create
        **kwargs: All available parameters (will be filtered by provider config)

    Returns:
        TTSProvider or None: Provider instance if successful, None otherwise
    """
    try:
        if provider_name not in PROVIDER_REGISTRY:
            logger.error(f"Unknown TTS provider: {provider_name}")
            logger.info(f"Available providers: {list(PROVIDER_REGISTRY.keys())}")
            return None

        # Get provider configuration
        provider_config = PROVIDER_CONFIGS.get(provider_name, {})
        provider_class = PROVIDER_REGISTRY[provider_name]

        # Filter kwargs based on what this provider supports
        filtered_kwargs = {}

        # Add language parameter if provider supports it
        if provider_config.get("supports_language", False) and "language" in kwargs:
            filtered_kwargs["language"] = kwargs["language"]

        # Add cache_enabled parameter if provider supports it
        if provider_config.get("supports_cache", False) and "cache_enabled" in kwargs:
            filtered_kwargs["cache_enabled"] = kwargs["cache_enabled"]

        # Add ElevenLabs-specific parameters
        if provider_config.get("supports_api_key", False) and "api_key" in kwargs:
            filtered_kwargs["api_key"] = kwargs["api_key"]

        if provider_config.get("supports_voice_id", False) and "voice_id" in kwargs:
            filtered_kwargs["voice_id"] = kwargs["voice_id"]

        if provider_config.get("supports_model_id", False) and "model_id" in kwargs:
            filtered_kwargs["model_id"] = kwargs["model_id"]

        # Create provider with filtered parameters
        provider = provider_class(**filtered_kwargs)

        # Check if provider is available
        if not provider.is_available():
            logger.error(f"TTS provider '{provider_name}' is not available")
            return None

        logger.info(f"Successfully created TTS provider: {provider_name}")
        return provider

    except Exception as e:
        logger.error(f"Error creating TTS provider '{provider_name}': {e}")
        return None


def get_available_providers() -> list:
    """
    Get list of available TTS provider names.

    Returns:
        list: List of provider names that can be instantiated
    """
    available = []

    for provider_name, provider_class in PROVIDER_REGISTRY.items():
        try:
            # Test if provider can be instantiated and is available
            provider = provider_class()
            if provider.is_available():
                available.append(provider_name)
        except Exception:
            # Provider not available (e.g., missing dependencies)
            continue

    return available


def register_provider(name: str, provider_class: Type[TTSProvider]) -> None:
    """
    Register a custom TTS provider.

    Args:
        name (str): Provider name
        provider_class (Type[TTSProvider]): Provider class that implements TTSProvider
    """
    if not issubclass(provider_class, TTSProvider):
        raise ValueError(f"Provider class must inherit from TTSProvider")

    PROVIDER_REGISTRY[name] = provider_class
    logger.info(f"Registered custom TTS provider: {name}")
