"""
Simple colored logging utility that matches uvicorn's format.
Provides consistent spacing and per-component coloring.
"""

import logging
import os
import sys
import re
from pathlib import Path
from datetime import datetime
from utils.constants import DateTimeConstants


def redact_sensitive_data(text: str) -> str:
    """
    Redact sensitive data from log messages to prevent API key exposure.

    Redacts:
    - API keys starting with 'sk-' (OpenAI/OpenRouter style)
    - Bearer tokens in Authorization headers
    - Long hexadecimal strings (40+ chars, likely keys)
    - Environment variables with sensitive names (API_KEY, TOKEN, SECRET, PASSWORD)

    Args:
        text: Log message text to redact

    Returns:
        Text with sensitive data replaced by ***REDACTED***
    """
    if not text:
        return text

    # Redact API keys starting with sk- (OpenAI/OpenRouter/Anthropic style)
    text = re.sub(r"sk-[a-zA-Z0-9_-]{20,}", "sk-***REDACTED***", text)

    # Redact Bearer tokens
    text = re.sub(
        r"Bearer\s+[a-zA-Z0-9_-]{20,}",
        "Bearer ***REDACTED***",
        text,
        flags=re.IGNORECASE,
    )

    # Redact long hexadecimal strings (likely API keys or tokens)
    text = re.sub(r"\b[a-f0-9]{40,}\b", "***REDACTED***", text, flags=re.IGNORECASE)

    # Redact environment variables with sensitive names
    # Matches patterns like: API_KEY=value, "TOKEN": "value", SECRET='value'
    text = re.sub(
        r'(API_KEY|TOKEN|SECRET|PASSWORD|APIKEY)(["\']?\s*[:=]\s*["\']?)([^\s"\',}\]]+)',
        r"\1\2***REDACTED***",
        text,
        flags=re.IGNORECASE,
    )

    return text


class ColoredFormatter(logging.Formatter):
    """Custom formatter that matches uvicorn's spacing and adds colors."""

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # cyan
        "INFO": "\033[32m",  # green
        "WARNING": "\033[33m",  # yellow
        "ERROR": "\033[31m",  # red
        "CRITICAL": "\033[35m",  # magenta
    }
    RESET = "\033[0m"

    def format(self, record):
        """
        Format log record with colors matching uvicorn style.

        Args:
            record: LogRecord instance to format

        Returns:
            Formatted log message with ANSI color codes
        """
        # Match uvicorn's format: "INFO:     component:message"
        level_color = self.COLORS.get(record.levelname, "")
        component = record.name
        message = record.getMessage()

        # Redact sensitive data from message
        message = redact_sensitive_data(message)

        # Format with proper spacing like uvicorn (5 spaces after colon)
        formatted = (
            f"{level_color}{record.levelname}:{self.RESET}     {component}:{message}"
        )

        return formatted


class PlainFormatter(logging.Formatter):
    """Plain formatter for file logging (no colors)."""

    def format(self, record):
        """
        Format log record for file output without colors.

        Args:
            record: LogRecord instance to format

        Returns:
            Formatted log message with timestamp and level
        """
        component = record.name
        message = record.getMessage()
        timestamp = datetime.fromtimestamp(record.created).strftime(
            DateTimeConstants.ISO_DATETIME_FORMAT
        )

        # Redact sensitive data from message
        message = redact_sensitive_data(message)

        # Format: timestamp LEVEL component:message
        formatted = f"{timestamp} {record.levelname:8} {component}:{message}"
        return formatted


def setup_logger(name: str) -> logging.Logger:
    """
    Set up a logger with uvicorn-style formatting.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    log_file = os.getenv("LOG_FILE")

    # Only add handler if not already configured AND not in file-only mode
    if not logger.handlers and not log_file:
        handler = logging.StreamHandler(sys.stdout)
        formatter = ColoredFormatter()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    # Always enable propagation for file logging
    logger.propagate = True
    logger.setLevel(logging.INFO)

    return logger


def setup_file_logging(claude_pid: int, log_dir: str = "logs") -> str:
    """
    Setup file logging for a Claude instance.

    Args:
        claude_pid: Claude process ID for filename
        log_dir: Directory to store logs (default: "logs")

    Returns:
        Path to the log file
    """
    # Create logs directory (including parent directories)
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Simple filename: just PID
    log_file = log_path / f"{claude_pid}.log"

    # Check if file handler already exists for this file
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        if isinstance(handler, logging.FileHandler) and handler.baseFilename == str(
            log_file.absolute()
        ):
            # Already setup, don't add duplicate
            return str(log_file)

    # Add file handler to root logger
    file_handler = logging.FileHandler(log_file, mode="a")  # Append mode
    file_handler.setFormatter(PlainFormatter())
    root_logger.addHandler(file_handler)

    return str(log_file)


def configure_root_logging():
    """Configure root logging to match uvicorn style."""
    # Check if we're in file-only mode (server with LOG_FILE env var)
    log_file = os.getenv("LOG_FILE")

    # Only configure if not already done
    root_logger = logging.getLogger()
    if not any(isinstance(h.formatter, ColoredFormatter) for h in root_logger.handlers):
        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Only add console handler if NOT in file-only mode
        if not log_file:
            handler = logging.StreamHandler(sys.stdout)
            formatter = ColoredFormatter()
            handler.setFormatter(formatter)
            root_logger.addHandler(handler)

        root_logger.setLevel(logging.INFO)
