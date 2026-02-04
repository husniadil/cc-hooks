#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "gtts>=2.5.4,<3",
#   "elevenlabs>=2.16.0,<3",
#   "openai>=2.1.0,<3",
#   "pygame>=2.6.1,<3",
#   "requests>=2.32.5,<3",
#   "python-dotenv>=1.1.1,<2",
# ]
# ///
"""
TTS Announcer for Claude Code hooks with unified provider system.

This module provides context-aware sound announcements using a flexible
TTS provider architecture that supports pre-recorded sounds, Google TTS,
and future providers like ElevenLabs.
"""

import sys
from pathlib import Path
from typing import Dict, Optional, Any

# Add parent directory to path for utils imports
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from utils.sound_player import play_sound  # noqa: E402
from utils.tts_manager import get_tts_manager, initialize_tts_manager  # noqa: E402
from utils.tts_providers.mappings import (  # noqa: E402
    get_sound_file_for_event,
    get_audio_description,
)
from utils.colored_logger import setup_logger, configure_root_logging  # noqa: E402
from utils.constants import SoundFiles  # noqa: E402

configure_root_logging()
logger = setup_logger(__name__)


def _convert_camel_case_words(text: str) -> str:
    """
    Convert camelCase words in text to readable format with spaces.
    Falls back to original text if any error occurs.

    Examples:
        "getUserName" -> "get User Name"
        "XMLParser" -> "XML Parser"
        "I'm using getUserId2" -> "I'm using get User Id 2"
        "JavaScript" -> "JavaScript" (preserved)

    Args:
        text: Text that may contain camelCase words

    Returns:
        Text with camelCase converted to readable format, or original text if error
    """
    if not text:
        return text

    try:
        import re

        def convert_word(word: str) -> str:
            """Convert individual word jika memang camelCase pattern"""
            try:
                # Check if word contains programming identifier patterns:
                # 1. lowercase followed by uppercase: camelCase
                # 2. uppercase sequence followed by lowercase: XMLParser
                # 3. mix of letters and numbers: userId2, API2Response
                has_camel_pattern = (
                    re.search(r"[a-z][A-Z]", word)  # camelCase
                    or re.search(r"[A-Z]{2,}[a-z]", word)  # XMLParser, HTTPSConnection
                    or re.search(
                        r"[a-zA-Z][0-9]|[0-9][a-zA-Z]", word
                    )  # userId2, API2Response
                )

                if not has_camel_pattern:
                    return word

                # Apply conversion: insert spaces at word boundaries
                converted = re.sub(
                    r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|(?<=[a-zA-Z])(?=[0-9])|(?<=[0-9])(?=[a-zA-Z])",
                    " ",
                    word,
                )

                return converted

            except Exception:
                # Fallback: return original word if conversion fails
                return word

        # Split text into words dan process each one
        words = text.split()
        converted_words = [convert_word(word) for word in words]

        return " ".join(converted_words)

    except Exception:
        # Fallback: return original text if entire function fails
        logger.warning("camelCase conversion failed, using original text")
        return text


def _clean_text_for_tts(text: str) -> str:
    """
    Clean text for TTS by removing formatting characters that would be read aloud.
    Includes camelCase conversion, fallback protection, and lowercase normalization.

    Args:
        text: Original text that may contain markdown formatting

    Returns:
        Cleaned text suitable for TTS, or empty string if None/empty input
    """
    if not text or text is None:
        return ""

    import re

    # First handle content inside backticks and other formatting - convert underscores to spaces FIRST
    def process_content(match):
        content = match.group(1)
        return re.sub(r"_", " ", content)

    # Remove backticks and keep content, converting underscores to spaces
    cleaned = re.sub(r"`([^`]+)`", process_content, text)  # Single backticks
    cleaned = re.sub(r"```([^`]+)```", process_content, cleaned)  # Triple backticks
    cleaned = re.sub(r"`", " ", cleaned)  # Any remaining backticks become spaces

    # Remove markdown bold/italic markers but keep content, converting underscores to spaces
    cleaned = re.sub(r"\*\*([^*]+)\*\*", process_content, cleaned)  # Bold
    cleaned = re.sub(r"\*([^*]+)\*", process_content, cleaned)  # Italic
    cleaned = re.sub(
        r"__(.*?)__", process_content, cleaned
    )  # Bold underscore (non-greedy)
    cleaned = re.sub(
        r"_(.*?)_", process_content, cleaned
    )  # Italic underscore (non-greedy)
    cleaned = re.sub(r"~~([^~]+)~~", process_content, cleaned)  # Strikethrough

    # Remove markdown links but keep the text
    cleaned = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", cleaned)

    # Convert any remaining underscores to spaces (so they're not pronounced as "underscore")
    cleaned = re.sub(r"_", " ", cleaned)

    # Remove remaining formatting symbols
    cleaned = re.sub(r"[#*~]", "", cleaned)

    # Convert camelCase variables to readable text with spaces
    cleaned = _convert_camel_case_words(cleaned)

    # Convert to lowercase for better TTS pronunciation
    cleaned = cleaned.lower()

    # Clean up multiple spaces and trim
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    return cleaned


def _shorten_tool_name_for_tts(tool_name: str, max_length: int = 20) -> str:
    """
    Shorten tool name for TTS announcements if too long.

    Args:
        tool_name: Original tool name
        max_length: Maximum length for tool name in TTS

    Returns:
        Shortened tool name suitable for TTS
    """
    if not tool_name or len(tool_name) <= max_length:
        return tool_name

    # Handle MCP tools specially - extract the meaningful part
    if tool_name.startswith("mcp__"):
        parts = tool_name.split("__")
        if len(parts) >= 3:
            # For mcp__provider__tool pattern, use just the tool name
            meaningful_part = parts[-1]
            # If still too long, take first part of tool name
            if len(meaningful_part) > max_length:
                return meaningful_part[:max_length].rstrip("_-")
            return meaningful_part

    # For other long tool names, just truncate
    return tool_name[:max_length].rstrip("_-")


def initialize_tts(providers: Optional[list[str]] = None, **kwargs) -> Any:
    """Initialize the TTS system with ordered provider list.

    Args:
        providers: List of provider names in order of preference
        **kwargs: Additional arguments for provider initialization

    Returns:
        TTSManager instance or None if initialization fails
    """
    try:
        return initialize_tts_manager(providers=providers, **kwargs)
    except Exception as e:
        logger.error(f"Error initializing TTS system: {e}")
        return None


def _translate_fallback_text(
    text: str, language: str, hook_event_name: str, event_data: Dict[str, Any]
) -> str:
    """
    Translate fallback text if OpenRouter translation is available.

    Args:
        text: The fallback text to translate
        language: Target language code
        hook_event_name: Name of the hook event
        event_data: Event data dictionary

    Returns:
        Translated text if available, otherwise original text
    """
    try:
        from utils.openrouter_service import translate_text_if_available

        return translate_text_if_available(text, language, hook_event_name, event_data)
    except ImportError:
        return text


def _prepare_text_for_event(
    hook_event_name: str,
    event_data: Dict[str, Any],
    language: str = "en",
    session_settings: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Prepare text for TTS providers by determining base text and applying translation.

    This function handles text determination logic for TTS providers:
    - For Stop events: Use transcript parser to generate contextual completion messages
    - For other events: Sound file mapping to get base descriptions + OpenRouter translation
    - Fallback to event name if no description found

    Args:
        hook_event_name (str): Name of the hook event
        event_data (dict): Hook event data from Claude Code
        language (str): Target language for text (default: "en")
        session_settings (dict): Optional session-specific settings (for OpenRouter contextual flags)

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
                    get_audio_description(SoundFiles.STOP_TASK_COMPLETED)
                    or "Task completed successfully"
                )
                # Apply translation to fallback text
                return _translate_fallback_text(
                    fallback_text, language, hook_event_name, event_data
                )

            # Get transcript path from event data
            transcript_path = event_data.get("transcript_path")
            if not transcript_path:
                logger.info(
                    f"No transcript found for session {session_id}, using fallback message"
                )
                fallback_text = (
                    get_audio_description(SoundFiles.STOP_TASK_COMPLETED)
                    or "Task completed successfully"
                )
                # Apply translation to fallback text
                return _translate_fallback_text(
                    fallback_text, language, hook_event_name, event_data
                )

            # Extract conversation context
            context = extract_conversation_context(transcript_path)
            if not context.has_context():
                logger.info(
                    "No meaningful conversation context found, skipping announcement"
                )
                return None

            # Get session-specific contextual_stop setting
            override_contextual_stop = None
            if session_settings:
                override_contextual_stop = session_settings.get(
                    "openrouter_contextual_stop"
                )
                logger.debug(
                    f"Using session contextual_stop setting: {override_contextual_stop}"
                )

            # Generate contextual completion message
            completion_message = generate_completion_message_if_available(
                session_id=session_id,
                user_prompt=context.last_user_prompt,
                claude_response=context.last_claude_response,
                target_language=language,
                fallback_message="Task completed successfully",
                override_contextual_stop=override_contextual_stop,
            )

            logger.info(
                f"Generated contextual completion message: '{completion_message}'"
            )
            return completion_message

        except Exception as e:
            logger.error(f"Error generating contextual completion message: {e}")
            # Fall back to default Stop message
            fallback_text = (
                get_audio_description(SoundFiles.STOP_TASK_COMPLETED)
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

    # Special handling for PreToolUse events - use transcript parser for contextual messages
    if hook_event_name == "PreToolUse":
        try:
            from utils.transcript_parser import extract_conversation_context
            from utils.openrouter_service import (
                generate_pre_tool_message_if_available,
            )

            # Get session_id and tool_name from event data
            session_id = event_data.get("session_id")
            tool_name = event_data.get("tool_name", "unknown")

            if not session_id:
                logger.warning(
                    "No session_id in PreToolUse event data, using fallback message"
                )
                short_tool_name = _shorten_tool_name_for_tts(tool_name)
                fallback_text = f"Running {short_tool_name} tool"
                # Apply translation to fallback text
                return _translate_fallback_text(
                    fallback_text, language, hook_event_name, event_data
                )

            # Get transcript path from event data
            transcript_path = event_data.get("transcript_path")
            if not transcript_path:
                logger.info(
                    f"No transcript found for session {session_id}, using fallback message"
                )
                short_tool_name = _shorten_tool_name_for_tts(tool_name)
                fallback_text = f"Running {short_tool_name} tool"
                # Apply translation to fallback text
                return _translate_fallback_text(
                    fallback_text, language, hook_event_name, event_data
                )

            # Extract conversation context
            context = extract_conversation_context(transcript_path)
            if not context.has_context():
                logger.info(
                    "No meaningful conversation context found, skipping announcement"
                )
                return None

            # Get session-specific contextual_pretooluse setting
            override_contextual_pretooluse = None
            if session_settings:
                override_contextual_pretooluse = session_settings.get(
                    "openrouter_contextual_pretooluse"
                )
                logger.debug(
                    f"Using session contextual_pretooluse setting: {override_contextual_pretooluse}"
                )

            # Generate contextual PreToolUse message
            pre_tool_message = generate_pre_tool_message_if_available(
                session_id=session_id,
                tool_name=tool_name,
                user_prompt=context.last_user_prompt,
                claude_response=context.last_claude_response,
                target_language=language,
                fallback_message=f"Running {_shorten_tool_name_for_tts(tool_name)} tool",
                override_contextual_pretooluse=override_contextual_pretooluse,
            )

            logger.info(
                f"Generated contextual PreToolUse message: '{pre_tool_message}'"
            )
            return pre_tool_message

        except Exception as e:
            logger.error(f"Error generating contextual PreToolUse message: {e}")
            # Fall back to default PreToolUse message
            tool_name = event_data.get("tool_name", "unknown")
            short_tool_name = _shorten_tool_name_for_tts(tool_name)
            fallback_text = f"Running {short_tool_name} tool"
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
    hook_event_name: str,
    event_data: Dict[str, Any],
    volume: float = 0.5,
    session_settings: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Play appropriate announcement sound for a hook event using TTS providers.

    Args:
        hook_event_name (str): Name of the hook event
        event_data (dict): Hook event data from Claude Code
        volume (float): Volume level 0.0-1.0 (default: 0.5)
        session_settings (dict): Optional session-specific settings (language, providers, voice_id, etc.)

    Returns:
        bool: True if sound played successfully, False otherwise
    """
    try:
        # Early exit if silent announcements mode is enabled (skip expensive OpenRouter calls)
        if session_settings and session_settings.get("silent_announcements", False):
            logger.debug(
                f"Silent announcements mode enabled, skipping announcement for {hook_event_name}"
            )
            return False

        # Get TTS configuration (session-specific or global defaults)
        from config import config

        tts_language = (
            session_settings.get("tts_language")
            if session_settings and session_settings.get("tts_language")
            else config.tts_language
        )
        tts_providers = (
            session_settings.get("tts_providers")
            if session_settings and session_settings.get("tts_providers")
            else config.tts_providers
        )
        elevenlabs_voice_id = (
            session_settings.get("elevenlabs_voice_id")
            if session_settings and session_settings.get("elevenlabs_voice_id")
            else config.elevenlabs_voice_id
        )
        elevenlabs_model_id = (
            session_settings.get("elevenlabs_model_id")
            if session_settings and session_settings.get("elevenlabs_model_id")
            else config.elevenlabs_model_id
        )
        tts_cache_enabled = (
            session_settings.get("tts_cache_enabled")
            if session_settings
            and session_settings.get("tts_cache_enabled") is not None
            else config.tts_cache_enabled
        )

        voice_id_preview = elevenlabs_voice_id[:8] if elevenlabs_voice_id else "None"
        logger.debug(
            f"TTS settings - language: {tts_language}, providers: {tts_providers}, voice_id: {voice_id_preview}..., model_id: {elevenlabs_model_id}, cache: {tts_cache_enabled} (from {'session' if session_settings and session_settings.get('tts_language') else 'config'})"
        )

        # Get TTS manager (reinitialize if session has different providers)
        manager = get_tts_manager()
        if not manager or (session_settings and session_settings.get("tts_providers")):
            # Reinitialize with session-specific providers if provided
            providers_list = (
                [p.strip() for p in tts_providers.split(",")]
                if isinstance(tts_providers, str)
                else config.get_tts_providers_list()
            )
            manager = initialize_tts_manager(
                providers=providers_list,
                language=tts_language,
                cache_enabled=tts_cache_enabled,
                api_key=config.elevenlabs_api_key,
                voice_id=elevenlabs_voice_id,
                model_id=elevenlabs_model_id,
            )

        if not manager:
            logger.error("TTS manager not initialized")
            return False

        # Prepare text for TTS providers
        prepared_text = _prepare_text_for_event(
            hook_event_name, event_data, str(tts_language), session_settings
        )

        # For contextual events (Stop, PreToolUse), skip announcement if no meaningful context
        if hook_event_name in ["Stop", "PreToolUse"] and prepared_text is None:
            logger.info(
                f"Skipping {hook_event_name} announcement due to no meaningful context"
            )
            return False

        if prepared_text:
            # Clean text for TTS (remove backticks and formatting)
            cleaned_text = _clean_text_for_tts(prepared_text)

            # Add prepared text to event_data for TTS providers
            enhanced_event_data = event_data.copy()
            enhanced_event_data["_prepared_text"] = cleaned_text
            # Mark contextual completion messages as no-cache
            if hook_event_name == "Stop" or hook_event_name == "PreToolUse":
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

        return bool(success)

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
        api_key=config.elevenlabs_api_key,
        voice_id=config.elevenlabs_voice_id,
        model_id=config.elevenlabs_model_id,
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

        for sound_file, desc in AUDIO_DESCRIPTIONS_MAP.items():
            print(f'   • {sound_file}: "{desc}"')

        return

    if not args.hook_event_name:
        print("❌ Error: Please provide hook_event_name or use --list")
        print("💡 Try: ./tts_announcer.py --list")
        return

    # Test announcement
    event_data = {}
    if args.source:
        event_data["source"] = args.source

    print("🔊 Testing TTS Announcer")
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
        description: str | None = get_audio_description(sound_path.name)
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
