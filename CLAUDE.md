# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this
repository.

## Project Overview

Claude Code hooks processing system that acts as middleware to handle hook events. The system queues
events from Claude Code hooks into SQLite and processes them sequentially with TTS announcements and
contextual AI-powered completion messages.

## Architecture

### Core Components

1. **Hook Script** (`hooks.py`) - Receives hook events via stdin, forwards to API server
2. **API Server** (`server.py`) - FastAPI server that queues events and runs background processor
3. **Claude Wrapper** (`claude.sh`) - Manages server lifecycle, instance tracking, launches Claude
   Code

### Critical Patterns

- **Fire-and-forget**: Hooks immediately return success after queuing to keep Claude Code responsive
- **Per-instance servers**: Each Claude Code session runs dedicated server on auto-assigned port
- **Provider chain**: TTS providers tried in priority order (prerecorded → gtts → elevenlabs)
- **Contextual AI**: OpenRouter integration for dynamic completion messages based on transcript
  context
- **Async/sync bridge**: Uses `loop.run_in_executor()` for sync operations in async context

## Development Commands

### Running the System

```bash
# Start server + Claude Code (recommended)
./claude.sh

# Start with language override (per-session)
./claude.sh --language=id

# Start with specific ElevenLabs voice ID (per-session)
./claude.sh --elevenlabs-voice-id=21m00Tcm4TlvDq8ikWAM

# Start with TTS providers override (per-session)
./claude.sh --tts-providers=gtts,prerecorded

# Combine language and voice overrides
./claude.sh --language=es --elevenlabs-voice-id=21m00Tcm4TlvDq8ikWAM

# Combine multiple session overrides
./claude.sh --language=id --tts-providers=elevenlabs,gtts --elevenlabs-voice-id=21m00Tcm4TlvDq8ikWAM

# Development server with hot reload
npm run dev
# or: uv run server.py --dev

# Server only (testing)
uv run server.py

# Format code
npm run format

# Update cc-hooks to latest version
npm run update

# Check for available updates
npm run version:check
```

### Testing

```bash
# Start test server first (required for hook testing)
uv run server.py &
SERVER_PID=$!

# Test hook manually (with required environment variables)
echo '{"session_id": "test", "hook_event_name": "SessionStart"}' | \
  CC_INSTANCE_ID="test-instance-123" CC_HOOKS_PORT=12222 uv run hooks.py --announce=0.5

# Test with specific sound effect
echo '{"session_id": "test", "hook_event_name": "PreToolUse", "tool_name": "Bash"}' | \
  CC_INSTANCE_ID="test-instance-123" CC_HOOKS_PORT=12222 uv run hooks.py --sound-effect=sound_effect_tek.mp3

# Test notification events with appropriate sounds
echo '{"session_id": "test", "hook_event_name": "Notification", "notification": {"message": "Permission required"}}' | \
  CC_INSTANCE_ID="test-instance-123" CC_HOOKS_PORT=12222 uv run hooks.py --sound-effect=sound_effect_tung.mp3 --announce=0.5

# Test contextual messages (requires OpenRouter config)
echo '{"session_id": "test", "hook_event_name": "Stop", "transcript_path": "/path/to/transcript.jsonl"}' | \
  CC_INSTANCE_ID="test-instance-123" CC_HOOKS_PORT=12222 uv run hooks.py --announce=0.8

# Test with language override (Indonesian TTS)
echo '{"session_id": "test", "hook_event_name": "SessionStart"}' | \
  CC_INSTANCE_ID="test-instance-123" CC_HOOKS_PORT=12222 CC_TTS_LANGUAGE=id uv run hooks.py --announce=0.5

# Test with ElevenLabs voice ID override
echo '{"session_id": "test", "hook_event_name": "SessionStart"}' | \
  CC_INSTANCE_ID="test-instance-123" CC_HOOKS_PORT=12222 CC_ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM uv run hooks.py --announce=0.5

# Test with both language and voice override
echo '{"session_id": "test", "hook_event_name": "SessionStart"}' | \
  CC_INSTANCE_ID="test-instance-123" CC_HOOKS_PORT=12222 CC_TTS_LANGUAGE=es CC_ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM uv run hooks.py --announce=0.5

# Test TTS system standalone (no server needed)
uv run utils/tts_announcer.py SessionStart
uv run utils/tts_announcer.py test_all

# Test individual components directly with uv run
# Sound player testing
uv run utils/sound_player.py                           # Play default sound (sound_effect_tek.mp3)
uv run utils/sound_player.py sound_effect_cetek.mp3    # Play specific sound file
uv run utils/sound_player.py --list                    # List all available sound files
uv run utils/sound_player.py --volume 0.3 sound_effect_tek.mp3  # Play with custom volume

# TTS announcer testing
uv run utils/tts_announcer.py --list                   # Show TTS system status and providers
uv run utils/tts_announcer.py SessionStart             # Test SessionStart announcement
uv run utils/tts_announcer.py SessionStart startup     # Test with source context
uv run utils/tts_announcer.py --provider gtts SessionStart     # Test with specific provider
uv run utils/tts_announcer.py --provider prerecorded Stop      # Test prerecorded provider

# Transcript parser testing
uv run utils/transcript_parser.py /path/to/transcript.jsonl              # Parse full transcript (JSON output)
uv run utils/transcript_parser.py --format text /path/to/transcript.jsonl # Parse with text output
uv run utils/transcript_parser.py --verbose /path/to/transcript.jsonl    # Parse with verbose logging
uv run utils/transcript_parser.py --start-line 10 --end-line 20 /path/to/transcript.jsonl  # Parse specific range
uv run utils/transcript_parser.py --skip-duplicate-check /path/to/transcript.jsonl         # Skip duplicate check

# Clean up test server
kill $SERVER_PID
```

### API Endpoints

```bash
# Health check (port auto-assigned, check .claude-instances/)
curl http://localhost:12222/health

# Submit event
curl -X POST http://localhost:12223/events \
  -H "Content-Type: application/json" \
  -d '{"data": {"session_id": "test", "hook_event_name": "SessionStart"}, "instance_id": "test-instance-123", "arguments": {"sound_effect": "sound_effect_cetek.mp3", "debug": true}}'

# Check event queue
curl http://localhost:12222/events/status?instance_id=test-instance-123

# Check for updates
curl http://localhost:12222/version/status

# Force fresh version check (skip cache)
curl http://localhost:12222/version/status?force=true
```

### Database Management

```bash
# View recent events
sqlite3 events.db "SELECT id, session_id, hook_event_name, status, instance_id FROM events ORDER BY created_at DESC LIMIT 10;"

# View events for specific instance
sqlite3 events.db "SELECT id, session_id, hook_event_name, status FROM events WHERE instance_id = 'test-instance-123' ORDER BY created_at DESC LIMIT 10;"

# Clear failed events (all instances)
sqlite3 events.db "DELETE FROM events WHERE status = 'failed';"

# Clear failed events for specific instance
sqlite3 events.db "DELETE FROM events WHERE status = 'failed' AND instance_id = 'test-instance-123';"
```

## Configuration

Configuration via `.env` file (see `.env.example`):

### Core Settings

- `DB_PATH`: SQLite database path (default: "events.db")
- `MAX_RETRY_COUNT`: Event retry attempts (default: 3)

### TTS Configuration

- `TTS_PROVIDERS`: Provider chain priority (default: "prerecorded")
- `TTS_LANGUAGE`: Language for TTS (default: "en")
- `TTS_CACHE_ENABLED`: Enable file caching (default: true)

### OpenRouter (AI Services)

- `OPENROUTER_ENABLED`: Enable AI features (default: false)
- `OPENROUTER_API_KEY`: API key for translation/contextual messages
- `OPENROUTER_CONTEXTUAL_STOP`: Dynamic completion messages (default: false)
- `OPENROUTER_CONTEXTUAL_PRETOOLUSE`: Action-oriented tool messages (default: false)

### ElevenLabs (Premium TTS)

- `ELEVENLABS_API_KEY`: API key
- `ELEVENLABS_VOICE_ID`: Voice ID (default: "21m00Tcm4TlvDq8ikWAM")

### Per-Session Overrides (via claude.sh)

- `CC_TTS_LANGUAGE`: Override language per session (via `--language=id`)
- `CC_TTS_PROVIDERS`: Override TTS providers chain per session (via
  `--tts-providers=gtts,prerecorded`)
- `CC_ELEVENLABS_VOICE_ID`: Override voice ID per session (via `--elevenlabs-voice-id=abc123`)

These environment variables are automatically set by `claude.sh` when using `--language`,
`--tts-providers`, or `--elevenlabs-voice-id` parameters, allowing multiple concurrent sessions with
different voice configurations without modifying `.env` files.

## Key Implementation Details

### Event Processing Flow

```
hooks.py → api.py → event_db.py → event_processor.py → [sound_player.py, tts_manager.py]
```

### Instance Management

- `claude.sh` generates UUID and manages `.claude-instances/` directory
- Environment variables `CC_INSTANCE_ID` and `CC_HOOKS_PORT` propagated to hooks
- Graceful shutdown waits for pending events via `/instances/{id}/last-event`

### TTS Provider Chain

- Factory pattern in `utils/tts_providers/factory.py`
- Providers tried left-to-right until success
- Smart parameter filtering based on provider capabilities
- Context-aware event mapping in `utils/tts_providers/mappings.py`

### Contextual AI Messages

- Uses `utils/transcript_parser.py` to extract conversation context
- OpenRouter generates dynamic messages based on user prompts and Claude responses
- No-cache strategy ensures freshness for contextual content
- Cost control via disabled-by-default flags

### Version Management

- Git-based version checking via `utils/version_checker.py`
- Background checks on server startup with 1-hour cache
- Results persisted in SQLite `version_checks` table
- API endpoint `/version/status` exposes update information
- Simple update via `npm run update` or `./update.sh`
- Auto-stash/restore uncommitted changes during update

## Updating cc-hooks

To update to the latest version:

```bash
# Simple update command
npm run update
# or
./update.sh
```

The update script will:

1. Check for uncommitted changes and offer to stash them
2. Fetch latest from origin
3. Pull changes from main branch
4. Update dependencies with `uv sync`
5. Restore stashed changes if any
6. Show current version after update

Check for available updates:

```bash
# CLI check
npm run version:check

# API check (if server is running)
curl http://localhost:12222/version/status
```

**Important**: Restart your Claude Code session after updating to use the new version.

## Adding Features

### New Event Handler

Add to `EVENT_CONFIGS` in `app/event_processor.py`:

```python
EVENT_CONFIGS = {
    HookEvent.YOUR_EVENT.value: {
        "log_message": "Session {session_id}: Your event triggered",
        "clear_tracking": False,
        "use_tool_name": False,
    },
}
```

### New TTS Provider

1. Create class in `utils/tts_providers/` inheriting from `TTSProvider`
2. Implement: `generate()`, `get_supported_params()`, `is_available()`
3. Register in `utils/tts_providers/factory.py`
4. Add to `TTS_PROVIDERS` environment variable

### Hook Arguments

- Arguments automatically parsed from `--key=value` format
- Stored as JSON in database
- Access via `arguments.get('your_arg', default)` in event handlers

## Dependencies

Uses `uv` for Python dependency management with inline PEP 723 declarations:

- FastAPI/Uvicorn (API server)
- aiosqlite (async database)
- pygame (cross-platform audio)
- gtts, elevenlabs (TTS providers)
- openai (OpenRouter integration)
- coloredlogs (per-component colored logging)

## Important Gotchas

1. **Temporal Filtering**: Only events created AFTER server startup are processed
2. **Instance ID Required**: `CC_INSTANCE_ID` must be set by `claude.sh` for proper tracking
3. **Port Auto-assignment**: Each instance finds available port starting from 12222
4. **Migration Safety**: Never modify existing migrations, always create new ones
5. **Contextual Costs**: OpenRouter contextual features disabled by default to control API costs
