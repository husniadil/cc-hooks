#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#     "aiosqlite>=0.21.0,<0.22",
# ]
# ///
"""
Version checking utility for cc-hooks update mechanism.

Provides Git-based version checking to detect available updates by comparing
local repository state with remote origin. Results are cached to minimize
network overhead and API rate limiting.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

from utils.colored_logger import setup_logger

logger = setup_logger(__name__)

# Cache duration for version checks (1 hour)
CACHE_DURATION_HOURS = 1


def _resolve_repo_root() -> Path:
    """
    Resolve the actual git repository root.

    Handles plugin mode where code runs from cache directory but git repo
    is in marketplace directory.

    Resolution order:
    1. If running from plugin cache → use marketplace directory
    2. Otherwise → use parent of utils/ directory
    """
    file_path = Path(__file__).resolve()
    default_root = file_path.parent.parent

    # Check if running from plugin cache directory
    # Pattern: ~/.claude/plugins/cache/cc-hooks-plugin/cc-hooks/{version}/
    path_str = str(file_path)
    if "/.claude/plugins/cache/cc-hooks-plugin/" in path_str:
        # Resolve to marketplace directory which has .git
        marketplace_path = Path.home() / ".claude/plugins/marketplaces/cc-hooks-plugin"
        if marketplace_path.exists() and (marketplace_path / ".git").exists():
            logger.debug(
                f"Resolved repo root from cache to marketplace: {marketplace_path}"
            )
            return marketplace_path

    return default_root


# Path to repo root (handles both standalone and plugin modes)
REPO_ROOT = _resolve_repo_root()


class VersionCheckResult:
    """Result of a version check operation."""

    def __init__(
        self,
        current_version: str,
        latest_version: str,
        commits_behind: int,
        update_available: bool,
        last_checked: datetime,
        error: Optional[str] = None,
    ):
        self.current_version = current_version
        self.latest_version = latest_version
        self.commits_behind = commits_behind
        self.update_available = update_available
        self.last_checked = last_checked
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for JSON serialization."""
        return {
            "current_version": self.current_version,
            "latest_version": self.latest_version,
            "commits_behind": self.commits_behind,
            "update_available": self.update_available,
            "last_checked": self.last_checked.isoformat(),
            "error": self.error,
        }


class VersionChecker:
    """Manages version checking with caching support."""

    def __init__(self, db_path: str = "events.db"):
        self.db_path = db_path
        self._cached_result: Optional[VersionCheckResult] = None
        self._cache_expires_at: Optional[datetime] = None

    async def check_for_updates(
        self, force: bool = False
    ) -> Optional[VersionCheckResult]:
        """
        Check if updates are available for cc-hooks.

        Args:
            force: Skip cache and force fresh check

        Returns:
            VersionCheckResult with update status, or None on failure
        """
        # Return cached result if still valid
        if not force and self._is_cache_valid():
            logger.debug("Returning cached version check result")
            return self._cached_result

        logger.info("Checking for cc-hooks updates...")

        try:
            # Get current version from git describe
            current_version = await self._get_current_version()
            if not current_version:
                return self._create_error_result("Failed to get current version")

            # Fetch latest from remote (with timeout)
            fetch_success = await self._git_fetch()
            if not fetch_success:
                return self._create_error_result("Failed to fetch from remote")

            # Get latest remote version
            latest_version = await self._get_latest_remote_version()
            if not latest_version:
                return self._create_error_result("Failed to get remote version")

            # Count commits behind
            commits_behind = await self._count_commits_behind()

            # Create result
            result = VersionCheckResult(
                current_version=current_version,
                latest_version=latest_version,
                commits_behind=commits_behind,
                update_available=commits_behind > 0,
                last_checked=datetime.now(timezone.utc),
            )

            # Cache result
            self._cached_result = result
            self._cache_expires_at = datetime.now(timezone.utc) + timedelta(
                hours=CACHE_DURATION_HOURS
            )

            # Persist to database
            await self._save_to_db(result)

            if result.update_available:
                logger.info(
                    f"Update available: {current_version} → {latest_version} ({commits_behind} commits behind)"
                )
            else:
                logger.info(f"Up to date: {current_version}")

            return result

        except Exception as e:
            logger.error(f"Version check failed: {e}")
            return self._create_error_result(str(e))

    async def _get_current_version(self) -> Optional[str]:
        """Get current version using git describe."""
        try:
            result = await self._run_git_command(
                ["describe", "--tags", "--always", "--dirty"]
            )
            return result.strip() if result else None
        except Exception as e:
            logger.error(f"Failed to get current version: {e}")
            return None

    async def _get_latest_remote_version(self) -> Optional[str]:
        """Get latest version from remote origin/main."""
        try:
            result = await self._run_git_command(
                ["describe", "--tags", "--always", "origin/main"]
            )
            return result.strip() if result else None
        except Exception as e:
            logger.error(f"Failed to get remote version: {e}")
            return None

    async def _git_fetch(self) -> bool:
        """Fetch latest from remote origin (with timeout)."""
        try:
            # Run git fetch with 10 second timeout
            await self._run_git_command(["fetch", "origin"], timeout=10)
            logger.debug("Git fetch completed successfully")
            return True
        except asyncio.TimeoutError:
            logger.warning("Git fetch timed out after 10 seconds")
            return False
        except Exception as e:
            logger.error(f"Git fetch failed: {e}")
            return False

    async def _count_commits_behind(self) -> int:
        """Count how many commits behind origin/main we are."""
        try:
            result = await self._run_git_command(
                ["rev-list", "--count", "HEAD..origin/main"]
            )
            return int(result.strip()) if result else 0
        except Exception as e:
            logger.error(f"Failed to count commits: {e}")
            return 0

    async def _run_git_command(
        self, args: list[str], timeout: int = 5
    ) -> Optional[str]:
        """
        Run a git command asynchronously.

        Args:
            args: Git command arguments (without 'git' prefix)
            timeout: Command timeout in seconds

        Returns:
            Command stdout output or None on failure
        """
        cmd = ["git", "-C", str(REPO_ROOT)] + args
        logger.debug(f"Running: {' '.join(cmd)}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )

            if process.returncode != 0:
                logger.error(f"Git command failed: {stderr.decode().strip()}")
                return None

            return stdout.decode()

        except asyncio.TimeoutError:
            logger.error(f"Git command timed out after {timeout}s")
            try:
                process.terminate()
                await asyncio.wait_for(process.wait(), timeout=5)
            except Exception:
                process.kill()
            return None
        except Exception as e:
            logger.error(f"Git command error: {e}")
            return None

    def _is_cache_valid(self) -> bool:
        """Check if cached result is still valid."""
        if not self._cached_result or not self._cache_expires_at:
            return False
        return datetime.now(timezone.utc) < self._cache_expires_at

    def _create_error_result(self, error_msg: str) -> VersionCheckResult:
        """Create error result for failed checks."""
        return VersionCheckResult(
            current_version="unknown",
            latest_version="unknown",
            commits_behind=0,
            update_available=False,
            last_checked=datetime.now(timezone.utc),
            error=error_msg,
        )

    async def _save_to_db(self, result: VersionCheckResult) -> None:
        """Save version check result to database for persistence."""
        try:
            import aiosqlite

            async with aiosqlite.connect(self.db_path) as db:
                # Check if version_checks table exists
                cursor = await db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='version_checks'"
                )
                if not await cursor.fetchone():
                    logger.debug(
                        "version_checks table not found, skipping database save"
                    )
                    return

                # Insert or replace latest check result
                await db.execute(
                    """
                    INSERT OR REPLACE INTO version_checks
                    (id, current_version, latest_version, commits_behind, update_available, last_checked, error)
                    VALUES (1, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.current_version,
                        result.latest_version,
                        result.commits_behind,
                        result.update_available,
                        result.last_checked.isoformat(),
                        result.error,
                    ),
                )
                await db.commit()
                logger.debug("Version check result saved to database")

        except Exception as e:
            logger.warning(f"Failed to save version check to database: {e}")

    async def load_from_db(self) -> Optional[VersionCheckResult]:
        """Load last version check result from database."""
        try:
            import aiosqlite

            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT current_version, latest_version, commits_behind, update_available, last_checked, error FROM version_checks WHERE id = 1"
                )
                row = await cursor.fetchone()

                if not row:
                    return None

                return VersionCheckResult(
                    current_version=row[0],
                    latest_version=row[1],
                    commits_behind=row[2],
                    update_available=bool(row[3]),
                    last_checked=datetime.fromisoformat(row[4]),
                    error=row[5],
                )

        except Exception as e:
            logger.debug(f"Failed to load version check from database: {e}")
            return None


# CLI interface for testing
async def main():
    """Test version checker from command line."""
    import sys

    checker = VersionChecker()

    force = "--force" in sys.argv

    result = await checker.check_for_updates(force=force)

    if not result:
        print("Version check failed")
        sys.exit(1)

    print(f"Current version:  {result.current_version}")
    print(f"Latest version:   {result.latest_version}")
    print(f"Commits behind:   {result.commits_behind}")
    print(f"Update available: {result.update_available}")
    print(f"Last checked:     {result.last_checked.isoformat()}")

    if result.error:
        print(f"Error: {result.error}")

    sys.exit(0 if not result.error else 1)


if __name__ == "__main__":
    asyncio.run(main())
