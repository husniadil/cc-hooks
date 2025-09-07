"""
TTS Manager for Claude Code hooks system.

This module provides a unified interface for text-to-speech functionality,
coordinating between different TTS providers and handling fallbacks.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from .tts_providers import create_provider

logger = logging.getLogger(__name__)


class TTSManager:
    """
    Manager for TTS providers with fallback support.

    Coordinates between multiple TTS providers, providing a unified interface
    and handling fallbacks when primary providers fail.
    """

    def __init__(self, providers: List[str] = None, **provider_kwargs):
        """
        Initialize the TTS manager with ordered provider list.

        Args:
            providers (list): List of provider names in order of preference (leftmost = highest priority)
            **provider_kwargs: Additional arguments for provider initialization
        """
        self.provider_kwargs = provider_kwargs
        self.providers = {}

        # Set up provider chain
        if providers is None or not providers:
            providers = ["prerecorded"]  # Default fallback

        # Remove duplicates while preserving order
        seen = set()
        self.provider_chain = []
        for provider in providers:
            if provider not in seen:
                seen.add(provider)
                self.provider_chain.append(provider)

        # Initialize providers
        self._initialize_providers()

    def get_sound(
        self, hook_event_name: str, event_data: Dict[str, Any]
    ) -> Optional[Path]:
        """
        Get audio file for the given hook event.

        Tries providers in order of preference until one succeeds.

        Args:
            hook_event_name (str): Name of the hook event
            event_data (dict): Hook event data from Claude Code

        Returns:
            Path or None: Path to audio file if successful, None otherwise
        """
        for provider_name in self.provider_chain:
            provider = self.providers.get(provider_name)

            if not provider:
                logger.warning(f"Provider '{provider_name}' not available, skipping")
                continue

            try:
                sound_path = provider.generate_speech(hook_event_name, event_data)

                if sound_path and sound_path.exists():
                    logger.info(
                        f"Successfully got sound from provider: {provider_name}"
                    )
                    return sound_path
                else:
                    logger.info(
                        f"Provider '{provider_name}' returned no sound for {hook_event_name}"
                    )

            except Exception as e:
                logger.error(f"Error from provider '{provider_name}': {e}")
                continue

        logger.warning(f"No provider could generate sound for {hook_event_name}")
        return None

    def get_primary_provider_name(self) -> str:
        """Get the name of the primary (first available) provider."""
        # Return first available provider, not just first in chain
        for provider_name in self.provider_chain:
            if (
                provider_name in self.providers
                and self.providers[provider_name].is_available()
            ):
                return provider_name

        # Fallback to first in chain if none are available
        return self.provider_chain[0] if self.provider_chain else "none"

    def get_available_providers(self) -> List[str]:
        """Get list of available provider names."""
        return list(self.providers.keys())

    def cleanup(self) -> None:
        """Clean up all providers."""
        for provider in self.providers.values():
            try:
                provider.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up provider: {e}")

    def _initialize_providers(self) -> None:
        """Initialize all providers in the chain."""
        for provider_name in self.provider_chain:
            try:
                provider = create_provider(provider_name, **self.provider_kwargs)

                if provider:
                    self.providers[provider_name] = provider
                    logger.info(f"Initialized TTS provider: {provider_name}")
                else:
                    logger.warning(
                        f"Failed to initialize TTS provider: {provider_name}"
                    )

            except Exception as e:
                logger.error(f"Error initializing provider '{provider_name}': {e}")

    def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status information for all providers.

        Returns:
            dict: Status information for each provider
        """
        status = {}

        for provider_name in self.provider_chain:
            provider = self.providers.get(provider_name)

            if provider:
                status[provider_name] = {
                    "available": provider.is_available(),
                    "provider_name": provider.provider_name,
                    "initialized": True,
                }
            else:
                status[provider_name] = {
                    "available": False,
                    "provider_name": provider_name,
                    "initialized": False,
                }

        return status


# Global TTS manager instance (will be initialized by config)
tts_manager: Optional[TTSManager] = None


def get_tts_manager() -> Optional[TTSManager]:
    """Get the global TTS manager instance."""
    return tts_manager


def initialize_tts_manager(
    providers: List[str] = None, **provider_kwargs
) -> TTSManager:
    """
    Initialize the global TTS manager with ordered provider list.

    Args:
        providers (list): List of provider names in order of preference
        **provider_kwargs: Additional arguments for provider initialization

    Returns:
        TTSManager: The initialized TTS manager
    """
    global tts_manager

    if tts_manager:
        tts_manager.cleanup()

    tts_manager = TTSManager(providers=providers, **provider_kwargs)

    logger.info(
        f"Initialized global TTS manager with providers: {providers or ['prerecorded']} (primary: {tts_manager.get_primary_provider_name()})"
    )
    return tts_manager
