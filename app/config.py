# Configuration management for Claude Code hooks processing system
# Loads settings from environment variables with sensible defaults

import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class Config:
    """Configuration settings loaded from environment variables."""
    db_path: str = "events.db"
    host: str = "0.0.0.0"
    port: int = 12345
    max_retry_count: int = 3

    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables."""
        return cls(
            db_path=os.getenv("DB_PATH", "events.db"),
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "12345")),
            max_retry_count=int(os.getenv("MAX_RETRY_COUNT", "3")),
        )


config = Config.from_env()
