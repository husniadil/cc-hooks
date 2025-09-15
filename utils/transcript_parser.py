#!/usr/bin/env uv run
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

"""
Transcript parser for Claude Code JSONL conversation files.

This module provides utilities to parse Claude Code transcript files
and extract conversation context for enhanced event processing.
"""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from utils.colored_logger import setup_logger, configure_root_logging

configure_root_logging()
logger = setup_logger(__name__)


def _get_temp_dir() -> Path:
    """Get or create temporary directory for transcript tracking."""
    temp_dir = Path(".claude-instances")
    try:
        temp_dir.mkdir(exist_ok=True)
    except (PermissionError, OSError) as e:
        logger.warning(f"Failed to create temp directory {temp_dir}: {e}")
        # Fallback to system temp directory
        import tempfile

        temp_dir = Path(tempfile.gettempdir()) / "claude-instances"
        temp_dir.mkdir(exist_ok=True)
        logger.info(f"Using fallback temp directory: {temp_dir}")
    return temp_dir


def _get_message_hash(entry: Dict[str, Any]) -> str:
    """Generate a hash for a message entry to use as unique identifier."""
    # Use timestamp, type, and content hash as unique identifier
    timestamp = entry.get("timestamp", "")
    msg_type = entry.get("type", "")
    message_content = str(entry.get("message", {}))

    # Create hash from combination of these fields
    content_to_hash = f"{timestamp}_{msg_type}_{message_content}"
    return hashlib.sha256(content_to_hash.encode()).hexdigest()[:16]


def _get_last_processed_file(session_id: str) -> Path:
    """Get path to file tracking last processed message for a session."""
    temp_dir = _get_temp_dir()
    return temp_dir / f"last-processed-{session_id}.txt"


def _save_last_processed_message(session_id: str, message_hash: str) -> None:
    """Save the hash of the last processed Claude message."""
    try:
        last_processed_file = _get_last_processed_file(session_id)
        with open(last_processed_file, "w") as f:
            f.write(message_hash)
        logger.debug(f"Saved last processed message hash: {message_hash}")
    except Exception as e:
        logger.warning(f"Failed to save last processed message: {e}")


def _get_last_processed_message(session_id: str) -> Optional[str]:
    """Get the hash of the last processed Claude message."""
    try:
        last_processed_file = _get_last_processed_file(session_id)
        if last_processed_file.exists():
            with open(last_processed_file, "r") as f:
                message_hash = f.read().strip()
                logger.debug(f"Retrieved last processed message hash: {message_hash}")
                return message_hash
    except Exception as e:
        logger.warning(f"Failed to read last processed message: {e}")
    return None


def clear_last_processed_message(session_id: str) -> None:
    """Clear the last processed message tracking for a session."""
    try:
        last_processed_file = _get_last_processed_file(session_id)
        if last_processed_file.exists():
            last_processed_file.unlink()
            logger.debug(f"Cleared last processed message for session {session_id}")
    except Exception as e:
        logger.warning(f"Failed to clear last processed message: {e}")


def cleanup_old_processed_files(max_age_hours: int = 24) -> None:
    """Clean up old last-processed files older than max_age_hours."""
    try:
        import time

        temp_dir = _get_temp_dir()
        current_time = time.time()
        cutoff_time = current_time - (max_age_hours * 3600)

        for file_path in temp_dir.glob("last-processed-*.txt"):
            try:
                file_stat = file_path.stat()
                if file_stat.st_mtime < cutoff_time:
                    file_path.unlink()
                    logger.debug(f"Cleaned up old processed file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up file {file_path}: {e}")

    except Exception as e:
        logger.warning(f"Failed to cleanup old processed files: {e}")


class ConversationContext:
    """Container for conversation context data."""

    def __init__(
        self,
        last_user_prompt: Optional[str] = None,
        last_claude_response: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        self.last_user_prompt = last_user_prompt
        self.last_claude_response = last_claude_response
        self.session_id = session_id

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "last_user_prompt": self.last_user_prompt,
            "last_claude_response": self.last_claude_response,
            "session_id": self.session_id,
        }

    def has_context(self) -> bool:
        """Check if we have meaningful conversation context."""
        return bool(self.last_claude_response)


def extract_message_content(message_data: Dict[str, Any]) -> Optional[str]:
    """
    Extract text content from Claude Code message data.

    Handles both string content and array content formats.

    Args:
        message_data: Message data from JSONL entry

    Returns:
        Extracted text content or None if not found
    """
    try:
        if not message_data:
            logger.debug("extract_message_content: No message data provided")
            return None

        if "content" not in message_data:
            logger.debug("extract_message_content: No 'content' field in message data")
            return None

        content = message_data["content"]

        # Handle string content directly
        if isinstance(content, str):
            stripped_content = content.strip()
            if not stripped_content:
                logger.debug(
                    "extract_message_content: Empty string content after stripping"
                )
                return None
            return stripped_content

        # Handle array content (Claude Code format)
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_content = item.get("text", "")
                    if text_content and isinstance(text_content, str):
                        text_parts.append(text_content.strip())

            if text_parts:
                return " ".join(text_parts)
            else:
                logger.debug(
                    "extract_message_content: No text content found in array format"
                )
                return None

        # Unknown content format
        logger.info(
            f"extract_message_content: Unsupported content format: {type(content)}"
        )
        return None

    except Exception as e:
        # Use error level for unexpected exceptions as these indicate real problems
        logger.error(f"Error extracting message content from data {message_data}: {e}")
        return None


def parse_jsonl_line(line: str) -> Optional[Dict[str, Any]]:
    """
    Parse a single JSONL line safely.

    Args:
        line: Raw JSONL line

    Returns:
        Parsed JSON object or None if invalid
    """
    try:
        line = line.strip()
        if not line:
            return None
        return json.loads(line)
    except json.JSONDecodeError as e:
        logger.debug(f"Invalid JSON line: {e}")
        return None
    except Exception as e:
        logger.warning(f"Error parsing JSONL line: {e}")
        return None


def read_transcript_backwards(
    transcript_path: str,
    max_lines: int = 50,
    start_line: int = None,
    end_line: int = None,
) -> List[Dict[str, Any]]:
    """
    Read JSONL transcript file backwards for efficiency.

    Reads from the end of the file to quickly find recent conversation context.
    Can optionally specify a line range for testing specific portions.

    Args:
        transcript_path: Path to JSONL transcript file
        max_lines: Maximum number of lines to read from end (ignored if start_line/end_line specified)
        start_line: Starting line number (1-indexed, inclusive) for range selection
        end_line: Ending line number (1-indexed, inclusive) for range selection

    Returns:
        List of parsed JSON objects in reverse chronological order
    """
    try:
        transcript_file = Path(transcript_path)
        if not transcript_file.exists():
            logger.warning(f"Transcript file not found: {transcript_path}")
            return []

        entries = []
        with open(transcript_file, "r", encoding="utf-8") as f:
            # Read all lines
            all_lines = f.readlines()

            # Select lines based on parameters
            if start_line is not None or end_line is not None:
                # Use line range if specified (convert to 0-indexed)
                start_idx = (start_line - 1) if start_line else 0
                end_idx = end_line if end_line else len(all_lines)
                selected_lines = all_lines[start_idx:end_idx]
                logger.debug(
                    f"Using line range {start_line or 1}-{end_line or len(all_lines)} ({len(selected_lines)} lines)"
                )
            else:
                # Use max_lines from end (original behavior)
                selected_lines = (
                    all_lines[-max_lines:] if len(all_lines) > max_lines else all_lines
                )
                logger.debug(f"Using last {len(selected_lines)} lines from end")

            # Parse lines in reverse order (newest first)
            for line in reversed(selected_lines):
                entry = parse_jsonl_line(line)
                if entry:
                    entries.append(entry)

        logger.debug(f"Read {len(entries)} entries from transcript: {transcript_path}")
        return entries

    except Exception as e:
        logger.error(f"Error reading transcript file {transcript_path}: {e}")
        return []


def extract_conversation_context(
    transcript_path: str, start_line: int = None, end_line: int = None
) -> ConversationContext:
    """
    Extract conversation context from Claude Code transcript file.

    Finds the last user prompt and Claude's response by parsing JSONL backwards.
    Special handling for Stop events: if there's a Stop event in the same session,
    only consider user prompts and Claude responses after the last Stop event.

    Logic:
    1. If no Stop event exists in session -> use last user prompt and Claude response
    2. If Stop event exists -> only use user prompt and Claude response after the last Stop event
    3. If Stop event exists but no messages after it -> return empty context (expected behavior)

    Args:
        transcript_path: Path to Claude Code JSONL transcript file
        start_line: Starting line number (1-indexed, inclusive) for range selection
        end_line: Ending line number (1-indexed, inclusive) for range selection

    Returns:
        ConversationContext with extracted information
    """
    try:
        if not transcript_path:
            logger.warning("No transcript path provided")
            return ConversationContext()

        # Read recent entries from transcript
        entries = read_transcript_backwards(
            transcript_path, start_line=start_line, end_line=end_line
        )
        if not entries:
            logger.info("No entries found in transcript")
            return ConversationContext()

        last_user_prompt = None
        last_claude_response = None
        session_id = None
        found_stop_event = False
        stop_event_index = -1

        # First pass: Extract session ID and find Stop events
        for i, entry in enumerate(entries):
            try:
                # Extract session ID if available
                if not session_id and "sessionId" in entry:
                    session_id = entry["sessionId"]

                # Check for Stop events (hook events with "Stop" name)
                if entry.get("type") == "hook" and entry.get("hookEventName") == "Stop":
                    found_stop_event = True
                    stop_event_index = i
                    logger.debug(f"Found Stop event at index {i}")
                    break  # We only care about the most recent Stop event

            except Exception as e:
                logger.debug(f"Error processing entry in first pass: {e}")
                continue

        # Second pass: Find user message and Claude response
        # If Stop event found, only look at entries before the Stop event index
        search_entries = entries[:stop_event_index] if found_stop_event else entries

        logger.debug(
            f"Searching {len(search_entries)} entries {'after last Stop event' if found_stop_event else 'from end'}"
        )

        for entry in search_entries:
            try:
                # Skip meta messages and system messages
                if entry.get("isMeta") or entry.get("type") == "system":
                    continue

                # Look for user messages
                if entry.get("type") == "user" and not last_user_prompt:
                    message = entry.get("message", {})
                    content = extract_message_content(message)
                    if content:
                        last_user_prompt = content
                        logger.debug(
                            f"Found user prompt {'after Stop event' if found_stop_event else ''}: {content[:50]}..."
                        )
                        # Debug logging for full user prompt
                        logger.info(f"User Prompt (session: {session_id}): {content}")

                # Look for assistant messages
                if entry.get("type") == "assistant" and not last_claude_response:
                    message = entry.get("message", {})
                    content = extract_message_content(message)
                    if content:
                        # Check if we've already processed this Claude response
                        current_message_hash = _get_message_hash(entry)
                        last_processed_hash = (
                            _get_last_processed_message(session_id)
                            if session_id
                            else None
                        )

                        if (
                            last_processed_hash
                            and current_message_hash == last_processed_hash
                        ):
                            logger.debug(
                                f"Skipping already processed Claude response: {current_message_hash}"
                            )
                            # Return empty context to avoid reprocessing
                            return ConversationContext(session_id=session_id)

                        last_claude_response = content

                        # Debug logging for full Claude response
                        logger.info(
                            f"Claude Response (session: {session_id}): {content}"
                        )

                        # Save this as the last processed message
                        if session_id:
                            _save_last_processed_message(
                                session_id, current_message_hash
                            )

                        logger.debug(
                            f"Found Claude response {'after Stop event' if found_stop_event else ''}: {content[:50]}..."
                        )

                # Stop if we found both
                if last_user_prompt and last_claude_response:
                    break

            except Exception as e:
                logger.debug(f"Error processing entry: {e}")
                continue

        # If Stop event was found but no messages after it, that's expected
        if found_stop_event:
            if not last_claude_response:
                logger.debug(
                    "Stop event found but no Claude response after it - this is expected"
                )
            if not last_user_prompt:
                logger.debug(
                    "Stop event found but no user prompt after it - this is expected"
                )

        context = ConversationContext(
            last_user_prompt=last_user_prompt,
            last_claude_response=last_claude_response,
            session_id=session_id,
        )

        if context.has_context():
            logger.info(
                f"Successfully extracted conversation context from {transcript_path}"
                f"{' (after Stop event)' if found_stop_event else ''}"
            )
            # Debug logging for final extracted context
            logger.info(
                f"Final User Prompt (session: {session_id}): {last_user_prompt}"
            )
            logger.info(
                f"Final Claude Response (session: {session_id}): {last_claude_response}"
            )
        else:
            logger.info("No meaningful conversation context found")
            logger.debug(
                f"No context - User Prompt: {last_user_prompt}, Claude Response: {last_claude_response}"
            )

        return context

    except Exception as e:
        logger.error(f"Error extracting conversation context: {e}")
        return ConversationContext()


def main():
    """CLI entry point for transcript parser."""
    parser = argparse.ArgumentParser(
        description="Extract conversation context from Claude Code transcript files"
    )
    parser.add_argument(
        "transcript_path", help="Path to Claude Code JSONL transcript file"
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument(
        "--start-line",
        type=int,
        help="Starting line number (1-indexed, inclusive) for range selection",
    )
    parser.add_argument(
        "--end-line",
        type=int,
        help="Ending line number (1-indexed, inclusive) for range selection",
    )
    parser.add_argument(
        "--skip-duplicate-check",
        action="store_true",
        help="Skip duplicate processing check (useful for testing)",
    )

    args = parser.parse_args()

    # Configure logging
    level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")

    # Extract conversation context
    if args.skip_duplicate_check:
        # Temporarily disable duplicate checking by clearing processed files
        import tempfile

        old_claude_instances = Path(".claude-instances")
        if old_claude_instances.exists():
            temp_backup = Path(tempfile.mkdtemp()) / "claude-instances-backup"
            old_claude_instances.rename(temp_backup)

        try:
            context = extract_conversation_context(
                args.transcript_path, start_line=args.start_line, end_line=args.end_line
            )
        finally:
            # Restore backup
            if "temp_backup" in locals() and temp_backup.exists():
                if Path(".claude-instances").exists():
                    import shutil

                    shutil.rmtree(".claude-instances")
                temp_backup.rename(".claude-instances")
    else:
        context = extract_conversation_context(
            args.transcript_path, start_line=args.start_line, end_line=args.end_line
        )

    # Output results
    if args.format == "json":
        import json

        print(json.dumps(context.to_dict(), indent=2))
    else:
        if context.has_context():
            if context.last_user_prompt:
                print(f"Last User Prompt: {context.last_user_prompt}")
            if context.last_claude_response:
                print(f"Last Claude Response: {context.last_claude_response}")
            if context.session_id:
                print(f"Session ID: {context.session_id}")
        else:
            print("No conversation context found")

    return 0


if __name__ == "__main__":
    exit(main())
