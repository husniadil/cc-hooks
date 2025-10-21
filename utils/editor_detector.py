#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["psutil"]
# ///

"""
Editor Detection Utility

Detects the parent editor (VSCode, Zed, Cursor, Windsurf, etc.) by tracing
the parent process chain of a given Claude PID.

Usage:
    uv run utils/editor_detector.py <claude_pid>
    uv run utils/editor_detector.py --test
"""

import os
import sys
from typing import Optional, Dict, List

try:
    import psutil
except ImportError:
    print("Error: psutil not available. Run: uv pip install psutil", file=sys.stderr)
    sys.exit(1)


# Editor signatures for detection
# Each editor has multiple signatures ordered by reliability:
# 1. Extension directory (most reliable - always in user home)
# 2. Unique subprocess/agent names (very reliable)
# 3. App names (least reliable - depends on install location)
EDITOR_SIGNATURES = {
    "zed": [
        "claude-code-acp",  # Unique agent identifier (most reliable)
        "Application Support/Zed",  # Always ~/Library/Application Support/Zed
        "Zed.app",  # App name (works with substring matching)
    ],
    "vscode": [
        ".vscode/extensions/anthropic.claude-code",  # Most reliable
        ".vscode-insiders/extensions/anthropic.claude-code",  # VSCode Insiders
        ".vscode-oss/extensions/anthropic.claude-code",  # VSCodium/OSS
        "anthropic.claude-code",  # Extension ID (fallback)
        "Code Helper (Plugin)",  # Subprocess name (shared by variants)
        "Visual Studio Code.app",  # Standard install
        "Code - Insiders.app",  # VSCode Insiders
        "VSCodium.app",  # VSCodium
        "Code - OSS.app",  # Code OSS
    ],
    "cursor": [
        ".cursor/extensions/anthropic.claude-code",  # Most reliable
        "Cursor.app",  # App name
    ],
    "windsurf": [
        ".windsurf/extensions/anthropic.claude-code",  # Most reliable
        "Windsurf.app",  # App name
    ],
}


def get_process_chain(pid: int, max_depth: int = 10) -> List[Dict[str, str]]:
    """
    Get the process chain from the given PID to the root process.

    Returns list of dicts with 'pid', 'name', 'cmdline' for each process.
    """
    chain = []
    current_pid = pid

    for _ in range(max_depth):
        try:
            proc = psutil.Process(current_pid)
            chain.append(
                {
                    "pid": current_pid,
                    "name": proc.name(),
                    "cmdline": " ".join(proc.cmdline()),
                }
            )

            # Move to parent
            parent = proc.parent()
            if parent is None or parent.pid == 1:
                break
            current_pid = parent.pid

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            break

    return chain


def is_terminal_session(pid: int) -> bool:
    """
    Detect if Claude is running in a terminal/CLI session.

    Returns True if process chain contains shell or terminal emulator.
    """
    chain = get_process_chain(pid)

    # Known shells
    shells = ["bash", "zsh", "fish", "sh", "tcsh", "ksh", "dash"]

    # Known terminal emulators (case-insensitive)
    terminals = [
        "terminal",  # macOS Terminal.app
        "iterm",
        "iterm2",
        "alacritty",
        "kitty",
        "warp",
        "hyper",
        "wezterm",
        "rio",
        "konsole",  # KDE
        "gnome-terminal",
        "xterm",
        "tmux",  # Terminal multiplexer
        "screen",  # Terminal multiplexer
    ]

    for process_info in chain:
        name = process_info["name"].lower()

        # Check if it's a known shell
        if name in shells:
            return True

        # Check if it's a terminal emulator (substring match)
        if any(term in name for term in terminals):
            return True

        # Check for SSH session
        if "sshd" in name or "ssh" in name:
            return True

    return False


def detect_editor(pid: int) -> Optional[str]:
    """
    Detect which editor spawned the Claude process with the given PID.

    Returns:
        Editor name ("zed", "vscode", "cursor", "windsurf") or None if unknown/terminal
    """
    chain = get_process_chain(pid)

    # Check each editor's signatures
    for editor_name, signatures in EDITOR_SIGNATURES.items():
        for process_info in chain:
            cmdline = process_info["cmdline"]
            # Check if any signature matches this process
            if any(sig in cmdline for sig in signatures):
                return editor_name

    return None


def is_vscode_extension(pid: int) -> bool:
    """
    Specific check for VSCode extension (only sends SessionStart).
    More reliable than general editor detection.
    """
    return detect_editor(pid) == "vscode"


def is_editor_session(pid: int) -> bool:
    """
    Check if this is an editor session (vs terminal).
    """
    return detect_editor(pid) is not None


def get_editor_info(pid: int) -> Dict[str, any]:
    """
    Get detailed editor information for a given Claude PID.

    Returns dict with 'editor', 'is_editor', 'process_chain'.
    """
    editor = detect_editor(pid)
    chain = get_process_chain(pid)

    return {
        "editor": editor,
        "is_editor": editor is not None,
        "is_vscode": editor == "vscode",
        "process_chain": chain,
    }


def main():
    """CLI interface for editor detection."""
    if len(sys.argv) < 2:
        print("Usage: uv run utils/editor_detector.py <claude_pid>", file=sys.stderr)
        print("       uv run utils/editor_detector.py --test", file=sys.stderr)
        sys.exit(1)

    if sys.argv[1] == "--test":
        # Test with all running Claude processes
        print("Searching for Claude processes...")
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                if proc.info["name"] == "claude" or (
                    proc.info["cmdline"]
                    and any("claude" in arg for arg in proc.info["cmdline"])
                ):
                    pid = proc.info["pid"]
                    info = get_editor_info(pid)
                    print(f"\nClaude PID {pid}:")
                    print(f"  Editor: {info['editor'] or 'terminal/unknown'}")
                    print(f"  Process chain:")
                    for p in info["process_chain"][:5]:
                        print(f"    {p['pid']}: {p['name']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return

    # Single PID check
    try:
        pid = int(sys.argv[1])
    except ValueError:
        print(f"Error: Invalid PID '{sys.argv[1]}'", file=sys.stderr)
        sys.exit(1)

    info = get_editor_info(pid)

    print(f"Claude PID: {pid}")
    print(f"Editor: {info['editor'] or 'terminal/unknown'}")
    print(f"Is editor session: {info['is_editor']}")
    print(f"Is VSCode: {info['is_vscode']}")
    print(f"\nProcess chain:")
    for i, proc in enumerate(info["process_chain"], 1):
        print(f"{i}. PID {proc['pid']}: {proc['name']}")
        if len(proc["cmdline"]) < 200:
            print(f"   {proc['cmdline']}")
        else:
            print(f"   {proc['cmdline'][:200]}...")


if __name__ == "__main__":
    main()
