#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "gtts",
#   "elevenlabs",
# ]
# ///
"""
TTS Announcer for Claude Code hooks with unified provider system.

This module provides context-aware sound announcements using a flexible
TTS provider architecture that supports pre-recorded sounds, Google TTS,
and future providers like ElevenLabs.
"""

import logging
from typing import Dict, Optional, Any
from utils.sound_player import play_sound
from utils.tts_manager import get_tts_manager, initialize_tts_manager
from utils.tts_providers.mappings import get_audio_description

# Configure logging
logger = logging.getLogger(__name__)


def initialize_tts(providers: Optional[list] = None, **kwargs):
    """
    Initialize the TTS system with ordered provider list.

    Args:
        providers (list): List of provider names in order of preference
        **kwargs: Additional arguments for provider initialization
    """
    try:
        return initialize_tts_manager(providers=providers, **kwargs)
    except Exception as e:
        logger.error(f"Error initializing TTS system: {e}")
        return None


def announce_event(
    hook_event_name: str, event_data: Dict[str, Any], volume: float = 0.5
) -> bool:
    """
    Play appropriate announcement sound for a hook event using TTS providers.

    Args:
        hook_event_name (str): Name of the hook event
        event_data (dict): Hook event data from Claude Code
        volume (float): Volume level 0.0-1.0 (default: 0.5)

    Returns:
        bool: True if sound played successfully, False otherwise
    """
    try:
        # Get TTS manager
        manager = get_tts_manager()
        if not manager:
            logger.error("TTS manager not initialized")
            return False

        # Get appropriate sound for this event
        sound_path = manager.get_sound(hook_event_name, event_data)

        if not sound_path:
            logger.info(f"No sound available for {hook_event_name}")
            return False

        # Play the sound using existing sound player
        success = play_sound(str(sound_path), volume)

        if success:
            logger.info(f"Announced {hook_event_name} with {sound_path.name}")
        else:
            logger.warning(
                f"Failed to announce {hook_event_name} with {sound_path.name}"
            )

        return success

    except Exception as e:
        logger.error(f"Error announcing event {hook_event_name}: {e}")
        return False


def get_tts_status() -> Dict[str, Any]:
    """
    Get status information about the TTS system.

    Returns:
        dict: Status information including provider status and configuration
    """
    try:
        manager = get_tts_manager()
        if not manager:
            return {"error": "TTS manager not initialized"}

        return {
            "primary_provider": manager.get_primary_provider_name(),
            "available_providers": manager.get_available_providers(),
            "provider_status": manager.get_provider_status(),
        }
    except Exception as e:
        logger.error(f"Error getting TTS status: {e}")
        return {"error": str(e)}


def main():
    """
    Command-line interface for TTS announcer.

    Usage:
    - ./tts_announcer.py --list                    # List TTS status and providers
    - ./tts_announcer.py SessionStart startup      # Test announcement
    - ./tts_announcer.py SessionStart              # Test with no source
    - ./tts_announcer.py --provider gtts SessionStart  # Test with specific provider
    """
    import argparse

    parser = argparse.ArgumentParser(description="TTS Announcer for Claude Code Hooks")
    parser.add_argument(
        "--list", "-l", action="store_true", help="List TTS system status"
    )
    parser.add_argument(
        "--provider", "-p", type=str, help="TTS provider to use (prerecorded, gtts)"
    )
    parser.add_argument(
        "hook_event_name",
        nargs="?",
        help="Hook event name to test (e.g., SessionStart, PreToolUse)",
    )
    parser.add_argument(
        "source", nargs="?", help="Source/reason for the event (optional)"
    )
    parser.add_argument(
        "--volume",
        "-v",
        type=float,
        default=0.5,
        help="Volume level 0.0-1.0 (default: 0.5)",
    )

    args = parser.parse_args()

    # Initialize TTS system
    from config import config

    if args.provider:
        # Use specific provider from command line
        providers = [args.provider]
    else:
        # Use providers from config
        providers = config.get_tts_providers_list()

    manager = initialize_tts(
        providers=providers,
        language=config.tts_language,
        cache_enabled=config.tts_cache_enabled,
    )

    if not manager:
        print("❌ Error: Could not initialize TTS system")
        return

    if args.list:
        print("🔊 TTS Announcer System Status")
        print("=" * 40)

        status = get_tts_status()

        if "error" in status:
            print(f"❌ Error: {status['error']}")
            return

        print(f"🎯 Primary Provider: {status['primary_provider']}")
        print(f"📋 Available Providers: {', '.join(status['available_providers'])}")
        print()

        print("🔧 Provider Status:")
        for provider_name, provider_status in status["provider_status"].items():
            status_icon = "✅" if provider_status["available"] else "❌"
            init_status = (
                "initialized" if provider_status["initialized"] else "not initialized"
            )
            print(f"   {status_icon} {provider_name} - {init_status}")

        print()
        print("💬 Available Descriptions:")
        from utils.tts_providers.mappings import AUDIO_DESCRIPTIONS_MAP

        for sound_file, description in AUDIO_DESCRIPTIONS_MAP.items():
            print(f'   • {sound_file}: "{description}"')

        return

    if not args.hook_event_name:
        print("❌ Error: Please provide hook_event_name or use --list")
        print("💡 Try: ./tts_announcer.py --list")
        return

    # Test announcement
    event_data = {}
    if args.source:
        event_data["source"] = args.source

    print(f"🔊 Testing TTS Announcer")
    print("=" * 25)
    print(f"🎯 Event: {args.hook_event_name}")
    print(f"🏷️  Source: {args.source or 'None'}")
    print(f"🔉 Volume: {args.volume}")
    print(f"⚙️  Providers: {', '.join(providers)}")
    print()

    # Get sound info
    manager = get_tts_manager()
    sound_path = (
        manager.get_sound(args.hook_event_name, event_data) if manager else None
    )

    if sound_path:
        print(f"🎵 Selected: {sound_path.name}")

        # Try to get description if it's a known sound file
        description = get_audio_description(sound_path.name)
        if description:
            print(f'💬 Description: "{description}"')

        print("🎵 Playing...")

        success = announce_event(args.hook_event_name, event_data, args.volume)

        if success:
            print("✅ Announcement complete!")
        else:
            print("❌ Error: Could not play announcement")
    else:
        print("❌ Error: No suitable sound found for this event")
        print("💡 Try: ./tts_announcer.py --list")


if __name__ == "__main__":
    main()
