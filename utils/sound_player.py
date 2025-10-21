#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pygame>=2.6.1,<3",
# ]
# ///
"""
Cross-Platform Sound Effect Player for Claude Code hooks.

This module provides flexible sound effect playback across macOS, Linux, and WSL.
Supports automatic sound file discovery, platform detection, and graceful error handling.
"""

import os
import platform
import sys
from pathlib import Path

try:
    import pygame

    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    pygame = None

try:
    from utils.constants import SoundFiles

    DEFAULT_SOUND = SoundFiles.TEK
except ImportError:
    # Fallback if constants module not available (standalone mode)
    DEFAULT_SOUND = "sound_effect_tek.mp3"


def get_sound_dir():
    """
    Get the sound directory path - supports both plugin and standalone modes.

    Plugin mode: Uses CLAUDE_PLUGIN_ROOT/sound
    Standalone mode: Uses script directory/../sound

    Returns:
        Path: Path to the sound directory
    """
    # Check if running in plugin mode
    plugin_root = os.getenv("CLAUDE_PLUGIN_ROOT")
    if plugin_root:
        return Path(plugin_root) / "sound"
    # Standalone mode: relative to script location
    return Path(__file__).parent.parent / "sound"


def get_sound_file_path(sound_file):
    """
    Get the full path to a sound file.

    Args:
        sound_file (str): Sound file name

    Returns:
        Path or None: Path to the sound file if it exists, None otherwise
    """
    sound_dir = get_sound_dir()
    sound_path = sound_dir / sound_file
    return sound_path if sound_path.exists() else None


def get_available_sound_files():
    """
    Discover available sound files in the sound directory.

    Returns:
        list: List of available sound file names (without path)
    """
    try:
        sound_dir = get_sound_dir()
        if not sound_dir.exists():
            return []

        # Pygame supports multiple audio formats
        supported_extensions = {".mp3", ".wav", ".ogg", ".flac"}
        sound_files = [
            f.name
            for f in sound_dir.iterdir()
            if f.is_file() and f.suffix.lower() in supported_extensions
        ]
        return sorted(sound_files)
    except Exception:
        return []


def play_sound(sound_file=None, volume=0.5):
    """
    Play a sound effect using pygame for cross-platform compatibility.

    Args:
        sound_file (str): Sound file name (default: SoundFiles.TEK)
        volume (float): Volume level 0.0-1.0 (default: 0.5)

    Returns:
        bool: True if sound played successfully, False otherwise
    """
    if sound_file is None:
        sound_file = DEFAULT_SOUND
    if not PYGAME_AVAILABLE:
        print(
            "[DEBUG] pygame not available - install with 'pip install pygame'",
            file=sys.stderr,
        )
        return False

    # Get sound file path
    sound_path = get_sound_file_path(sound_file)
    if not sound_path:
        print(f"[DEBUG] Sound file not found: {sound_file}", file=sys.stderr)
        return False

    try:
        # Initialize pygame mixer for audio playback
        pygame.mixer.init()

        # Load and play the audio
        pygame.mixer.music.load(str(sound_path))
        pygame.mixer.music.set_volume(volume)
        pygame.mixer.music.play()

        # Wait for playback to finish (blocking - queue manager handles async)
        while pygame.mixer.music.get_busy():
            pygame.time.wait(100)

        # Cleanup
        pygame.mixer.quit()
        return True

    except Exception as e:
        print(f"[DEBUG] Pygame audio error: {e}", file=sys.stderr)
        # Cleanup on error
        try:
            pygame.mixer.quit()
        except:
            pass
        return False


def main():
    """
    Command-line interface for sound player.

    Usage:
    - ./sound_player.py                    # Play default sound (SoundFiles.TEK)
    - ./sound_player.py sound_effect_cetek.mp3          # Play specific sound
    - ./sound_player.py --list             # List available sounds
    - ./sound_player.py --volume 0.3 sound_effect_tek.mp3  # Play with custom volume
    """
    import argparse

    parser = argparse.ArgumentParser(description="Cross-Platform Sound Effect Player")
    parser.add_argument(
        "sound_file",
        nargs="?",
        default=DEFAULT_SOUND,
        help=f"Sound file to play (default: {DEFAULT_SOUND})",
    )
    parser.add_argument(
        "--volume",
        "-v",
        type=float,
        default=0.5,
        help="Volume level 0.0-1.0 (default: 0.5)",
    )
    parser.add_argument(
        "--list", "-l", action="store_true", help="List available sound files"
    )

    args = parser.parse_args()

    if args.list:
        print("🔊 Available Sound Effects:")
        print("=" * 30)
        sound_files = get_available_sound_files()
        if sound_files:
            for sound in sound_files:
                print(f"  • {sound}")
        else:
            print("  No sound files found in sound/ directory")
        return

    # Display info
    platform_name = platform.system()

    print(f"🔊 {platform_name} Sound Player")
    print("=" * 25)
    print(f"🎯 File: {args.sound_file}")

    if PYGAME_AVAILABLE:
        print("🎵 Backend: pygame (cross-platform)")
        print(f"🔉 Volume: {args.volume}")
    else:
        print("🎵 Backend: pygame not available")
        print("💡 Install pygame: pip install pygame")

    print("🎵 Playing...")

    success = play_sound(args.sound_file, args.volume)

    if success:
        print("✅ Playback complete!")
    else:
        print("❌ Error: Could not play sound file")
        print("💡 Try: ./sound_player.py --list")
        sys.exit(1)


if __name__ == "__main__":
    main()
