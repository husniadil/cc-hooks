#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "gtts",
#   "elevenlabs",
#   "openai",
#   "pygame",
#   "requests",
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
from utils.tts_providers.mappings import get_sound_file_for_event, get_audio_description

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


def _prepare_text_for_event(
    hook_event_name: str, event_data: Dict[str, Any], language: str = "en"
) -> Optional[str]:
    """
    Prepare text for TTS providers by determining base text and applying translation.

    This function consolidates the text determination logic that was previously
    duplicated in TTS providers, handling:
    - For Stop events: Use transcript parser to generate contextual completion messages
    - For other events: Sound file mapping to get base descriptions + OpenRouter translation
    - Fallback to event name if no description found

    Args:
        hook_event_name (str): Name of the hook event
        event_data (dict): Hook event data from Claude Code
        language (str): Target language for text (default: "en")

    Returns:
        str or None: Prepared text ready for TTS conversion
    """
    # Special handling for Stop events - use transcript parser for contextual messages
    if hook_event_name == "Stop":
        try:
            from utils.transcript_parser import extract_conversation_context
            from utils.openrouter_service import (
                generate_completion_message_if_available,
            )

            # Get session_id from event data
            session_id = event_data.get("session_id")
            if not session_id:
                logger.warning(
                    "No session_id in Stop event data, using fallback message"
                )
                fallback_text = (
                    get_audio_description("stop_task_completed.mp3")
                    or "Task completed successfully"
                )
                # Apply translation to fallback text
                try:
                    from utils.openrouter_service import translate_text_if_available

                    return translate_text_if_available(
                        fallback_text, language, hook_event_name, event_data
                    )
                except ImportError:
                    return fallback_text

            # Get transcript path from event data
            transcript_path = event_data.get("transcript_path")
            if not transcript_path:
                logger.info(
                    f"No transcript found for session {session_id}, using fallback message"
                )
                fallback_text = (
                    get_audio_description("stop_task_completed.mp3")
                    or "Task completed successfully"
                )
                # Apply translation to fallback text
                try:
                    from utils.openrouter_service import translate_text_if_available

                    return translate_text_if_available(
                        fallback_text, language, hook_event_name, event_data
                    )
                except ImportError:
                    return fallback_text

            # Extract conversation context
            context = extract_conversation_context(transcript_path)
            if not context.has_context():
                logger.info(
                    "No meaningful conversation context found, using fallback message"
                )
                fallback_text = (
                    get_audio_description("stop_task_completed.mp3")
                    or "Task completed successfully"
                )
                # Apply translation to fallback text
                try:
                    from utils.openrouter_service import translate_text_if_available

                    return translate_text_if_available(
                        fallback_text, language, hook_event_name, event_data
                    )
                except ImportError:
                    return fallback_text

            # Generate contextual completion message
            completion_message = generate_completion_message_if_available(
                session_id=session_id,
                user_prompt=context.last_user_prompt,
                claude_response=context.last_claude_response,
                target_language=language,
                fallback_message="Task completed successfully",
            )

            logger.info(
                f"Generated contextual completion message: '{completion_message}'"
            )
            return completion_message

        except Exception as e:
            logger.error(f"Error generating contextual completion message: {e}")
            # Fall back to default Stop message
            fallback_text = (
                get_audio_description("stop_task_completed.mp3")
                or "Task completed successfully"
            )
            # Apply translation to fallback text
            try:
                from utils.openrouter_service import translate_text_if_available

                return translate_text_if_available(
                    fallback_text, language, hook_event_name, event_data
                )
            except ImportError:
                return fallback_text

    # For all other events, use existing logic
    # Get sound file name from shared mapping
    sound_file = get_sound_file_for_event(hook_event_name, event_data)

    # Get base text (English description)
    base_text = None
    if sound_file:
        # Get descriptive text for the sound file
        description = get_audio_description(sound_file)
        if description:
            base_text = description

    # Fallback: use event name as text
    if not base_text:
        base_text = hook_event_name.replace("_", " ")

    # Apply OpenRouter translation if available and needed
    try:
        from utils.openrouter_service import translate_text_if_available

        translated_text = translate_text_if_available(
            base_text, language, hook_event_name, event_data
        )
        return translated_text
    except ImportError:
        # OpenRouter service not available, use original text
        return base_text


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

        # Prepare text for TTS providers
        from config import config

        prepared_text = _prepare_text_for_event(
            hook_event_name, event_data, config.tts_language
        )

        if prepared_text:
            # Add prepared text to event_data for TTS providers
            enhanced_event_data = event_data.copy()
            enhanced_event_data["_prepared_text"] = prepared_text
            # Mark contextual completion messages as no-cache
            if hook_event_name == "Stop":
                enhanced_event_data["_no_cache"] = True
        else:
            enhanced_event_data = event_data

        # Get appropriate sound for this event
        sound_path = manager.get_sound(hook_event_name, enhanced_event_data)

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
