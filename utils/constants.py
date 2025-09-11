"""
Centralized constants for Claude Code hooks processing system.

This module consolidates all system constants, enums, and configuration values
into a single location for better maintainability and type safety.
"""

from enum import Enum
from typing import Literal

# Re-export HookEvent for convenience
from utils.hooks_constants import HookEvent

__all__ = ["EventStatus", "ProcessingConstants", "DatabaseConstants", "HookEvent"]


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


# Type alias for backward compatibility
EventStatusLiteral = Literal["pending", "processing", "completed", "failed"]
