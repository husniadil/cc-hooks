#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "requests",
# ]
# ///

# Claude Code hooks entry point
# Receives hook events from Claude Code via stdin and forwards them to the API server

import json
import sys
import requests
from typing import Dict, Any
from app.config import config


def read_json_from_stdin() -> Dict[Any, Any]:
    """Read and parse JSON data from stdin."""
    try:
        data = sys.stdin.read()
        if not data.strip():
            raise ValueError("No data received from stdin")

        return json.loads(data)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format - {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading from stdin: {e}", file=sys.stderr)
        sys.exit(1)


def send_to_api(event_data: Dict[Any, Any]) -> bool:
    """Send event data to the API endpoint."""
    api_url = f"http://{config.host}:{config.port}/events"

    try:
        payload = {"data": event_data}
        response = requests.post(api_url, json=payload, timeout=30)
        response.raise_for_status()

        result = response.json()
        print(f"Success: Event queued with ID {result.get('event_id')}")
        return True

    except requests.exceptions.RequestException as e:
        print(f"Error sending request to API: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return False


def main():
    """Main function to handle the hook process."""
    event_data = read_json_from_stdin()
    success = send_to_api(event_data)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
