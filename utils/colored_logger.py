"""
Simple colored logging utility that matches uvicorn's format.
Provides consistent spacing and per-component coloring.
"""

import logging
import sys


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
        # Match uvicorn's format: "INFO:     component:message"
        level_color = self.COLORS.get(record.levelname, "")
        component = record.name
        message = record.getMessage()

        # Format with proper spacing like uvicorn (5 spaces after colon)
        formatted = (
            f"{level_color}{record.levelname}:{self.RESET}     {component}:{message}"
        )

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

    # Only add handler if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = ColoredFormatter()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False

    return logger


def configure_root_logging():
    """Configure root logging to match uvicorn style."""
    # Only configure if not already done
    root_logger = logging.getLogger()
    if not any(isinstance(h.formatter, ColoredFormatter) for h in root_logger.handlers):
        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Add our custom handler
        handler = logging.StreamHandler(sys.stdout)
        formatter = ColoredFormatter()
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)
