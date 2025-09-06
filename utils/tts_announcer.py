#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
# ]
# ///
"""
TTS Announcer for Claude Code hooks with intelligent sound mapping.

This module provides context-aware sound announcements based on hook event types
and sources, mapping them to appropriate MP3 files for better user experience.
"""

import logging
from typing import Dict, Tuple, Optional, Any
from utils.sound_player import play_sound, get_sound_file_path

# Configure logging
logger = logging.getLogger(__name__)

# Mapping from event/source to appropriate MP3 files for Claude Code hook data
# Format: (hook_event_name, source) : "filename.mp3"
HOOK_EVENT_SOUND_MAP: Dict[Tuple[str, Optional[str]], str] = {
    # SessionStart events
    ("SessionStart", "startup"): "session_start_startup.mp3",
    ("SessionStart", "resume"): "session_start_resume.mp3",
    ("SessionStart", "clear"): "session_start_clear.mp3",
    ("SessionStart", "compact"): "session_start_compact.mp3",
    ("SessionStart", None): "session_start_startup.mp3",  # fallback
    ("SessionStart", "unknown"): "session_start_startup.mp3",  # fallback
    # SessionEnd events
    ("SessionEnd", "clear"): "session_end_clear.mp3",
    ("SessionEnd", "logout"): "session_end_logout.mp3",
    ("SessionEnd", "prompt_input_exit"): "session_end_prompt_input_exit.mp3",
    ("SessionEnd", "other"): "session_end_other.mp3",
    ("SessionEnd", None): "session_end_other.mp3",  # fallback
    # PreToolUse events
    ("PreToolUse", "tool_running"): "pre_tool_use_tool_running.mp3",
    ("PreToolUse", "command_blocked"): "pre_tool_use_command_blocked.mp3",
    ("PreToolUse", None): "pre_tool_use_tool_running.mp3",  # fallback
    # PostToolUse events
    ("PostToolUse", "tool_completed"): "post_tool_use_tool_completed.mp3",
    ("PostToolUse", None): "post_tool_use_tool_completed.mp3",  # fallback
    # Notification events
    ("Notification", "general"): "notification_general.mp3",
    ("Notification", "permission"): "notification_permission.mp3",
    ("Notification", "waiting"): "notification_waiting.mp3",
    ("Notification", None): "notification_general.mp3",  # fallback
    # UserPromptSubmit events
    ("UserPromptSubmit", "prompt"): "user_prompt_submit_prompt.mp3",
    ("UserPromptSubmit", None): "user_prompt_submit_prompt.mp3",  # fallback
    # Stop events
    ("Stop", "task_completed"): "stop_task_completed.mp3",
    ("Stop", None): "stop_task_completed.mp3",  # fallback
    # SubagentStop events
    ("SubagentStop", "agent_completed"): "subagent_stop_agent_completed.mp3",
    ("SubagentStop", None): "subagent_stop_agent_completed.mp3",  # fallback
    # PreCompact events
    ("PreCompact", "auto"): "pre_compact_auto.mp3",
    ("PreCompact", "manual"): "pre_compact_manual.mp3",
    ("PreCompact", None): "pre_compact_auto.mp3",  # fallback
}


def extract_source_from_event_data(event_data: Dict[str, Any]) -> Optional[str]:
    """
    Extract source information from Claude Code hook event data.

    Args:
        event_data (dict): Hook event data from Claude Code

    Returns:
        str or None: Extracted source identifier
    """
    # Special handling for Notification events based on message content
    if event_data.get("hook_event_name") == "Notification" and "message" in event_data:
        message = str(event_data["message"])

        if message.startswith("Claude needs your permission"):
            return "permission"
        elif message.startswith("Claude is waiting for your input"):
            return "waiting"
        else:
            return "general"

    # Common source fields in Claude Code hook data
    source_fields = ["source", "reason", "trigger", "action", "type"]

    for field in source_fields:
        if field in event_data and event_data[field]:
            return str(event_data[field]).lower()

    return None


def get_announcement_sound(
    hook_event_name: str, event_data: Dict[str, Any]
) -> Optional[str]:
    """
    Get appropriate sound file for hook event based on context mapping.

    Args:
        hook_event_name (str): Name of the hook event
        event_data (dict): Hook event data from Claude Code

    Returns:
        str or None: Sound file name if found and exists, None otherwise
    """
    try:
        # Extract source from event data
        source = extract_source_from_event_data(event_data)

        # Try exact match first: (event, source)
        mapping_key = (hook_event_name, source)
        if mapping_key in HOOK_EVENT_SOUND_MAP:
            sound_file = HOOK_EVENT_SOUND_MAP[mapping_key]

            # Verify file exists before returning
            if get_sound_file_path(sound_file):
                logger.info(f"Found specific mapping: {mapping_key} -> {sound_file}")
                return sound_file
            else:
                logger.warning(f"Mapped sound file not found: {sound_file}")

        # Try fallback with None source: (event, None)
        fallback_key = (hook_event_name, None)
        if fallback_key in HOOK_EVENT_SOUND_MAP:
            sound_file = HOOK_EVENT_SOUND_MAP[fallback_key]

            # Verify file exists
            if get_sound_file_path(sound_file):
                logger.info(f"Found fallback mapping: {fallback_key} -> {sound_file}")
                return sound_file
            else:
                logger.warning(f"Fallback sound file not found: {sound_file}")

        # No suitable sound found - return None (no sound will be played)
        logger.info(
            f"No announcement sound mapping for: {hook_event_name} (source: {source})"
        )
        return None

    except Exception as e:
        logger.error(f"Error getting announcement sound: {e}")
        return None


def announce_event(
    hook_event_name: str, event_data: Dict[str, Any], volume: float = 0.5
) -> bool:
    """
    Play appropriate announcement sound for a hook event.

    Args:
        hook_event_name (str): Name of the hook event
        event_data (dict): Hook event data from Claude Code
        volume (float): Volume level 0.0-1.0 (default: 0.5)

    Returns:
        bool: True if sound played successfully, False otherwise
    """
    try:
        # Get appropriate sound for this event
        sound_file = get_announcement_sound(hook_event_name, event_data)

        if not sound_file:
            logger.info(f"No announcement sound available for {hook_event_name}")
            return False

        # Play the sound using existing sound player
        success = play_sound(sound_file, volume)

        if success:
            logger.info(f"Announced {hook_event_name} with {sound_file}")
        else:
            logger.warning(f"Failed to announce {hook_event_name} with {sound_file}")

        return success

    except Exception as e:
        logger.error(f"Error announcing event {hook_event_name}: {e}")
        return False


def list_available_mappings() -> Dict[str, list]:
    """
    Get information about available sound mappings.

    Returns:
        dict: Dictionary with mapping info and available files
    """
    try:
        available_mappings = {}
        missing_files = []

        for (event, source), sound_file in HOOK_EVENT_SOUND_MAP.items():
            if get_sound_file_path(sound_file):
                event_key = f"{event}" + (f" ({source})" if source else "")
                if event not in available_mappings:
                    available_mappings[event] = []
                available_mappings[event].append(
                    {"source": source, "sound_file": sound_file, "key": event_key}
                )
            else:
                missing_files.append(
                    {"event": event, "source": source, "sound_file": sound_file}
                )

        return {
            "available_mappings": available_mappings,
            "missing_files": missing_files,
            "total_mappings": len(HOOK_EVENT_SOUND_MAP),
            "available_count": len(HOOK_EVENT_SOUND_MAP) - len(missing_files),
        }

    except Exception as e:
        logger.error(f"Error listing mappings: {e}")
        return {"error": str(e)}


def main():
    """
    Command-line interface for TTS announcer.

    Usage:
    - ./tts_announcer.py --list                    # List available mappings
    - ./tts_announcer.py SessionStart startup      # Test announcement
    - ./tts_announcer.py SessionStart              # Test with no source
    """
    import argparse

    parser = argparse.ArgumentParser(description="TTS Announcer for Claude Code Hooks")
    parser.add_argument(
        "--list", "-l", action="store_true", help="List available sound mappings"
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

    if args.list:
        print("🔊 TTS Announcer Sound Mappings")
        print("=" * 40)

        mappings_info = list_available_mappings()

        if "error" in mappings_info:
            print(f"❌ Error: {mappings_info['error']}")
            return

        available = mappings_info["available_mappings"]
        missing = mappings_info["missing_files"]

        print(
            f"📊 Summary: {mappings_info['available_count']}/{mappings_info['total_mappings']} mappings available"
        )
        print()

        for event_name, mappings in available.items():
            print(f"🎯 {event_name}:")
            for mapping in mappings:
                source_info = (
                    f" (source: {mapping['source']})"
                    if mapping["source"]
                    else " (no source)"
                )
                print(f"   • {mapping['sound_file']}{source_info}")
            print()

        if missing:
            print("⚠️  Missing Files:")
            for item in missing:
                source_info = f" (source: {item['source']})" if item["source"] else ""
                print(f"   • {item['event']}{source_info} -> {item['sound_file']}")

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
    print()

    # Get sound info
    sound_file = get_announcement_sound(args.hook_event_name, event_data)
    if sound_file:
        print(f"🎵 Selected: {sound_file}")
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
