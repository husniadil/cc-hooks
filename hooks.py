#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "requests>=2.32.5,<3",
#     "openai>=2.1.0,<3",
#     "gtts>=2.5.4,<3",
#     "elevenlabs>=2.16.0,<3",
#     "pygame>=2.6.1,<3",
#     "python-dotenv>=1.1.1,<2",
#     "psutil>=6.1.1,<7",
#     "aiosqlite>=0.21.0,<0.22",
#     "pyyaml>=6.0.1,<7",
# ]
# ///

# Claude Code hooks entry point
# Receives hook events from Claude Code via stdin and forwards them to the API server

import json
import os
import sys
import requests
from pathlib import Path
from typing import Dict, Any, Optional
from utils.colored_logger import (
    setup_logger,
    configure_root_logging,
    setup_file_logging,
)
from utils.constants import (
    NetworkConstants,
    PathConstants,
    get_server_url,
)
from utils.process_utils import detect_claude_pid

configure_root_logging()
logger = setup_logger(__name__)

# Track if file logging already setup
_file_logging_initialized = False


def discover_server_port(
    start_port: int = NetworkConstants.PORT_DISCOVERY_START,
    max_attempts: int = NetworkConstants.PORT_DISCOVERY_MAX_ATTEMPTS,
) -> int:
    """
    Discover the server port by trying sequential ports.
    Returns the first working port.
    Raises RuntimeError if no working port found.
    """
    for offset in range(max_attempts):
        port = start_port + offset
        try:
            url = get_server_url(port, "/health")
            response = requests.get(url, timeout=0.5)
            if response.status_code == 200:
                logger.debug(f"Found server on port {port}")
                return port
        except requests.exceptions.RequestException:
            continue

    error_msg = (
        f"Could not find running server on ports {start_port}-{start_port + max_attempts - 1}. "
        f"Troubleshooting: Check if server is running, verify network connectivity, "
        f"or check logs for startup errors."
    )
    raise RuntimeError(error_msg)


def find_available_port(
    start_port: int = NetworkConstants.PORT_DISCOVERY_START,
    max_attempts: int = NetworkConstants.PORT_DISCOVERY_MAX_ATTEMPTS,
) -> int:
    """
    Find an available port for starting server.
    Returns first port that's not in use.
    """
    import socket

    for offset in range(max_attempts):
        port = start_port + offset
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", port))
                return port
            except OSError:
                continue

    error_msg = (
        f"Could not find available port in range {start_port}-{start_port + max_attempts - 1}. "
        f"All ports are in use. Try closing other applications or increasing max_attempts."
    )
    raise RuntimeError(error_msg)


def start_server(port: int, log_file_path: Optional[str] = None) -> bool:
    """Start server in background on specified port.

    Returns True if started successfully.
    If log_file_path provided, server output will be appended to that file.
    """
    try:
        import subprocess

        # Get script directory - supports both plugin and standalone modes
        # Plugin mode: Use CLAUDE_PLUGIN_ROOT
        # Standalone mode: Use script directory
        script_dir = Path(os.getenv("CLAUDE_PLUGIN_ROOT", Path(__file__).parent))
        server_script = script_dir / "server.py"

        if not server_script.exists():
            logger.error(f"Server script not found: {server_script}")
            return False

        # Prepare environment variables for server
        server_env = {**os.environ, "PORT": str(port)}

        # Pass log file path to server via env var
        # Server will open and manage its own log file internally
        # This prevents file descriptor issues when hooks.py exits
        if log_file_path:
            server_env["LOG_FILE"] = str(log_file_path)
            logger.debug(f"Server will log to: {log_file_path}")

        # Start server in background
        # Use DEVNULL for stdout/stderr - server handles its own logging
        process = subprocess.Popen(
            ["uv", "run", str(server_script)],
            env=server_env,
            stdout=subprocess.DEVNULL,  # Server logs internally via LOG_FILE
            stderr=subprocess.DEVNULL,  # Server logs internally via LOG_FILE
            start_new_session=True,  # Detach from parent
        )

        logger.debug(f"Server process started (PID: {process.pid})")

        # Wait for server to be ready
        for attempt in range(NetworkConstants.SERVER_STARTUP_MAX_ATTEMPTS):
            try:
                url = get_server_url(port, "/health")
                response = requests.get(url, timeout=0.5)
                if response.status_code == 200:
                    logger.info(f"Started server on port {port}")
                    return True
            except requests.exceptions.RequestException:
                import time

                time.sleep(NetworkConstants.SERVER_STARTUP_RETRY_DELAY)

        # Server failed to start - kill the leaked subprocess
        logger.error(f"Server failed to start on port {port}")
        if log_file_path:
            logger.error(f"Check log file for details: {log_file_path}")

        try:
            process.terminate()
            process.wait(timeout=5)
            logger.debug(f"Cleaned up failed server process (PID: {process.pid})")
        except Exception as cleanup_err:
            logger.warning(
                f"Failed to cleanup server process {process.pid}: {cleanup_err}"
            )
            try:
                process.kill()
            except Exception:
                pass

        return False

    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        return False


def find_or_start_server(log_file_path: Optional[str] = None) -> int:
    """Start dedicated server for this Claude session.

    Each session gets its own server on a unique port.
    Returns port number of the started server.
    """
    # Start new dedicated server (each session has its own server)
    logger.info("Starting dedicated server for this session...")
    port = find_available_port()
    if start_server(port, log_file_path):
        return port
    else:
        raise RuntimeError("Failed to start server")


def register_session(session_id: str, claude_pid: int, port: int) -> bool:
    """
    Register session with settings at SessionStart.
    Reads CC_* env vars and POSTs to DB.

    Note: Handles /clear command case where same claude_pid starts new session.
    The API handles cleanup of sessions for this PID.
    """
    try:
        api_url = get_server_url(port, "/sessions")
        payload = {
            "session_id": session_id,
            "claude_pid": claude_pid,
            "server_port": port,
            "tts_language": os.getenv("CC_TTS_LANGUAGE"),
            "tts_providers": os.getenv("CC_TTS_PROVIDERS"),
            "tts_cache_enabled": os.getenv("CC_TTS_CACHE_ENABLED", "true").lower()
            == "true",
            "elevenlabs_voice_id": os.getenv("CC_ELEVENLABS_VOICE_ID"),
            "elevenlabs_model_id": os.getenv("CC_ELEVENLABS_MODEL_ID"),
            "silent_announcements": os.getenv("CC_SILENT_ANNOUNCEMENTS", "").lower()
            == "true",
            "silent_effects": os.getenv("CC_SILENT_EFFECTS", "").lower() == "true",
            "openrouter_enabled": os.getenv("CC_OPENROUTER_ENABLED", "").lower()
            == "true",
            "openrouter_model": os.getenv("CC_OPENROUTER_MODEL"),
            "openrouter_contextual_stop": os.getenv(
                "CC_OPENROUTER_CONTEXTUAL_STOP", ""
            ).lower()
            == "true",
            "openrouter_contextual_pretooluse": os.getenv(
                "CC_OPENROUTER_CONTEXTUAL_PRETOOLUSE", ""
            ).lower()
            == "true",
        }

        # cleanup_pid parameter deletes sessions for same claude_pid before insert
        response = requests.post(
            api_url, json=payload, params={"cleanup_pid": claude_pid}, timeout=10
        )
        response.raise_for_status()

        logger.info(
            f"Registered session {session_id} for claude_pid {claude_pid} on port {port}"
        )
        return True

    except requests.exceptions.RequestException as e:
        logger.error(f"Error registering session: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error registering session: {e}")
        return False


def read_json_from_stdin() -> Dict[str, Any]:
    """Read and parse JSON data from stdin."""
    try:
        data = sys.stdin.read()
        if not data.strip():
            raise ValueError("No data received from stdin")

        result = json.loads(data)
        if not isinstance(result, dict):
            raise ValueError("Expected JSON object")
        result_dict: Dict[str, Any] = result
        return result_dict
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON format - {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error reading from stdin: {e}")
        sys.exit(1)


def delete_session(session_id: str, port: int) -> bool:
    """
    Delete session at SessionEnd.
    """
    try:
        api_url = get_server_url(port, f"/sessions/{session_id}")
        response = requests.delete(api_url, timeout=10)
        response.raise_for_status()

        logger.info(f"Deleted session {session_id}")
        return True

    except requests.exceptions.ConnectionError as e:
        # Connection refused is expected during shutdown - server already closed
        if "Connection refused" in str(e) or "Errno 61" in str(e):
            logger.debug(
                "Server already shut down, session cleanup skipped (expected during exit)"
            )
        else:
            logger.error(f"Connection error deleting session: {e}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Error deleting session: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error deleting session: {e}")
        return False


def send_to_api(
    event_data: Dict[Any, Any],
    claude_pid: Optional[int] = None,
    port: Optional[int] = None,
) -> bool:
    """Send event data to the API endpoint."""
    try:
        global _file_logging_initialized

        # Get hook event name for lifecycle management
        hook_event_name = event_data.get("hook_event_name")

        # Detect Claude PID if not provided
        if claude_pid is None:
            claude_pid = detect_claude_pid()

        # Log process info for debugging
        import psutil

        hooks_pid = os.getpid()
        hooks_process = psutil.Process(hooks_pid)
        logger.debug(
            f"Hook process: PID={hooks_pid}, detected_claude_pid={claude_pid}, "
            f"event={hook_event_name}, name={hooks_process.name()}"
        )

        # Setup file logging early (once per instance)
        # Use shared directory for logs (persists across plugin updates)
        log_file_path = None
        if not _file_logging_initialized:
            try:
                # Use shared data directory for logs
                log_file_path = setup_file_logging(
                    claude_pid, str(PathConstants.LOGS_DIR)
                )
                _file_logging_initialized = True
            except Exception as e:
                logger.warning(f"Failed to setup file logging: {e}")
        else:
            # Log file already setup, construct path
            log_file_path = str(PathConstants.LOGS_DIR / f"{claude_pid}.log")

        # Handle SessionStart: find/start server, register session
        if hook_event_name == "SessionStart":
            session_id = event_data.get("session_id")
            if not session_id:
                raise RuntimeError("session_id required for SessionStart")

            # Detect editor type and decide whether to start server
            # Strategy:
            # - Terminal (any form) → Start server (legitimate CLI usage)
            # - Known editors → Per-editor rules (VSCode=skip, Zed=start)
            # - Unknown editor → Skip server (conservative, assume VSCode-like)
            try:
                from utils.editor_detector import detect_editor, is_terminal_session

                # First, check if it's a terminal session
                is_terminal = is_terminal_session(claude_pid)

                if is_terminal:
                    # Terminal session (iTerm, zsh, ssh, tmux, etc.) → Always start server
                    logger.info(
                        f"Detected terminal/CLI session {session_id}, starting server"
                    )
                else:
                    # Not terminal, check for known editors
                    editor = detect_editor(claude_pid)

                    if editor in ["vscode", "cursor", "windsurf"]:
                        # VSCode/forks → Skip server (only send SessionStart)
                        logger.info(
                            f"Detected {editor.upper()} extension (only sends SessionStart), "
                            f"skipping server start for session {session_id}"
                        )
                        print(
                            f"cc-hooks: {editor.upper()} extension detected, server disabled "
                            f"(only SessionStart hook supported by {editor})",
                            file=sys.stderr,
                        )
                        sys.exit(0)  # Exit cleanly

                    elif editor == "zed":
                        # Zed → Start server (sends hooks, PID monitor handles cleanup)
                        logger.info(
                            f"Detected Zed editor for session {session_id}, "
                            f"starting server (PID monitor will handle cleanup on exit)"
                        )

                    else:
                        # Unknown editor → Skip server (conservative approach)
                        logger.info(
                            f"Detected unknown editor for session {session_id}, "
                            f"skipping server start (conservative: assume VSCode-like behavior)"
                        )
                        print(
                            "cc-hooks: Unknown editor detected, server disabled "
                            "(only terminal and known editors supported)",
                            file=sys.stderr,
                        )
                        sys.exit(0)  # Exit cleanly

            except Exception as e:
                # Detection failed → Default to terminal behavior (start server)
                logger.warning(
                    f"Failed to detect editor for session {session_id}: {e}, "
                    f"defaulting to terminal behavior (starting server)"
                )

            # Check if we should reuse existing server (for /clear or /compact commands)
            # Extract source to determine if this is a soft restart that should reuse server
            # Use the same extraction logic as audio mappings (supports multiple field names)
            from utils.tts_providers.mappings import extract_source_from_event_data

            source = extract_source_from_event_data(hook_event_name, event_data)
            logger.info(
                f"SessionStart source detected: '{source}' (event_data keys: {list(event_data.keys())})"
            )

            existing_port = None
            if source in ["clear", "compact"]:
                logger.info(
                    f"Detected /{source} SessionStart - attempting to reuse existing server for PID {claude_pid}"
                )
                # Try to find existing server for this claude_pid
                try:
                    from app.event_db import get_session_by_pid
                    import asyncio

                    # Run async function in sync context
                    existing_session = asyncio.run(get_session_by_pid(claude_pid))
                    if existing_session:
                        test_port = existing_session.get("server_port")
                        logger.info(
                            f"Found existing session for PID {claude_pid} on port {test_port}, checking health..."
                        )
                        # Verify server is still alive
                        if test_port is not None:
                            try:
                                health_url = get_server_url(test_port, "/health")
                                health_response = requests.get(health_url, timeout=0.5)
                                if health_response.status_code == 200:
                                    existing_port = test_port
                                    logger.info(
                                        f"✓ Reusing existing server on port {test_port} for /{source} command"
                                    )
                                else:
                                    logger.info(
                                        f"✗ Server on port {test_port} returned status {health_response.status_code}, will start new server"
                                    )
                            except requests.exceptions.RequestException as e:
                                logger.info(
                                    f"✗ Server on port {test_port} not responding ({e}), will start new server"
                                )
                        else:
                            logger.warning(
                                f"Session for PID {claude_pid} has no server_port, will start new server"
                            )
                    else:
                        logger.info(
                            f"No existing session found for PID {claude_pid}, will start new server"
                        )
                except Exception as e:
                    logger.info(
                        f"Error looking up existing server: {e}, will start new server"
                    )
            else:
                logger.info(
                    f"Not a /clear or /compact SessionStart (source='{source}'), starting new server"
                )

            # Use existing server port or start new one
            if existing_port:
                port = existing_port
            else:
                # Find running server or start new one, pass log file for server output
                port = find_or_start_server(log_file_path)

            # Register session in DB (unified table with all info)
            if not register_session(session_id, claude_pid, port):
                logger.warning("Failed to register session, continuing anyway")

        # Get server port from DB if not provided (non-SessionStart events)
        # Each hook call is a new process, so we need to lookup the port from DB
        if port is None:
            session_id = event_data.get("session_id")
            if not session_id:
                raise RuntimeError("session_id required for non-SessionStart events")

            try:
                # Fast lookup: try to find session by session_id
                # Use shorter timeout for faster failure detection
                found_port = None
                lookup_timeout = 0.2

                for port_offset in range(10):
                    test_port = NetworkConstants.PORT_DISCOVERY_START + port_offset
                    try:
                        url = get_server_url(test_port, f"/sessions/{session_id}")
                        response = requests.get(url, timeout=lookup_timeout)
                        if response.status_code == 200:
                            session = response.json()
                            found_port = session.get("server_port")
                            actual_claude_pid = session.get("claude_pid")
                            logger.debug(
                                f"Found server port {found_port} for session {session_id}"
                            )
                            # Update claude_pid to actual PID from SessionStart
                            claude_pid = actual_claude_pid
                            break
                    except requests.exceptions.RequestException:
                        continue

                if found_port:
                    port = found_port
                else:
                    # Session not found - handle based on event type
                    if hook_event_name == "SessionStart":
                        # SessionStart creates server
                        logger.info(
                            f"SessionStart for new session {session_id}. Starting server..."
                        )
                        port = find_or_start_server(log_file_path)

                        # Register session
                        if not register_session(session_id, claude_pid, port):
                            logger.warning(
                                "Failed to register session, continuing anyway"
                            )

                        logger.info(
                            f"Started server on port {port} and registered session"
                        )
                    else:
                        # Non-SessionStart event: try to find running server and auto-register
                        # This handles cases where session ID changes without SessionStart
                        try:
                            discovered_port = discover_server_port()
                            logger.info(
                                f"Session {session_id} not found, auto-registering on port {discovered_port}"
                            )
                            if register_session(
                                session_id, claude_pid, discovered_port
                            ):
                                port = discovered_port
                                logger.info(
                                    f"Auto-registered session {session_id} on port {discovered_port}"
                                )
                            else:
                                logger.warning(
                                    f"Failed to auto-register session {session_id}, skipping event"
                                )
                                return True  # Skip event gracefully
                        except RuntimeError:
                            # No running server found
                            logger.warning(
                                f"Session {session_id} not found and no running server for "
                                f"{hook_event_name} event. Skipping (SessionStart must run first)."
                            )
                            return True  # Skip event gracefully

            except Exception as e:
                logger.error(f"Could not find or start server: {e}")
                raise

        # Send the event
        api_url = get_server_url(port, "/events")

        # Construct instance_id in "claude_pid:server_port" format
        instance_id = f"{claude_pid}:{port}"

        payload = {
            "data": event_data,
            "claude_pid": claude_pid,
            "instance_id": instance_id,
        }

        response = requests.post(api_url, json=payload, timeout=30)
        response.raise_for_status()
        response.json()  # Validate JSON response

        # Handle SessionEnd: wait for event processing, then cleanup and maybe shutdown
        if hook_event_name == "SessionEnd":
            import time

            session_id = event_data.get("session_id")
            if not session_id:
                logger.warning("No session_id for SessionEnd, skipping cleanup")
                return True

            # Extract end_reason to determine cleanup behavior
            # Check FIRST to avoid unnecessary waiting for /clear
            end_reason = event_data.get("reason")

            if end_reason == "clear":
                logger.info(
                    f"SessionEnd with reason 'clear' - keeping session {session_id} and server alive"
                )
                # Skip session deletion, shutdown, and waiting for /clear
                # Server and session will persist, avoiding unnecessary restart
                return True

            # For actual exits (not /clear), wait for last event to complete
            # This ensures all announcements complete during server shutdown (e.g., PreCompact, SessionEnd)
            logger.debug(
                "Waiting for last event (any type) to complete processing for instance..."
            )

            # Poll for last event completion with timeout
            # Check LAST event (not just SessionEnd) to ensure all events complete
            max_wait_time = 10  # Maximum 10 seconds
            poll_interval = 1  # Check every 1 second
            elapsed = 0
            all_events_completed = False

            while elapsed < max_wait_time:
                try:
                    # Check last event status for this instance (any event type)
                    last_event_url = get_server_url(
                        port, f"/instances/{instance_id}/last-event"
                    )
                    check_response = requests.get(last_event_url, timeout=2)

                    if check_response.status_code == 200:
                        result = check_response.json()
                        has_pending = result.get("has_pending", False)

                        if not has_pending:
                            logger.debug(
                                f"Last event completed for instance {instance_id} after {elapsed:.1f}s"
                            )
                            all_events_completed = True
                            break
                        else:
                            logger.debug(
                                f"Still waiting for last event... (has_pending={has_pending}, elapsed={elapsed}s)"
                            )
                except Exception as e:
                    logger.debug(f"Error checking last event status: {e}")

                time.sleep(poll_interval)
                elapsed += poll_interval

            if not all_events_completed:
                logger.warning(
                    f"Last event not completed after {max_wait_time}s, proceeding anyway"
                )

            logger.debug("Last event processing wait completed")

            # Legitimate exit (logout, prompt_input_exit, etc.) - cleanup normally
            logger.debug(
                f"SessionEnd with reason '{end_reason}' - proceeding with cleanup"
            )

            # Delete session (unified table)
            if not delete_session(session_id, port):
                logger.warning("Failed to delete session, continuing anyway")

            # Check if this is the last session FOR THIS SERVER and shutdown if so
            try:
                # Filter count by server_port to ensure we only count sessions for THIS server
                # This prevents shutdown when other server instances still have active sessions
                response = requests.get(
                    get_server_url(port, "/sessions/count"),
                    params={"server_port": port},
                    timeout=5,
                )
                response.raise_for_status()
                count = response.json().get("count", 0)

                if count == 0:
                    logger.info("Last session closed for this server, shutting down...")
                    # Shutdown server
                    shutdown_response = requests.post(
                        get_server_url(port, "/shutdown"), timeout=5
                    )
                    if shutdown_response.status_code == 200:
                        logger.info("Server shutdown initiated successfully")
                    else:
                        logger.warning(
                            f"Server shutdown returned status: {shutdown_response.status_code}"
                        )
                else:
                    logger.info(
                        f"Server will continue running ({count} session(s) remaining on port {port})"
                    )
            except requests.exceptions.ConnectionError as e:
                # Connection refused is expected - Claude Code already shut down the server
                if "Connection refused" in str(e) or "Errno 61" in str(e):
                    logger.debug(
                        "Server already shut down by Claude Code (expected during exit)"
                    )
                else:
                    logger.warning(f"Connection error checking session count: {e}")
            except Exception as e:
                logger.warning(f"Could not check session count or shutdown server: {e}")

        return True

    except Exception as e:
        logger.error(f"Error in send_to_api: {e}")
        return False


def main():
    """Main function to handle the hook process."""
    try:
        # Load config file defaults (only sets env vars if not already set)
        # Priority: CLI flags > Env vars > Config file > Hardcoded defaults
        from utils.config_loader import apply_config_to_env

        apply_config_to_env()

        event_data = read_json_from_stdin()
        success = send_to_api(event_data)

        sys.exit(0 if success else 1)

    except RuntimeError as e:
        logger.error(f"Runtime error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
