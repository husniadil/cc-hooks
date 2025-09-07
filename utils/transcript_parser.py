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
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


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
        return bool(self.last_user_prompt or self.last_claude_response)


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
        if not message_data or "content" not in message_data:
            return None

        content = message_data["content"]

        # Handle string content directly
        if isinstance(content, str):
            return content.strip() if content.strip() else None

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

        return None

    except Exception as e:
        logger.warning(f"Error extracting message content: {e}")
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
    transcript_path: str, max_lines: int = 50
) -> List[Dict[str, Any]]:
    """
    Read JSONL transcript file backwards for efficiency.

    Reads from the end of the file to quickly find recent conversation context.

    Args:
        transcript_path: Path to JSONL transcript file
        max_lines: Maximum number of lines to read from end

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
            # Read all lines and take the last max_lines
            all_lines = f.readlines()
            recent_lines = (
                all_lines[-max_lines:] if len(all_lines) > max_lines else all_lines
            )

            # Parse lines in reverse order (newest first)
            for line in reversed(recent_lines):
                entry = parse_jsonl_line(line)
                if entry:
                    entries.append(entry)

        logger.debug(f"Read {len(entries)} entries from transcript: {transcript_path}")
        return entries

    except Exception as e:
        logger.error(f"Error reading transcript file {transcript_path}: {e}")
        return []


def extract_conversation_context(transcript_path: str) -> ConversationContext:
    """
    Extract conversation context from Claude Code transcript file.

    Finds the last user prompt and Claude's response by parsing JSONL backwards.

    Args:
        transcript_path: Path to Claude Code JSONL transcript file

    Returns:
        ConversationContext with extracted information
    """
    try:
        if not transcript_path:
            logger.warning("No transcript path provided")
            return ConversationContext()

        # Read recent entries from transcript
        entries = read_transcript_backwards(transcript_path)
        if not entries:
            logger.info("No entries found in transcript")
            return ConversationContext()

        last_user_prompt = None
        last_claude_response = None
        session_id = None

        # Find last user message and Claude response
        for entry in entries:
            try:
                # Extract session ID if available
                if not session_id and "sessionId" in entry:
                    session_id = entry["sessionId"]

                # Skip meta messages and system messages
                if entry.get("isMeta") or entry.get("type") == "system":
                    continue

                # Look for user messages
                if entry.get("type") == "user" and not last_user_prompt:
                    message = entry.get("message", {})
                    content = extract_message_content(message)
                    if content and not content.startswith(
                        "<command-"
                    ):  # Skip command messages
                        last_user_prompt = content
                        logger.debug(f"Found user prompt: {content[:50]}...")

                # Look for assistant messages
                if entry.get("type") == "assistant" and not last_claude_response:
                    message = entry.get("message", {})
                    content = extract_message_content(message)
                    if content:
                        last_claude_response = content
                        logger.debug(f"Found Claude response: {content[:50]}...")

                # Stop if we found both
                if last_user_prompt and last_claude_response:
                    break

            except Exception as e:
                logger.debug(f"Error processing entry: {e}")
                continue

        context = ConversationContext(
            last_user_prompt=last_user_prompt,
            last_claude_response=last_claude_response,
            session_id=session_id,
        )

        if context.has_context():
            logger.info(
                f"Successfully extracted conversation context from {transcript_path}"
            )
        else:
            logger.info("No meaningful conversation context found")

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

    args = parser.parse_args()

    # Configure logging
    level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")

    # Extract conversation context
    context = extract_conversation_context(args.transcript_path)

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
