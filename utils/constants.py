"""
Centralized constants for Claude Code hooks processing system.

This module consolidates all system constants, enums, and configuration values
into a single location for better maintainability and type safety.
"""

from enum import Enum
from typing import Literal

# Re-export HookEvent for convenience
from utils.hooks_constants import HookEvent

__all__ = [
    "EventStatus",
    "ProcessingConstants",
    "DatabaseConstants",
    "DateTimeConstants",
    "NetworkConstants",
    "HTTPStatusConstants",
    "HookEvent",
    "get_server_url",
]


class EventStatus(Enum):
    """
    Event processing status enumeration.

    Provides type safety and prevents typos when working with event status values.
    """

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

    def __str__(self) -> str:
        """Return the string value of the event status."""
        return self.value


class ProcessingConstants:
    """Constants related to event processing timing and behavior."""

    RETRY_DELAY_SECONDS = 0.5
    NO_EVENTS_WAIT_SECONDS = 0.1
    ERROR_WAIT_SECONDS = 5
    DEFAULT_SLEEP_SECONDS = 0.01


class DatabaseConstants:
    """Constants related to database operations and queries."""

    RECENT_EVENTS_LIMIT = 10


class DateTimeConstants:
    """Constants related to date and time formatting."""

    ISO_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class NetworkConstants:
    """Constants related to network operations."""

    DEFAULT_PORT = 12222
    DEFAULT_HOST = "0.0.0.0"
    LOCALHOST = "localhost"


class HTTPStatusConstants:
    """HTTP status code constants for better maintainability."""

    OK = 200
    BAD_REQUEST = 400
    NOT_FOUND = 404
    INTERNAL_SERVER_ERROR = 500


# Type alias for backward compatibility
EventStatusLiteral = Literal["pending", "processing", "completed", "failed"]


# Helper functions
def get_server_url(
    port: int = NetworkConstants.DEFAULT_PORT, endpoint: str = ""
) -> str:
    """
    Generate server URL for API calls.

    Args:
        port: Server port number (defaults to DEFAULT_PORT)
        endpoint: API endpoint path (should start with / if provided)

    Returns:
        Complete server URL with endpoint
    """
    return f"http://{NetworkConstants.LOCALHOST}:{port}{endpoint}"
