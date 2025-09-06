#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
# ]
# ///
"""
Cross-Platform Sound Effect Player for Claude Code hooks.

This module provides flexible sound effect playback across macOS, Linux, and WSL.
Supports automatic sound file discovery, platform detection, and graceful error handling.
"""

import platform
import subprocess
import sys
from pathlib import Path


def get_audio_command():
    """
    Get the appropriate audio playback command for the current platform.

    Returns:
        tuple: (command, supports_volume) - command as list and volume support flag
    """
    system = platform.system().lower()

    if system == "darwin":  # macOS
        if subprocess.run(["which", "afplay"], capture_output=True).returncode == 0:
            return (["afplay"], True)

    elif system == "linux":  # Linux/WSL
        # Try common Linux audio players in order of preference
        audio_commands = [
            (["ffplay", "-nodisp", "-autoexit"], False),  # ffmpeg
            (["mpg123", "-q"], False),  # mpg123
        ]

        for cmd, vol_support in audio_commands:
            if subprocess.run(["which", cmd[0]], capture_output=True).returncode == 0:
                return (cmd, vol_support)

    return (None, False)


def get_sound_dir():
    """
    Get the sound directory path relative to the script location.

    Returns:
        Path: Path to the sound directory
    """
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

        supported_extensions = {".mp3"}
        sound_files = [
            f.name
            for f in sound_dir.iterdir()
            if f.is_file() and f.suffix.lower() in supported_extensions
        ]
        return sorted(sound_files)
    except Exception:
        return []


def play_sound(sound_file="sound_effect_tek.mp3", volume=0.5):
    """
    Play a sound effect using cross-platform audio commands.

    Args:
        sound_file (str): Sound file name (default: "sound_effect_tek.mp3")
        volume (float): Volume level 0.0-1.0 (default: 0.5)

    Returns:
        bool: True if sound played successfully, False otherwise
    """
    try:
        # Get appropriate audio command for platform
        audio_cmd, supports_volume = get_audio_command()
        if not audio_cmd:
            print(
                f"[DEBUG] No audio playback command available on {platform.system()}",
                file=sys.stderr,
            )
            return False

        # Get sound file path directly from sound directory
        sound_path = get_sound_file_path(sound_file)

        if not sound_path:
            return False

        # Build command with platform-specific options
        cmd = audio_cmd.copy()
        cmd.append(str(sound_path))

        # Add volume control if supported (currently only afplay)
        if supports_volume and audio_cmd[0] == "afplay":
            cmd.extend(["-v", str(volume)])

        # Execute audio playback (blocking - queue manager handles async)
        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
        )

        return True

    except subprocess.CalledProcessError as e:
        # Log subprocess errors for debugging if needed
        print(f"[DEBUG] Sound player subprocess error: {e}", file=sys.stderr)
        return False
    except Exception as e:
        # Log API errors for debugging if needed
        print(f"[DEBUG] Sound player error: {e}", file=sys.stderr)
        return False


def main():
    """
    Command-line interface for sound player.

    Usage:
    - ./sound_player.py                    # Play default sound (sound_effect_tek.mp3)
    - ./sound_player.py sound_effect_cetek.mp3          # Play specific sound
    - ./sound_player.py --list             # List available sounds
    - ./sound_player.py --volume 0.3 sound_effect_tek.mp3  # Play with custom volume
    """
    import argparse

    parser = argparse.ArgumentParser(description="Cross-Platform Sound Effect Player")
    parser.add_argument(
        "sound_file",
        nargs="?",
        default="sound_effect_tek.mp3",
        help="Sound file to play (default: sound_effect_tek.mp3)",
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

    # Get audio command info for display
    audio_cmd, supports_volume = get_audio_command()
    platform_name = platform.system()

    print(f"🔊 {platform_name} Sound Player")
    print("=" * 25)
    print(f"🎯 File: {args.sound_file}")
    if supports_volume:
        print(f"🔉 Volume: {args.volume}")
    else:
        print("🔉 Volume: system default (volume control not supported)")
    if audio_cmd:
        print(f"🎵 Command: {' '.join(audio_cmd)}")
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
