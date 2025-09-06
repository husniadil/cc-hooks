# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this
repository.

## Project Overview

This is a Claude Code hooks processing system that acts as a middleware server to handle Claude Code
hook events. The system queues events from Claude Code hooks into a SQLite database and processes
them sequentially, allowing for complex event handling workflows without blocking Claude Code
operations.

## Architecture

The system consists of three main components:

1. **Hook Script** (`hooks.py`) - Receives hook events from Claude Code via stdin and forwards them
   to the API server
2. **API Server** (`server.py`) - FastAPI server that receives events, queues them in SQLite, and
   runs the background processor
3. **Claude Wrapper** (`claude.sh`) - Bash script that manages server lifecycle and launches Claude
   Code with hooks enabled

The event flow:

1. Claude Code triggers a hook (PreToolUse, PostToolUse, etc.)
2. Hook script receives JSON via stdin and posts to API endpoint
3. API server queues event to SQLite database
4. Background processor handles events sequentially with retry logic

## Development Commands

### Running the System

```bash
# Start the server and Claude Code (recommended way)
./claude.sh

# Start only the server (for development/testing)
uv run server.py

# Test the hook script manually
echo '{"session_id": "test", "hook_event_name": "Test"}' | uv run hooks.py

# Test with sound effect arguments
echo '{"session_id": "test", "hook_event_name": "Test"}' | uv run hooks.py --sound-effect=sound_effect_tek.mp3

# Test with multiple arguments
echo '{"session_id": "test", "hook_event_name": "Test"}' | uv run hooks.py --sound-effect=sound_effect_cetek.mp3 --debug
```

### API Health Check

```bash
# Check if server is running
curl http://localhost:12345/health

# Check event queue status
curl http://localhost:12345/events/status

# Check migration status
curl http://localhost:12345/migrations
```

### API Usage Examples

```bash
# Submit event without arguments
curl -X POST http://localhost:12345/events \
  -H "Content-Type: application/json" \
  -d '{"data": {"session_id": "test", "hook_event_name": "SessionStart"}}'

# Submit event with sound effect argument
curl -X POST http://localhost:12345/events \
  -H "Content-Type: application/json" \
  -d '{"data": {"session_id": "test", "hook_event_name": "PostToolUse"}, "arguments": {"sound_effect": "sound_effect_tek.mp3"}}'

# Submit event with multiple arguments
curl -X POST http://localhost:12345/events \
  -H "Content-Type: application/json" \
  -d '{"data": {"session_id": "test", "hook_event_name": "PreToolUse"}, "arguments": {"sound_effect": "sound_effect_cetek.mp3", "debug": true}}'
```

### Database Management

```bash
# View events in database
sqlite3 events.db "SELECT * FROM events ORDER BY created_at DESC LIMIT 10;"

# View events with arguments
sqlite3 events.db "SELECT id, session_id, hook_event_name, arguments, status FROM events ORDER BY created_at DESC LIMIT 10;"

# Clear failed events
sqlite3 events.db "DELETE FROM events WHERE status = 'failed';"

# Check database schema after migrations
sqlite3 events.db ".schema events"
```

### Development Workflow

#### Before Every Commit

Always follow this workflow before committing changes:

```bash
# 1. Format all code (Python + Prettier)
npm run format

# 2. Update changelog and version (REQUIRED)
# - Update CHANGELOG.md [Unreleased] section with changes
# - Increment version in package.json
# - Verify both files appear in git diff

# 3. Verify changes are ready
git status  # Should show CHANGELOG.md, package.json, and formatted files
git diff   # Should show changelog and version updates

# 4. Standard commit workflow
git add .
git commit -m "Your commit message"

# 5. Optional: Run integration test after commit
./claude.sh  # Verify system still works
```

**IMPORTANT**: CHANGELOG.md and package.json MUST be updated and appear in git diff before every
commit. This ensures proper version tracking and release management.

#### Development Testing

```bash
# Quick development server test
npm run dev  # Start server only

# Full integration test
npm run start  # Start server + Claude Code wrapper

# Manual hook testing
echo '{"session_id": "test", "hook_event_name": "Test"}' | uv run hooks.py --sound-effect=sound_effect_tek.mp3
```

### Changelog and Release Management

The project follows semantic versioning and maintains a detailed changelog:

```bash
# Development workflow (no changelog needed)
# - Bug fixes and improvements during active development
# - Update documentation as needed
# - Commit changes without changelog entries

# Pre-release workflow (update CHANGELOG.md)
# 1. Review all changes since last version
git log --oneline v0.1.0..HEAD

# 2. Update CHANGELOG.md [Unreleased] section with:
#    - Added: new features
#    - Changed: modifications to existing functionality
#    - Deprecated: features marked for removal
#    - Removed: deleted features
#    - Fixed: bug fixes
#    - Security: vulnerability fixes

# 3. Test thoroughly before release
npm run format
./claude.sh  # Integration test

# Release workflow
# 1. Move [Unreleased] changes to new version section in CHANGELOG.md
# 2. Update package.json version
# 3. Commit and tag release
git add CHANGELOG.md package.json
git commit -m "Release v0.x.x"
git tag v0.x.x

# Version strategy:
# - 0.x.x: Development phase (current)
# - 1.x.x: Production ready (stable API, full testing, deployment docs)
```

### Server Lifecycle Troubleshooting

```bash
# Check server status and active instances
curl http://localhost:12345/health
ls -la .claude-instances/

# Force cleanup if server is stuck
pkill -f "uv run.*server.py"
rm -rf .claude-instances/

# Debug server startup issues
uv run server.py  # Run server directly to see errors

# Monitor server logs during startup
./claude.sh > /dev/null &  # Start in background
tail -f /dev/null  # Or check server logs if available
```

## Key Implementation Details

### Dependencies

This project uses `uv` for Python dependency management. Dependencies are declared inline in script
headers using PEP 723 format. The main dependencies are:

- FastAPI/Uvicorn for the API server
- aiosqlite for async database operations
- requests for HTTP client in hooks
- python-dotenv for environment configuration

### Database Migrations

The system includes an automatic migration system for database schema updates:

- **Migration Tracking**: Migrations are tracked in a `migrations` table with version numbers
- **Automatic Execution**: Migrations run automatically when the server starts
- **Incremental Updates**: Only new migrations are applied, existing data is preserved
- **Current Migrations**:
  - Version 1: Initial schema with events table
  - Version 2: Added `arguments` column for hook parameters

Migration status can be checked via the `/migrations` API endpoint or by querying the database
directly.

### Configuration

Configuration is managed through environment variables (`.env` file) with defaults:

- `DB_PATH`: SQLite database path (default: "events.db")
- `HOST`: Server host (default: "0.0.0.0")
- `PORT`: Server port (default: 12345)
- `MAX_RETRY_COUNT`: Event retry attempts (default: 3)

### Event Processing

Events are processed with the following characteristics:

- Sequential processing with retry logic (max 3 attempts by default)
- Failed events are marked but not reprocessed automatically
- Each event type (SessionStart, PreToolUse, etc.) can have custom handlers in `event_processor.py`
- Support for hook arguments passed via command line (e.g., sound effects, debug flags)
- Built-in sound effect processing for audible feedback

#### Hook Arguments Support

The system supports dynamic command-line arguments for hooks:

- **Sound Effects**: `--sound-effect=filename.mp3` triggers audio playback during event processing
- **Debug Mode**: `--debug` enables additional logging and debugging features
- **Custom Arguments**: Any `--key=value` or `--flag` format is supported for extensibility

Arguments are stored in the database `arguments` column and passed to event processors for custom
handling.

#### Sound Effects Feature

The system includes built-in sound effect processing:

- Sound files should be placed in the `sound/` directory
- Uses `utils/sound_player.py` for cross-platform audio playback
- Supports common audio formats (WAV, MP3, etc.)
- Synchronous playback to ensure sequential event processing (no sound overlap)
- Graceful error handling if sound files are missing or audio system unavailable

### Server Lifecycle Management

The cc-hooks system implements sophisticated lifecycle management to handle multiple Claude Code
instances sharing a single server:

#### Instance Tracking

- Each Claude Code session registers itself with a unique PID in `.claude-instances/`
- The wrapper script tracks active instances and cleans up stale PID files automatically
- Server is only started if no healthy server exists, and only stopped when the last instance exits

#### Startup Process

1. Clean up any stale instance PID files from previous sessions
2. Register current instance before starting server
3. Check if server is already running via health endpoint
4. If not running, kill any zombie server processes and start fresh
5. Wait up to 10 seconds for server to be ready and responsive
6. If server fails to start or respond, exit with error

#### Shutdown Process

1. Unregister current instance first
2. Count remaining active instances
3. If other instances exist, keep server running
4. If this is the last instance:
   - Gracefully shutdown server with SIGTERM
   - Wait up to 3 seconds for clean shutdown
   - Force kill with SIGKILL if needed
   - Clean up instances directory

#### Server Health Checks

- Health endpoint: `http://localhost:12345/health`
- Connection timeout: 2 seconds
- Used during startup validation and instance management

### Claude Code Integration

The system integrates with Claude Code through its hooks configuration. To use this system:

1. Configure Claude Code hooks to call `hooks.py` in settings
2. Run Claude Code through `claude.sh` wrapper to ensure server is running
3. Events will be queued and processed sequentially

The wrapper handles all server lifecycle management automatically, allowing multiple Claude Code
sessions to share the same event processing server efficiently.

## Important Files

- `hooks.py`: Entry point for Claude Code hooks with dynamic argument parsing
- `server.py`: Main FastAPI server with lifecycle management
- `claude.sh`: Wrapper script for server management
- `app/api.py`: API endpoints for event submission and status with arguments support
- `app/event_db.py`: Database operations for event queue including arguments column
- `app/event_processor.py`: Background processor with event handling logic and sound effects
- `app/config.py`: Configuration management from environment variables
- `app/migrations.py`: Database schema migrations and setup with version tracking
- `utils/sound_player.py`: Cross-platform sound effect playback utility
- `sound/`: Directory for audio files used by sound effects feature
- `status-lines/status_line.py`: Custom Claude Code status line implementation
