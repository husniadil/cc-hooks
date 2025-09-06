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
3. **Claude Wrapper** (`claude.sh`) - Bash script that manages server lifecycle, instance tracking,
   and launches Claude Code with hooks enabled

The event flow:

1. Claude Code triggers a hook (PreToolUse, PostToolUse, etc.)
2. Hook script receives JSON via stdin and posts to API endpoint (with instance ID)
3. API server queues event to SQLite database with instance tracking
4. Background processor handles events sequentially with retry logic
5. Optional TTS announcements provide audio feedback for events

## Development Commands

### Running the System

```bash
# Start the server and Claude Code (recommended way)
./claude.sh

# Start only the server (for development/testing)
uv run server.py

# Start server with hot reload for development
uv run server.py --dev
# or
uv run server.py --reload

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

# Submit event with instance ID
curl -X POST http://localhost:12345/events \
  -H "Content-Type: application/json" \
  -d '{"data": {"session_id": "test", "hook_event_name": "SessionEnd"}, "instance_id": "abc-123"}'

# Check instance last event status
curl http://localhost:12345/instances/abc-123/last-event
```

### Database Management

```bash
# View events in database
sqlite3 events.db "SELECT * FROM events ORDER BY created_at DESC LIMIT 10;"

# View events with arguments and instance tracking
sqlite3 events.db "SELECT id, session_id, hook_event_name, arguments, status, instance_id FROM events ORDER BY created_at DESC LIMIT 10;"

# View events for specific instance
sqlite3 events.db "SELECT * FROM events WHERE instance_id = 'your-instance-id' ORDER BY created_at DESC;"

# Clear failed events
sqlite3 events.db "DELETE FROM events WHERE status = 'failed';"

# Check database schema after migrations
sqlite3 events.db ".schema events"
```

### Development Workflow

#### Code Formatting

```bash
# Format all code (Python with Black, JS/JSON with Prettier)
npm run format

# Format Python code only
npm run format:py  # or: black . --line-length 88

# Format JS/JSON/MD only
npm run format:prettier  # or: prettier --write .
```

#### Development Testing

```bash
# Quick development server test with hot reload
npm run dev  # Start server with --dev flag (includes hot reload)

# Alternative: explicit hot reload command
npm run dev:reload  # Start server with --reload flag

# Full integration test
npm run start  # Start server + Claude Code wrapper

# Manual hook testing
echo '{"session_id": "test", "hook_event_name": "Test"}' | uv run hooks.py --sound-effect=sound_effect_tek.mp3
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
  - Version 3: Added `instance_id` column for Claude Code instance tracking

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
- **TTS Announcements**: `--announce=<volume>` enables text-to-speech event announcements (volume:
  0.0-1.0)
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

#### TTS Announcement System

Intelligent context-aware voice announcements for events:

- **Smart Event Mapping**: Maps 19+ different event contexts to appropriate sounds
- **Context Extraction**: Analyzes event data (tool names, session types) for precise sound
  selection
- **Volume Control**: Configurable volume levels (0.0-1.0) via `--announce` argument
- **Comprehensive Coverage**: Unique sounds for all Claude Code hook event types:
  - Session events (startup, resume, clear, logout)
  - Tool events (running, completed, blocked)
  - Notification events (general, permission, waiting)
  - Compact mode events (manual, auto)
- **Testing**: Standalone testing via `uv run utils/tts_announcer.py <event_name>`

### Server Lifecycle Management

The cc-hooks system implements sophisticated lifecycle management to handle multiple Claude Code
instances sharing a single server:

#### Instance Tracking

- Each Claude Code session registers itself with a unique UUID and PID in `.claude-instances/`
- Instance ID (`CC_INSTANCE_ID`) is passed to hook scripts via environment variable
- Events are tracked per instance for better session management
- The wrapper script tracks active instances and cleans up stale PID files automatically
- Server is only started if no healthy server exists, and only stopped when the last instance exits
- Graceful shutdown waits for pending events (up to 10 seconds) before terminating

#### Startup Process

1. Clean up any stale instance PID files from previous sessions
2. Register current instance before starting server
3. Check if server is already running via health endpoint
4. If not running, kill any zombie server processes and start fresh
5. Wait up to 10 seconds for server to be ready and responsive
6. If server fails to start or respond, exit with error

#### Shutdown Process

1. Check for pending events via `/instances/{instance_id}/last-event` endpoint
2. Wait up to 10 seconds for last event to complete
3. Unregister current instance after event completion
4. Count remaining active instances
5. If other instances exist, keep server running
6. If this is the last instance:
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

- `hooks.py`: Entry point for Claude Code hooks with dynamic argument parsing and instance tracking
- `server.py`: Main FastAPI server with lifecycle management and hot reload support
- `claude.sh`: Wrapper script for server management with graceful shutdown
- `app/api.py`: API endpoints for event submission, status, and instance tracking
- `app/event_db.py`: Database operations for event queue with instance support
- `app/event_processor.py`: Background processor with event handling logic and sound effects
- `app/config.py`: Configuration management from environment variables
- `app/migrations.py`: Database schema migrations and setup with version tracking
- `utils/sound_player.py`: Cross-platform sound effect playback utility
- `utils/tts_announcer.py`: Intelligent TTS announcement system for events
- `sound/`: Directory for audio files (19+ event-specific sounds)
- `status-lines/status_line.py`: Custom Claude Code status line implementation
- `CHANGELOG.md`: Comprehensive version history following Keep a Changelog format
- `package.json`: Project metadata and npm scripts for development
