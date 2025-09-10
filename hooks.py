#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "requests",
#     "openai",
#     "gtts",
#     "elevenlabs",
#     "pygame",
#     "python-dotenv",
# ]
# ///

# Claude Code hooks entry point
# Receives hook events from Claude Code via stdin and forwards them to the API server

import json
import os
import sys
import requests
from typing import Dict, Any, Optional
from config import config
from utils.colored_logger import setup_logger, configure_root_logging

configure_root_logging()
logger = setup_logger(__name__)


def read_json_from_stdin() -> Dict[Any, Any]:
    """Read and parse JSON data from stdin."""
    try:
        data = sys.stdin.read()
        if not data.strip():
            raise ValueError("No data received from stdin")

        return json.loads(data)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON format - {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error reading from stdin: {e}")
        sys.exit(1)


def send_to_api(
    event_data: Dict[Any, Any], arguments: Optional[Dict[str, Any]] = None
) -> bool:
    """Send event data to the API endpoint."""
    # Use port from environment variable set by claude.sh, fallback to default
    port = os.getenv("CC_HOOKS_PORT", "12222")
    api_url = f"http://localhost:{port}/events"

    try:
        payload = {"data": event_data}
        if arguments:
            payload["arguments"] = arguments

        # Add instance_id from environment variable if available
        instance_id = os.getenv("CC_INSTANCE_ID")
        if instance_id:
            payload["instance_id"] = instance_id

        response = requests.post(api_url, json=payload, timeout=30)
        response.raise_for_status()

        response.json()  # Validate JSON response
        return True

    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending request to API: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False


def parse_custom_arguments():
    """
    Parse any --key=value or --flag arguments dynamically.
    This makes the script scalable for future parameter additions.
    """
    arguments = {}

    # Process command line arguments manually to support any --key=value format
    i = 1  # Skip script name
    while i < len(sys.argv):
        arg = sys.argv[i]

        if arg.startswith("--"):
            key = arg[2:]  # Remove '--' prefix

            if "=" in key:
                # Handle --key=value format
                key, value = key.split("=", 1)
                # Convert dashes to underscores for Python-friendly keys
                key = key.replace("-", "_")
                arguments[key] = value
            else:
                # Handle --flag format (boolean)
                # Convert dashes to underscores for Python-friendly keys
                key = key.replace("-", "_")
                arguments[key] = True

        i += 1

    return arguments


def main():
    """Main function to handle the hook process."""
    # Parse any custom arguments dynamically
    arguments = parse_custom_arguments()

    event_data = read_json_from_stdin()
    success = send_to_api(event_data, arguments if arguments else None)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
