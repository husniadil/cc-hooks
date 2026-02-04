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

_file_logging_initialized = False


def discover_server_port(
    start_port: int = NetworkConstants.PORT_DISCOVERY_START,
    max_attempts: int = NetworkConstants.PORT_DISCOVERY_MAX_ATTEMPTS,
) -> int:
    """Discover the server port by trying sequential ports. Raises RuntimeError if none found."""
    for offset in range(max_attempts):
        port = start_port + offset
        try:
            if (
                requests.get(
                    get_server_url(port, "/health"),
                    timeout=NetworkConstants.HEALTH_CHECK_TIMEOUT,
                ).status_code
                == 200
            ):
                logger.debug(f"Found server on port {port}")
                return port
        except requests.exceptions.RequestException:
            continue

    raise RuntimeError(
        f"Could not find running server on ports {start_port}-{start_port + max_attempts - 1}"
    )


def find_available_port(
    start_port: int = NetworkConstants.PORT_DISCOVERY_START,
    max_attempts: int = NetworkConstants.PORT_DISCOVERY_MAX_ATTEMPTS,
) -> int:
    """Find an available port for starting server. Raises RuntimeError if none found."""
    import socket

    for offset in range(max_attempts):
        port = start_port + offset
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", port))
                return port
            except OSError:
                continue

    raise RuntimeError(
        f"Could not find available port in range {start_port}-{start_port + max_attempts - 1}"
    )


def start_server(port: int, log_file_path: Optional[str] = None) -> bool:
    """Start server in background on specified port. Returns True if started successfully."""
    try:
        import subprocess
        import time

        script_dir = Path(os.getenv("CLAUDE_PLUGIN_ROOT", Path(__file__).parent))
        server_script = script_dir / "server.py"

        if not server_script.exists():
            logger.error(f"Server script not found: {server_script}")
            return False

        server_env = {**os.environ, "PORT": str(port)}
        if log_file_path:
            server_env["LOG_FILE"] = str(log_file_path)

        process = subprocess.Popen(
            ["uv", "run", str(server_script)],
            env=server_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        logger.debug(f"Server process started (PID: {process.pid})")

        for _ in range(NetworkConstants.SERVER_STARTUP_MAX_ATTEMPTS):
            try:
                if (
                    requests.get(
                        get_server_url(port, "/health"),
                        timeout=NetworkConstants.HEALTH_CHECK_TIMEOUT,
                    ).status_code
                    == 200
                ):
                    logger.info(f"Started server on port {port}")
                    return True
            except requests.exceptions.RequestException:
                time.sleep(NetworkConstants.SERVER_STARTUP_RETRY_DELAY)

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
    """Start dedicated server for this Claude session. Returns port number."""
    logger.info("Starting dedicated server for this session...")
    port = find_available_port()
    if not start_server(port, log_file_path):
        raise RuntimeError("Failed to start server")
    return port


def _env_bool(name: str) -> bool:
    """Read an environment variable as boolean (true if value is 'true')."""
    return os.getenv(name, "").lower() == "true"


def register_session(session_id: str, claude_pid: int, port: int) -> bool:
    """Register session with settings at SessionStart. Reads CC_* env vars and POSTs to DB."""
    try:
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
            "silent_announcements": _env_bool("CC_SILENT_ANNOUNCEMENTS"),
            "silent_effects": _env_bool("CC_SILENT_EFFECTS"),
            "openrouter_enabled": _env_bool("CC_OPENROUTER_ENABLED"),
            "openrouter_model": os.getenv("CC_OPENROUTER_MODEL"),
            "openrouter_contextual_stop": _env_bool("CC_OPENROUTER_CONTEXTUAL_STOP"),
            "openrouter_contextual_pretooluse": _env_bool(
                "CC_OPENROUTER_CONTEXTUAL_PRETOOLUSE"
            ),
        }

        response = requests.post(
            get_server_url(port, "/sessions"),
            json=payload,
            params={"cleanup_pid": claude_pid},
            timeout=NetworkConstants.API_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        logger.info(
            f"Registered session {session_id} for claude_pid {claude_pid} on port {port}"
        )
        return True

    except Exception as e:
        logger.error(f"Error registering session: {e}")
        return False


def read_json_from_stdin() -> Dict[str, Any]:
    """Read and parse JSON data from stdin."""
    try:
        data = sys.stdin.read().strip()
        if not data:
            raise ValueError("No data received from stdin")
        result = json.loads(data)
        if not isinstance(result, dict):
            raise ValueError("Expected JSON object")
        return result
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Error reading from stdin: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error reading from stdin: {e}")
        sys.exit(1)


def delete_session(session_id: str, port: int) -> bool:
    """Delete session at SessionEnd."""
    try:
        response = requests.delete(
            get_server_url(port, f"/sessions/{session_id}"),
            timeout=NetworkConstants.API_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        logger.info(f"Deleted session {session_id}")
        return True
    except requests.exceptions.ConnectionError as e:
        if "Connection refused" in str(e) or "Errno 61" in str(e):
            logger.debug(
                "Server already shut down, session cleanup skipped (expected during exit)"
            )
        else:
            logger.error(f"Connection error deleting session: {e}")
        return False
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        return False


def _setup_file_logging(claude_pid: int) -> Optional[str]:
    """Setup file logging once per process. Returns log file path."""
    global _file_logging_initialized
    if not _file_logging_initialized:
        try:
            log_file_path = setup_file_logging(claude_pid, str(PathConstants.LOGS_DIR))
            _file_logging_initialized = True
            return log_file_path
        except Exception as e:
            logger.warning(f"Failed to setup file logging: {e}")
            return None
    return str(PathConstants.LOGS_DIR / f"{claude_pid}.log")


def _check_editor_compatibility(session_id: str, claude_pid: int) -> None:
    """Check editor type and exit if unsupported. Only proceeds for terminal/Zed."""
    try:
        from utils.editor_detector import detect_editor, is_terminal_session

        if is_terminal_session(claude_pid):
            logger.info(f"Detected terminal/CLI session {session_id}, starting server")
            return

        editor = detect_editor(claude_pid)

        if editor in ["vscode", "cursor", "windsurf"]:
            logger.info(
                f"Detected {editor.upper()} extension (only sends SessionStart), "
                f"skipping server start for session {session_id}"
            )
            print(
                f"cc-hooks: {editor.upper()} extension detected, server disabled "
                f"(only SessionStart hook supported by {editor})",
                file=sys.stderr,
            )
            sys.exit(0)

        elif editor == "zed":
            logger.info(
                f"Detected Zed editor for session {session_id}, "
                f"starting server (PID monitor will handle cleanup on exit)"
            )

        else:
            logger.info(
                f"Detected unknown editor for session {session_id}, "
                f"skipping server start (conservative: assume VSCode-like behavior)"
            )
            print(
                "cc-hooks: Unknown editor detected, server disabled "
                "(only terminal and known editors supported)",
                file=sys.stderr,
            )
            sys.exit(0)

    except Exception as e:
        logger.warning(
            f"Failed to detect editor for session {session_id}: {e}, "
            f"defaulting to terminal behavior (starting server)"
        )


def _try_reuse_existing_server(source: str, claude_pid: int) -> Optional[int]:
    """Try to reuse an existing server for /clear or /compact. Returns port or None."""
    if source not in ["clear", "compact"]:
        logger.info(
            f"Not a /clear or /compact SessionStart (source='{source}'), starting new server"
        )
        return None

    logger.info(
        f"Detected /{source} SessionStart - attempting to reuse existing server for PID {claude_pid}"
    )
    try:
        from app.event_db import get_session_by_pid
        import asyncio

        existing_session = asyncio.run(get_session_by_pid(claude_pid))
        if not existing_session:
            logger.info(
                f"No existing session found for PID {claude_pid}, will start new server"
            )
            return None

        test_port = existing_session.get("server_port")
        logger.info(
            f"Found existing session for PID {claude_pid} on port {test_port}, checking health..."
        )

        if test_port is None:
            logger.warning(
                f"Session for PID {claude_pid} has no server_port, will start new server"
            )
            return None

        try:
            health_response = requests.get(
                get_server_url(test_port, "/health"),
                timeout=NetworkConstants.HEALTH_CHECK_TIMEOUT,
            )
            if health_response.status_code == 200:
                logger.info(
                    f"Reusing existing server on port {test_port} for /{source} command"
                )
                return test_port
            logger.info(
                f"Server on port {test_port} returned status {health_response.status_code}, will start new server"
            )
        except requests.exceptions.RequestException as e:
            logger.info(
                f"Server on port {test_port} not responding ({e}), will start new server"
            )

    except Exception as e:
        logger.info(f"Error looking up existing server: {e}, will start new server")

    return None


def _handle_session_start(
    event_data: Dict[Any, Any], claude_pid: int, log_file_path: Optional[str]
) -> int:
    """Handle SessionStart: editor check, server reuse/start, session registration. Returns port."""
    session_id = event_data.get("session_id")
    if not session_id:
        raise RuntimeError("session_id required for SessionStart")

    _check_editor_compatibility(session_id, claude_pid)

    # Check for server reuse on /clear or /compact
    from utils.tts_providers.mappings import extract_source_from_event_data

    source = extract_source_from_event_data("SessionStart", event_data)
    logger.info(
        f"SessionStart source detected: '{source}' (event_data keys: {list(event_data.keys())})"
    )

    port = _try_reuse_existing_server(source or "", claude_pid)
    if port is None:
        port = find_or_start_server(log_file_path)

    if not register_session(session_id, claude_pid, port):
        logger.warning("Failed to register session, continuing anyway")

    return port


def _resolve_server_port(
    event_data: Dict[Any, Any],
    hook_event_name: Optional[str],
    claude_pid: int,
    log_file_path: Optional[str],
) -> tuple[int, int]:
    """Resolve server port for non-SessionStart events. Returns (port, claude_pid)."""
    session_id = event_data.get("session_id")
    if not session_id:
        raise RuntimeError("session_id required for non-SessionStart events")

    # Fast lookup: scan running servers for this session
    for port_offset in range(10):
        test_port = NetworkConstants.PORT_DISCOVERY_START + port_offset
        try:
            url = get_server_url(test_port, f"/sessions/{session_id}")
            response = requests.get(
                url, timeout=NetworkConstants.SESSION_LOOKUP_TIMEOUT
            )
            if response.status_code == 200:
                session = response.json()
                found_port = session.get("server_port")
                actual_claude_pid = session.get("claude_pid")
                logger.debug(f"Found server port {found_port} for session {session_id}")
                return found_port, actual_claude_pid
        except requests.exceptions.RequestException:
            continue

    # Session not found — fallback based on event type
    if hook_event_name == "SessionStart":
        logger.info(f"SessionStart for new session {session_id}. Starting server...")
        port = find_or_start_server(log_file_path)
        if not register_session(session_id, claude_pid, port):
            logger.warning("Failed to register session, continuing anyway")
        logger.info(f"Started server on port {port} and registered session")
        return port, claude_pid

    # Non-SessionStart: try auto-registering on a discovered server
    try:
        discovered_port = discover_server_port()
        logger.info(
            f"Session {session_id} not found, auto-registering on port {discovered_port}"
        )
        if register_session(session_id, claude_pid, discovered_port):
            logger.info(
                f"Auto-registered session {session_id} on port {discovered_port}"
            )
            return discovered_port, claude_pid
        logger.warning(f"Failed to auto-register session {session_id}, skipping event")
    except RuntimeError:
        logger.warning(
            f"Session {session_id} not found and no running server for "
            f"{hook_event_name} event. Skipping (SessionStart must run first)."
        )

    raise _SkipEvent()


class _SkipEvent(Exception):
    """Signal to skip an event gracefully (no server found)."""


def _post_event(event_data: Dict[Any, Any], claude_pid: int, port: int) -> str:
    """POST event to the API server. Returns instance_id."""
    instance_id = f"{claude_pid}:{port}"
    payload = {
        "data": event_data,
        "claude_pid": claude_pid,
        "instance_id": instance_id,
    }
    response = requests.post(
        get_server_url(port, "/events"),
        json=payload,
        timeout=NetworkConstants.EVENT_SUBMIT_TIMEOUT,
    )
    response.raise_for_status()
    response.json()  # Validate JSON response
    return instance_id


def _handle_session_end(
    event_data: Dict[Any, Any], port: int, instance_id: str
) -> None:
    """Handle SessionEnd: wait for events, cleanup session, maybe shutdown server."""
    session_id = event_data.get("session_id")
    if not session_id:
        logger.warning("No session_id for SessionEnd, skipping cleanup")
        return

    end_reason = event_data.get("reason")

    # /clear keeps session and server alive
    if end_reason == "clear":
        logger.info(
            f"SessionEnd with reason 'clear' - keeping session {session_id} and server alive"
        )
        return

    # Wait for all events to finish processing before cleanup
    _wait_for_event_completion(port, instance_id)

    logger.debug(f"SessionEnd with reason '{end_reason}' - proceeding with cleanup")

    if not delete_session(session_id, port):
        logger.warning("Failed to delete session, continuing anyway")

    _maybe_shutdown_server(port)


def _wait_for_event_completion(port: int, instance_id: str) -> None:
    """Poll for last event completion with timeout."""
    import time

    logger.debug(
        "Waiting for last event (any type) to complete processing for instance..."
    )

    max_wait_time = 10
    poll_interval = 1
    elapsed = 0

    while elapsed < max_wait_time:
        try:
            last_event_url = get_server_url(
                port, f"/instances/{instance_id}/last-event"
            )
            check_response = requests.get(
                last_event_url, timeout=NetworkConstants.LAST_EVENT_POLL_TIMEOUT
            )

            if check_response.status_code == 200:
                result = check_response.json()
                if not result.get("has_pending", False):
                    logger.debug(
                        f"Last event completed for instance {instance_id} after {elapsed:.1f}s"
                    )
                    return
                logger.debug(
                    f"Still waiting for last event... (has_pending=True, elapsed={elapsed}s)"
                )
        except Exception as e:
            logger.debug(f"Error checking last event status: {e}")

        time.sleep(poll_interval)
        elapsed += poll_interval

    logger.warning(
        f"Last event not completed after {max_wait_time}s, proceeding anyway"
    )


def _maybe_shutdown_server(port: int) -> None:
    """Shutdown server if this was the last session on it."""
    try:
        response = requests.get(
            get_server_url(port, "/sessions/count"),
            params={"server_port": port},
            timeout=NetworkConstants.SHUTDOWN_TIMEOUT,
        )
        response.raise_for_status()
        count = response.json().get("count", 0)

        if count == 0:
            logger.info("Last session closed for this server, shutting down...")
            shutdown_response = requests.post(
                get_server_url(port, "/shutdown"),
                timeout=NetworkConstants.SHUTDOWN_TIMEOUT,
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
        if "Connection refused" in str(e) or "Errno 61" in str(e):
            logger.debug(
                "Server already shut down by Claude Code (expected during exit)"
            )
        else:
            logger.warning(f"Connection error checking session count: {e}")
    except Exception as e:
        logger.warning(f"Could not check session count or shutdown server: {e}")


def send_to_api(
    event_data: Dict[Any, Any],
    claude_pid: Optional[int] = None,
    port: Optional[int] = None,
) -> bool:
    """Send event data to the API endpoint. Orchestrates lifecycle hooks."""
    try:
        if claude_pid is None:
            claude_pid = detect_claude_pid()

        # Log process info for debugging
        import psutil

        hooks_pid = os.getpid()
        hooks_process = psutil.Process(hooks_pid)
        hook_event_name = event_data.get("hook_event_name")
        logger.debug(
            f"Hook process: PID={hooks_pid}, detected_claude_pid={claude_pid}, "
            f"event={hook_event_name}, name={hooks_process.name()}"
        )

        log_file_path = _setup_file_logging(claude_pid)

        # Resolve server port based on event type
        if hook_event_name == "SessionStart":
            port = _handle_session_start(event_data, claude_pid, log_file_path)
        elif port is None:
            port, claude_pid = _resolve_server_port(
                event_data, hook_event_name, claude_pid, log_file_path
            )

        # Fire event to server
        instance_id = _post_event(event_data, claude_pid, port)

        # Post-event lifecycle handling
        if hook_event_name == "SessionEnd":
            _handle_session_end(event_data, port, instance_id)

        return True

    except _SkipEvent:
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
