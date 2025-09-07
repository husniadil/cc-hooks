"""
TTS Providers for Claude Code hooks system.

This package provides a unified interface for different text-to-speech providers,
including pre-recorded sounds, Google TTS, and future providers like ElevenLabs.
"""

from .base import TTSProvider
from .factory import create_provider

__all__ = ["TTSProvider", "create_provider"]
