"""Shared process utilities for Claude Code hooks system."""

import os
from typing import Optional

from utils.colored_logger import setup_logger

logger = setup_logger(__name__)

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not available - process detection disabled")


def is_claude_binary(name: str, cmdline: str, cmdline_list: list[str]) -> bool:
    """Check if a process matches Claude binary signatures."""
    return (
        name == "claude"
        or cmdline.startswith("claude ")
        or cmdline == "claude"
        or (len(cmdline_list) > 0 and cmdline_list[0].endswith("/claude"))
    )


def detect_claude_pid() -> int:
    """Detect Claude binary PID by walking up the process tree."""
    if not PSUTIL_AVAILABLE:
        raise RuntimeError("psutil not available for Claude PID detection")

    try:
        current_process = psutil.Process(os.getpid())

        # Walk up the process tree looking for actual 'claude' binary
        while current_process:
            cmdline_list = current_process.cmdline()
            cmdline = " ".join(cmdline_list).lower()
            name = current_process.name().lower()

            if is_claude_binary(name, cmdline, cmdline_list):
                claude_pid: int = current_process.pid
                logger.debug(f"Found Claude process: PID={claude_pid}")
                return claude_pid

            # Move to parent
            _parent = current_process.parent()
            if _parent:
                current_process = _parent
            else:
                break

        raise RuntimeError("Claude process not found in parent process tree")

    except RuntimeError:
        raise
    except Exception as e:
        logger.error(f"Failed to detect Claude PID: {e}")
        raise RuntimeError(f"Could not detect Claude PID: {e}")


def detect_claude_pid_safe() -> Optional[int]:
    """Detect Claude binary PID, returning None instead of raising."""
    try:
        return detect_claude_pid()
    except (RuntimeError, Exception) as e:
        logger.debug(f"Could not detect Claude PID: {e}")
        return None


def is_claude_process(pid: int) -> bool:
    """Check if a PID is a Claude process. Returns True when uncertain (conservative)."""
    if not PSUTIL_AVAILABLE:
        logger.warning(f"psutil not available, assuming PID {pid} is Claude")
        return True

    try:
        proc = psutil.Process(pid)
        cmdline_list = proc.cmdline()
        name = proc.name().lower()
        cmdline = " ".join(cmdline_list).lower()

        return is_claude_binary(name, cmdline, cmdline_list)
    except psutil.NoSuchProcess:
        # Process doesn't exist - definitely not Claude
        return False
    except psutil.AccessDenied:
        # Cannot access process - be conservative
        logger.warning(f"Access denied checking PID {pid} - assuming it is Claude")
        return True
    except Exception as e:
        # Error occurred - be conservative to avoid false cleanup
        logger.warning(
            f"Could not check if PID {pid} is Claude process: {e} - assuming it is"
        )
        return True


def is_process_running(pid: int) -> bool:
    """Check if a process with given PID exists."""
    try:
        import errno

        os.kill(pid, 0)
        return True
    except OSError as e:
        return e.errno == errno.EPERM
