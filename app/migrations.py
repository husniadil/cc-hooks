# Database migration system for Claude Code hooks
# Manages schema changes and version tracking for SQLite database

import aiosqlite
from typing import Dict, Any
from config import config
from utils.colored_logger import setup_logger

logger = setup_logger(__name__)

# Migration definitions
MIGRATIONS = [
    {
        "version": 1,
        "description": "Initial events table",
        "sql": """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                hook_event_name TEXT NOT NULL,
                payload TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP NULL,
                retry_count INTEGER DEFAULT 0,
                error_message TEXT NULL
            )
        """,
    },
    # Add future migrations here with incremented version numbers
    {
        "version": 2,
        "description": "Add arguments column for hook parameters",
        "sql": "ALTER TABLE events ADD COLUMN arguments TEXT NULL",
    },
    {
        "version": 3,
        "description": "Add instance_id column for Claude Code instance tracking",
        "sql": "ALTER TABLE events ADD COLUMN instance_id TEXT NULL",
    },
]


async def create_migrations_table():
    """Create the migrations tracking table if it doesn't exist"""
    async with aiosqlite.connect(config.db_path) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS migrations (
                version INTEGER PRIMARY KEY,
                description TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        await db.commit()


async def get_current_version() -> int:
    """Get the current migration version from database"""
    async with aiosqlite.connect(config.db_path) as db:
        cursor = await db.execute("SELECT MAX(version) FROM migrations")
        result = await cursor.fetchone()
        return result[0] if result[0] is not None else 0


async def apply_migration(migration: Dict[str, Any]):
    """Apply a single migration"""
    async with aiosqlite.connect(config.db_path) as db:
        # Execute the migration SQL
        await db.execute(migration["sql"])

        # Record the migration as applied
        await db.execute(
            "INSERT INTO migrations (version, description) VALUES (?, ?)",
            (migration["version"], migration["description"]),
        )

        await db.commit()
        logger.info(
            f"Applied migration {migration['version']}: {migration['description']}"
        )


async def run_migrations():
    """Run all pending migrations"""
    await create_migrations_table()
    current_version = await get_current_version()

    pending_migrations = [m for m in MIGRATIONS if m["version"] > current_version]

    if not pending_migrations:
        logger.info("No pending migrations")
        return

    logger.info(f"Running {len(pending_migrations)} migrations...")

    for migration in pending_migrations:
        await apply_migration(migration)

    logger.info("All migrations completed successfully")


async def get_migration_status() -> Dict[str, Any]:
    """Get current migration status"""
    await create_migrations_table()
    current_version = await get_current_version()
    latest_version = max([m["version"] for m in MIGRATIONS]) if MIGRATIONS else 0
    pending_count = len([m for m in MIGRATIONS if m["version"] > current_version])

    async with aiosqlite.connect(config.db_path) as db:
        cursor = await db.execute(
            "SELECT version, description, applied_at FROM migrations ORDER BY version"
        )
        applied_migrations = await cursor.fetchall()

    return {
        "current_version": current_version,
        "latest_version": latest_version,
        "pending_migrations": pending_count,
        "applied_migrations": [
            {"version": row[0], "description": row[1], "applied_at": row[2]}
            for row in applied_migrations
        ],
    }
