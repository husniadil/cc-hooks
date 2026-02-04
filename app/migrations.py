# Database migration system for Claude Code hooks
# Manages schema changes and version tracking for SQLite database

import aiosqlite
from typing import Dict, Any
from pathlib import Path
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
    {
        "version": 4,
        "description": "Add database indexes for query optimization",
        "sql": "CREATE INDEX IF NOT EXISTS idx_events_processing ON events (instance_id, status, created_at, id)",
    },
    {
        "version": 5,
        "description": "Add session_id index for debugging support",
        "sql": "CREATE INDEX IF NOT EXISTS idx_events_session ON events (session_id)",
    },
    {
        "version": 6,
        "description": "Create version_checks table for update tracking",
        "sql": """
            CREATE TABLE IF NOT EXISTS version_checks (
                id INTEGER PRIMARY KEY,
                current_version TEXT NOT NULL,
                latest_version TEXT NOT NULL,
                commits_behind INTEGER NOT NULL,
                update_available INTEGER NOT NULL,
                last_checked TEXT NOT NULL,
                error TEXT NULL
            )
        """,
    },
    {
        "version": 7,
        "description": "Create sessions table with complete schema",
        "sql": """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                claude_pid INTEGER NOT NULL,
                server_port INTEGER NOT NULL,
                tts_language TEXT NULL,
                tts_providers TEXT NULL,
                tts_cache_enabled INTEGER DEFAULT 1,
                elevenlabs_voice_id TEXT NULL,
                elevenlabs_model_id TEXT NULL,
                silent_announcements INTEGER DEFAULT 0,
                silent_effects INTEGER DEFAULT 0,
                openrouter_enabled INTEGER DEFAULT 0,
                openrouter_model TEXT NULL,
                openrouter_contextual_stop INTEGER DEFAULT 0,
                openrouter_contextual_pretooluse INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
    },
    {
        "version": 8,
        "description": "Drop suboptimal idx_events_processing index (fix v4/v8 conflict)",
        "sql": "DROP INDEX IF EXISTS idx_events_processing",
    },
    {
        "version": 9,
        "description": "Create optimized events index for query performance",
        "sql": "CREATE INDEX IF NOT EXISTS idx_events_processing ON events (status, created_at, id)",
    },
    {
        "version": 10,
        "description": "Create index on sessions claude_pid",
        "sql": "CREATE INDEX IF NOT EXISTS idx_sessions_claude_pid ON sessions (claude_pid)",
    },
    {
        "version": 11,
        "description": "Drop arguments column from events table",
        "sql": "ALTER TABLE events DROP COLUMN arguments",
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
        return result[0] if result and result[0] is not None else 0


async def apply_migration(migration: Dict[str, Any]):
    """Apply a single migration"""
    async with aiosqlite.connect(config.db_path) as db:
        # Execute the migration SQL - handle multiple statements
        sql_statements = [
            stmt.strip() for stmt in migration["sql"].split(";") if stmt.strip()
        ]

        for statement in sql_statements:
            await db.execute(statement)

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
    # Ensure database parent directory exists
    db_path = Path(config.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    await create_migrations_table()
    current_version = await get_current_version()

    pending_migrations = [m for m in MIGRATIONS if (m["version"] or 0) > current_version]  # type: ignore[operator]

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
    latest_version = max((m["version"] or 0) for m in MIGRATIONS) if MIGRATIONS else 0  # type: ignore[type-var,arg-type]
    pending_count = len([m for m in MIGRATIONS if (m["version"] or 0) > current_version])  # type: ignore[operator]

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
