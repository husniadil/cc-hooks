# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this
repository.

## Project Overview

This is a Claude Code hooks processing system that acts as a middleware server to handle Claude Code
hook events. The system queues events from Claude Code hooks into a SQLite database and processes
them asynchronously, allowing for complex event handling workflows without blocking Claude Code
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
4. Background processor handles events asynchronously with retry logic

## Development Commands

### Running the System

```bash
# Start the server and Claude Code (recommended way)
./claude.sh

# Start only the server (for development/testing)
uv run server.py

# Test the hook script manually
echo '{"session_id": "test", "hook_event_name": "Test"}' | uv run hooks.py
```

### API Health Check

```bash
# Check if server is running
curl http://localhost:12345/health

# Check event queue status
curl http://localhost:12345/events/status
```

### Database Management

```bash
# View events in database
sqlite3 events.db "SELECT * FROM events ORDER BY created_at DESC LIMIT 10;"

# Clear failed events
sqlite3 events.db "DELETE FROM events WHERE status = 'failed';"
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

### Configuration

Configuration is managed through environment variables (`.env` file) with defaults:

- `DB_PATH`: SQLite database path (default: "events.db")
- `HOST`: Server host (default: "0.0.0.0")
- `PORT`: Server port (default: 12345)
- `MAX_RETRY_COUNT`: Event retry attempts (default: 3)

### Event Processing

Events are processed with the following characteristics:

- Async processing with retry logic (max 3 attempts by default)
- Failed events are marked but not reprocessed automatically
- Each event type (SessionStart, PreToolUse, etc.) can have custom handlers in `event_processor.py`

### Server Lifecycle Management

The cc-hooks system implements sophisticated lifecycle management to handle multiple Claude Code instances sharing a single server:

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
3. Events will be queued and processed asynchronously

The wrapper handles all server lifecycle management automatically, allowing multiple Claude Code sessions to share the same event processing server efficiently.

## Important Files

- `hooks.py`: Entry point for Claude Code hooks
- `server.py`: Main FastAPI server with lifecycle management
- `claude.sh`: Wrapper script for server management
- `app/api.py`: API endpoints for event submission and status
- `app/event_db.py`: Database operations for event queue
- `app/event_processor.py`: Background processor with event handling logic
- `app/config.py`: Configuration management from environment variables
- `app/migrations.py`: Database schema migrations and setup
- `status-lines/status_line.py`: Custom Claude Code status line implementation
