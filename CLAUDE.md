# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this
repository.

## Project Overview

This is a Claude Code hooks processing system that acts as a middleware server to handle Claude Code
hook events. The system queues events from Claude Code hooks into a SQLite database and processes
them sequentially, allowing for complex event handling workflows without blocking Claude Code
operations.

## Architecture

### Core Components

The system consists of three main components:

1. **Hook Script** (`hooks.py`) - Receives hook events from Claude Code via stdin and forwards them
   to the API server
2. **API Server** (`server.py`) - FastAPI server that receives events, queues them in SQLite, and
   runs the background processor
3. **Claude Wrapper** (`claude.sh`) - Bash script that manages server lifecycle, instance tracking,
   and launches Claude Code with hooks enabled

### Event Processing Pipeline

The event flow:

1. Claude Code triggers a hook (PreToolUse, PostToolUse, etc.)
2. Hook script receives JSON via stdin and posts to API endpoint (with instance ID)
3. API server queues event to SQLite database with instance tracking
4. Background processor handles events sequentially with retry logic
5. Optional TTS announcements provide audio feedback for events

### Critical Architectural Patterns

#### Multi-Instance Server Sharing Pattern

The system implements sophisticated lifecycle management allowing multiple Claude Code instances to
share a single API server:

- **Instance Registration**: Each session gets unique UUID and PID file in `.claude-instances/`
- **Shared Server**: Multiple instances share one server (only starts if needed, stops when last
  exits)
- **Graceful Shutdown**: Waits for pending events via `/instances/{id}/last-event` before shutdown
- **Temporal Filtering**: Only processes events created after server startup (prevents stale events)

#### Non-Blocking Hook Integration

The most critical design decision - hooks immediately return success after queuing, ensuring Claude
Code never waits for event processing. This **fire-and-forget pattern** maintains Claude Code
responsiveness regardless of processing complexity.

#### Provider Chain Pattern (TTS System)

The TTS system (`utils/tts_*`) demonstrates flexible provider architecture:

- **Factory Pattern**: Registry-based provider instantiation in `tts_providers/factory.py`
- **Chain of Responsibility**: Providers tried in priority order until success (leftmost = highest)
- **Context-Aware Mapping**: Analyzes event data to select appropriate sounds (not just event names)
- **Smart Parameter Filtering**: Providers receive only supported parameters
- **Multiple Providers**: Prerecorded, Google TTS (gtts), ElevenLabs API integration
- **Caching**: Generated TTS files cached for performance

#### Async/Sync Bridge Pattern

Sophisticated handling of async/sync boundaries:

- **Async Database**: `event_db.py` uses `aiosqlite` for non-blocking I/O
- **Sync Audio**: `sound_player.py` uses synchronous subprocess (prevents sound overlap)
- **Threading Bridge**: `event_processor.py` uses `loop.run_in_executor()` for sync operations in
  async context

#### Type-Safe Event Handling

The system uses enum-based event constants for validation:

- **Hook Constants**: `utils/hooks_constants.py` defines `HookEvent` enum
- **Validation Functions**: `is_valid_hook_event()` prevents invalid event names
- **API Integration**: Automatic validation in event submission endpoints

#### Contextual Completion Messages (Stop Event Enhancement)

Special handling for Stop events that generates dynamic completion messages:

- **Transcript Integration**: Uses `utils/transcript_parser.py` to extract conversation context from
  Claude Code JSONL transcripts
- **AI-Powered Generation**: OpenRouter integration generates contextual completion messages based
  on actual user prompts and Claude responses
- **No-Cache Strategy**: Contextual messages bypass TTS caching to ensure freshness and relevance
- **Graceful Fallback**: Falls back to standard Stop event messages if transcript parsing or AI
  generation fails
- **Multi-Language Support**: Generated messages respect `TTS_LANGUAGE` configuration
- **Context Requirements**: Requires both `session_id` and `transcript_path` in event data for
  optimal results

#### Contextual PreToolUse Messages (PreToolUse Event Enhancement)

Special handling for PreToolUse events that generates dynamic action-oriented messages:

- **Context-First Approach**: Messages describe what Claude is about to do based on user's request
  rather than just announcing tool names
- **Conversation-Aware**: Uses transcript parser to extract last user prompt and Claude's planned
  response for context
- **Tool-Supplemented**: Tool name provides additional context but isn't the primary focus of the
  message
- **Action-Oriented**: Messages sound natural and conversational, like "Installing the dependencies
  you requested" instead of "Running Bash tool"
- **No-Cache Strategy**: Fresh contextual messages generated for each tool execution to reflect
  current conversation context
- **Graceful Fallback**: Falls back to "Running {tool_name} tool" if transcript parsing or AI
  generation fails
- **Multi-Language Support**: Generated messages respect `TTS_LANGUAGE` configuration
- **OpenRouter Integration**: Uses dedicated PreToolUse prompt system optimized for action
  descriptions

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
curl http://localhost:12222/health

# Check event queue status
curl http://localhost:12222/events/status

# Check migration status
curl http://localhost:12222/migrations

# Shutdown server gracefully
curl -X POST http://localhost:12222/shutdown
```

### API Usage Examples

```bash
# Submit event without arguments
curl -X POST http://localhost:12222/events \
  -H "Content-Type: application/json" \
  -d '{"data": {"session_id": "test", "hook_event_name": "SessionStart"}}'

# Submit event with sound effect argument
curl -X POST http://localhost:12222/events \
  -H "Content-Type: application/json" \
  -d '{"data": {"session_id": "test", "hook_event_name": "PostToolUse"}, "arguments": {"sound_effect": "sound_effect_tek.mp3"}}'

# Submit event with multiple arguments
curl -X POST http://localhost:12222/events \
  -H "Content-Type: application/json" \
  -d '{"data": {"session_id": "test", "hook_event_name": "PreToolUse"}, "arguments": {"sound_effect": "sound_effect_cetek.mp3", "debug": true}}'

# Submit event with instance ID
curl -X POST http://localhost:12222/events \
  -H "Content-Type: application/json" \
  -d '{"data": {"session_id": "test", "hook_event_name": "SessionEnd"}, "instance_id": "abc-123"}'

# Check instance last event status
curl http://localhost:12222/instances/abc-123/last-event
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

#### Testing Specific Event Types

```bash
# Test SessionStart event with TTS announcement
echo '{"session_id": "test", "hook_event_name": "SessionStart"}' | uv run hooks.py --announce=0.5

# Test PreToolUse event (tool execution)
echo '{"session_id": "test", "hook_event_name": "PreToolUse", "tool_name": "Bash"}' | uv run hooks.py

# Test PreToolUse with contextual announcement
echo '{"session_id": "test", "hook_event_name": "PreToolUse", "tool_name": "Read"}' | uv run hooks.py --announce=0.5

# Test PreToolUse with transcript context (requires valid transcript path)
echo '{"session_id": "test", "hook_event_name": "PreToolUse", "tool_name": "Write", "transcript_path": "/path/to/transcript.jsonl"}' | uv run hooks.py --announce=0.5

# Test PostToolUse with error
echo '{"session_id": "test", "hook_event_name": "PostToolUse", "tool_name": "Read", "error": "File not found"}' | uv run hooks.py

# Test notification events
echo '{"session_id": "test", "hook_event_name": "NotificationReceived", "notification": {"message": "Permission required"}}' | uv run hooks.py --announce=0.8

# Test TTS announcer standalone
uv run utils/tts_announcer.py SessionStart  # Test specific event mapping
uv run utils/tts_announcer.py test_all      # Test all event mappings
```

### Server Lifecycle Troubleshooting

```bash
# Check server status and active instances
curl http://localhost:12222/health
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

### Cross-Component Dependencies

Understanding these dependencies is crucial for modifications:

#### Configuration Flow

- `config.py` (root level) is the single source of truth, loaded by all components
- Environment variables in `.env` override defaults (see `.env.example` for complete options)
- TTS providers list parsed from comma-separated string with priority ordering
- Server endpoint configuration affects both `hooks.py` and health checks
- Provider-specific configs (ElevenLabs API keys, voice IDs) loaded conditionally

#### Event Processing Dependencies

```
hooks.py → api.py → event_db.py → event_processor.py → [sound_player.py, tts_manager.py]
```

Key interaction points:

- `hooks.py` depends on `CC_INSTANCE_ID` and `CC_HOOKS_PORT` environment variables from `claude.sh`
- `event_processor.py` orchestrates both sound effects and TTS announcements
- TTS system requires `utils/sound_player.py` for actual playback
- Database operations require server start time and instance ID for temporal filtering

#### Instance Management Chain

- `claude.sh` generates UUID and manages `.claude-instances/` directory
- Instance ID propagated through environment to `hooks.py`
- API tracks events per instance via `instance_id` column
- Graceful shutdown queries `/instances/{id}/last-event` endpoint

#### Migration System Dependencies

- `app/migrations.py` runs automatically during server startup
- Migrations must be idempotent (safe to run multiple times)
- New columns must have defaults for existing rows
- Migration version tracking prevents re-execution

### Dependencies

This project uses `uv` for Python dependency management. Dependencies are declared inline in script
headers using PEP 723 format. The main dependencies are:

- FastAPI/Uvicorn for the API server
- aiosqlite for async database operations
- requests for HTTP client in hooks
- python-dotenv for environment configuration
- pygame for cross-platform audio playback
- gtts (Google Text-to-Speech) for TTS generation
- elevenlabs for advanced TTS with voice cloning
- openai SDK for OpenRouter API integration (translation services)

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

#### Core Settings

- `DB_PATH`: SQLite database path (default: "events.db")
- `MAX_RETRY_COUNT`: Event retry attempts (default: 3)

**Note**: Server host and port are now automatically managed per Claude Code instance. Each instance
finds an available port starting from 12222 and increments as needed. No manual configuration
required.

#### TTS Configuration

- `TTS_PROVIDERS`: Comma-separated list with priority (default: "prerecorded,gtts,elevenlabs")
- `TTS_CACHE_DIR`: Directory for cached TTS files (default: ".tts_cache")
- `TTS_LANGUAGE`: Language for TTS generation (default: "en")

#### ElevenLabs Configuration

- `ELEVENLABS_API_KEY`: Your ElevenLabs API key
- `ELEVENLABS_VOICE_ID`: Voice ID to use (default: "21m00Tcm4TlvDq8ikWAM")
- `ELEVENLABS_MODEL_ID`: Model to use (default: "eleven_flash_v2_5")

#### OpenRouter Configuration (AI Services)

- `OPENROUTER_ENABLED`: Enable OpenRouter integration (default: false)
- `OPENROUTER_API_KEY`: Your OpenRouter API key
- `OPENROUTER_MODEL`: Model to use (default: "openai/gpt-4o-mini")
- `OPENROUTER_CONTEXTUAL_STOP`: Enable contextual Stop messages (default: false)
- `OPENROUTER_CONTEXTUAL_PRETOOLUSE`: Enable contextual PreToolUse messages (default: false)

OpenRouter provides three main services:

1. **Translation Services**: When `TTS_LANGUAGE` is not "en", event descriptions are automatically
   translated
2. **Contextual Completion Messages**: For Stop events, generates dynamic completion messages based
   on conversation context (requires `OPENROUTER_CONTEXTUAL_STOP=true`)
3. **Contextual PreToolUse Messages**: For PreToolUse events, generates action-oriented messages
   based on conversation context (requires `OPENROUTER_CONTEXTUAL_PRETOOLUSE=true`)

**Cost Control**: Contextual message features are disabled by default to control API costs. Enable
selectively based on your usage needs and budget. Translation services are always available when
OpenRouter is enabled.

See `.env.example` for complete configuration options and examples.

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
- **Parallel Audio Processing**: Multiple audio tasks (sound effects + TTS announcements) run
  concurrently for better performance
- Graceful error handling if sound files are missing or audio system unavailable

#### TTS Announcement System

Intelligent context-aware voice announcements for events:

- **Smart Event Mapping**: Maps 19+ different event contexts to appropriate sounds
- **Context Extraction**: Analyzes event data (tool names, session types) for precise sound
  selection
- **Contextual Completion Messages**: Stop events use transcript parser and OpenRouter to generate
  dynamic completion messages based on actual conversation context
- **Volume Control**: Configurable volume levels (0.0-1.0) via `--announce` argument
- **Intelligent Caching**: Generated TTS cached for performance, with no-cache option for dynamic
  content
- **Comprehensive Coverage**: Unique sounds for all Claude Code hook event types:
  - Session events (startup, resume, clear, logout)
  - Tool events (running, completed, blocked)
  - Notification events (general, permission, waiting)
  - Compact mode events (manual, auto)
- **Testing**: Standalone testing via `uv run utils/tts_announcer.py <event_name>`

### Server Lifecycle Management

The cc-hooks system implements sophisticated lifecycle management where each Claude Code instance
runs its own dedicated server for optimal isolation and performance:

#### Instance Tracking

- Each Claude Code session registers itself with a unique UUID and PID in `.claude-instances/`
- Instance ID (`CC_INSTANCE_ID`) and port (`CC_HOOKS_PORT`) are passed to hook scripts via
  environment
- Events are tracked per instance with dedicated server handling
- The wrapper script automatically finds available ports starting from 12222
- Each instance manages its own server lifecycle independently
- Graceful shutdown waits for pending events (up to 10 seconds) before terminating

#### Port Management

- **Automatic Port Discovery**: Starting from port 12222, each instance finds the next available
  port
- **Per-Instance Servers**: Each Claude Code session runs its own dedicated server
- **Environment Propagation**: `CC_HOOKS_PORT` environment variable communicates the assigned port
- **Health Check Awareness**: Status line and health checks use the correct instance port
- **No Configuration Required**: Port assignment is fully automated

#### Startup Process

1. Clean up any stale instance PID files from previous sessions
2. Register current instance with UUID and assigned port
3. Find available port starting from 12222 (or configured base port)
4. Start dedicated server on assigned port with instance-specific configuration
5. Wait up to 10 seconds for server to be ready and responsive
6. If server fails to start or respond, exit with error

#### Shutdown Process

1. Check for pending events via `/instances/{instance_id}/last-event` endpoint
2. Wait up to 10 seconds for last event to complete
3. Stop the dedicated server for this instance
4. Unregister current instance after cleanup
5. Clean up instances directory if no other instances remain

#### Server Health Checks

- Health endpoint: `http://localhost:{assigned_port}/health`
- Connection timeout: 2 seconds
- Used during startup validation and instance management
- Each instance checks its own dedicated server port

### Claude Code Integration

The system integrates with Claude Code through its hooks configuration. To use this system:

1. Configure Claude Code hooks to call `hooks.py` in settings
2. Run Claude Code through `claude.sh` wrapper to launch dedicated server
3. Events will be queued and processed sequentially per instance

The wrapper handles all server lifecycle management automatically, with each Claude Code session
running its own dedicated server for optimal isolation and performance.

## Important Files

- `hooks.py`: Entry point for Claude Code hooks with dynamic argument parsing and instance tracking
- `server.py`: Main FastAPI server with lifecycle management and hot reload support
- `claude.sh`: Wrapper script for server management with graceful shutdown
- `config.py`: Root-level configuration management from environment variables
- `.env.example`: Complete configuration template with all available options
- `app/api.py`: API endpoints for event submission, status, and instance tracking
- `app/event_db.py`: Database operations for event queue with instance support
- `app/event_processor.py`: Background processor with event handling logic and sound effects
- `app/migrations.py`: Database schema migrations and setup with version tracking
- `utils/hooks_constants.py`: Type-safe event constants with `HookEvent` enum
- `utils/sound_player.py`: Cross-platform sound effect playback utility
- `utils/tts_manager.py`: TTS provider orchestration with fallback chain
- `utils/tts_announcer.py`: Intelligent TTS announcement system for events
- `utils/tts_providers/`: Provider implementations:
  - `base.py`: Abstract base class for TTS providers
  - `factory.py`: Provider factory with parameter filtering
  - `prerecorded_provider.py`: Uses local sound files
  - `gtts_provider.py`: Google Text-to-Speech integration
  - `elevenlabs_provider.py`: ElevenLabs API integration
  - `mappings.py`: Event-to-text mapping configuration
- `utils/openrouter_service.py`: OpenRouter API integration for translation and contextual
  completion messages
- `utils/transcript_parser.py`: Claude Code transcript parser for extracting conversation context
- `sound/`: Directory for audio files (19+ event-specific sounds)
- `status-lines/status_line.py`: Custom Claude Code status line implementation
- `CHANGELOG.md`: Comprehensive version history following Keep a Changelog format
- `package.json`: Project metadata and npm scripts for development

## Common Development Scenarios

### Adding a New Event Handler

To add custom processing for a specific event type:

1. Edit `app/event_processor.py` and add handler in `process_event()` function
2. Access event data via `event['data']` dictionary
3. Use `event.get('arguments', {})` for hook arguments
4. Return success/failure status for retry logic

### Adding a New TTS Provider

1. Create new provider class in `utils/tts_providers/` inheriting from `TTSProvider` base class
2. Implement required methods: `generate()`, `get_supported_params()`, `is_available()`
3. Register provider in `utils/tts_providers/factory.py` registry
4. Add provider name to `TTS_PROVIDERS` environment variable (leftmost = highest priority)
5. Provider automatically receives filtered parameters based on `get_supported_params()`

Example provider structure:

```python
from utils.tts_providers.base import TTSProvider

class CustomProvider(TTSProvider):
    def generate(self, text: str, event_name: str, **kwargs) -> Optional[str]:
        # Generate audio file, return path if successful
        pass

    def get_supported_params(self) -> List[str]:
        return ["custom_param1", "custom_param2"]

    def is_available(self) -> bool:
        # Check if provider dependencies are met
        return True
```

### Extending Hook Arguments

1. Add argument parsing in `hooks.py` (already supports `--key=value` format)
2. Arguments stored as JSON in database automatically
3. Access in `event_processor.py` via `event.get('arguments', {})`
4. No database migration needed - uses JSON column

### Debugging Event Processing

```bash
# Watch real-time event processing
sqlite3 events.db "SELECT id, hook_event_name, status, retry_count FROM events ORDER BY created_at DESC LIMIT 10;" -header -column

# Check specific instance events
sqlite3 events.db "SELECT * FROM events WHERE instance_id = 'your-instance-id' ORDER BY created_at DESC;"

# Monitor server logs with reload
uv run server.py --dev  # Includes detailed logging

# Test event with debug flag
echo '{"session_id": "test", "hook_event_name": "Test"}' | uv run hooks.py --debug
```

### Testing TTS Providers

```bash
# Test specific TTS provider chain
TTS_PROVIDERS=gtts,prerecorded uv run utils/tts_announcer.py SessionStart

# Test with ElevenLabs as primary provider
TTS_PROVIDERS=elevenlabs uv run utils/tts_announcer.py PreToolUse

# Test all event mappings
uv run utils/tts_announcer.py test_all

# Test transcript parser standalone
uv run utils/transcript_parser.py path/to/transcript.jsonl --format=text

# Check provider availability
python -c "from utils.tts_providers.factory import TTSProviderFactory; print(TTSProviderFactory.get_available_providers())"
```

### Implementing Contextual Completion Messages

For events that need dynamic, conversation-aware completion messages:

1. **Ensure OpenRouter is configured** with valid API key in `.env`
2. **Access transcript data** in event processing via `event_data.get('transcript_path')`
3. **Use transcript parser** to extract conversation context:
   ```python
   from utils.transcript_parser import extract_conversation_context
   context = extract_conversation_context(transcript_path)
   ```
4. **Generate contextual messages** using OpenRouter service:
   ```python
   from utils.openrouter_service import generate_completion_message_if_available
   message = generate_completion_message_if_available(
       session_id=session_id,
       user_prompt=context.last_user_prompt,
       claude_response=context.last_claude_response,
       target_language="en"
   )
   ```
5. **Set no-cache flag** in event data to prevent caching dynamic content:
   ```python
   event_data["_no_cache"] = True
   ```

### Testing OpenRouter Integration

```bash
# Test OpenRouter translation directly
python -c "
from utils.openrouter_service import get_openrouter_service
service = get_openrouter_service()
if service:
    result = service.translate_text('Session started', 'id')
    print(f'Translation: {result}')
else:
    print('OpenRouter not configured')
"

# Test contextual completion message generation
python -c "
from utils.openrouter_service import generate_completion_message_if_available
result = generate_completion_message_if_available(
    session_id='test',
    user_prompt='Help me fix this error',
    claude_response='I found the issue and fixed it by updating the import statement...',
    target_language='en'
)
print(f'Completion message: {result}')
"

# Test contextual PreToolUse message generation
python -c "
from utils.openrouter_service import generate_pre_tool_message_if_available
result = generate_pre_tool_message_if_available(
    session_id='test',
    tool_name='Bash',
    user_prompt='Install the latest dependencies for this project',
    claude_response='I will run npm install to install all the dependencies listed in package.json',
    target_language='en'
)
print(f'PreToolUse message: {result}')
"

# Test TTS with translation (requires OpenRouter config)
TTS_LANGUAGE=id OPENROUTER_ENABLED=true uv run utils/tts_announcer.py SessionStart

# Test Stop event with contextual completion (requires transcript)
echo '{"session_id": "test", "hook_event_name": "Stop", "transcript_path": "path/to/transcript.jsonl"}' | uv run hooks.py --announce=0.8

# Test with contextual features disabled (default behavior)
OPENROUTER_CONTEXTUAL_STOP=false OPENROUTER_CONTEXTUAL_PRETOOLUSE=false uv run utils/tts_announcer.py Stop

# Test with only contextual Stop messages enabled
OPENROUTER_ENABLED=true OPENROUTER_CONTEXTUAL_STOP=true OPENROUTER_CONTEXTUAL_PRETOOLUSE=false echo '{"session_id": "test", "hook_event_name": "Stop", "transcript_path": "path/to/transcript.jsonl"}' | uv run hooks.py --announce=0.8

# Test with only contextual PreToolUse messages enabled
OPENROUTER_ENABLED=true OPENROUTER_CONTEXTUAL_STOP=false OPENROUTER_CONTEXTUAL_PRETOOLUSE=true echo '{"session_id": "test", "hook_event_name": "PreToolUse", "tool_name": "Bash", "transcript_path": "path/to/transcript.jsonl"}' | uv run hooks.py --announce=0.8

# Test with both contextual features enabled
OPENROUTER_ENABLED=true OPENROUTER_CONTEXTUAL_STOP=true OPENROUTER_CONTEXTUAL_PRETOOLUSE=true uv run utils/tts_announcer.py test_all
```

## Important Gotchas

1. **Server Start Time Filtering**: Only events created AFTER server startup are processed. This
   prevents processing stale events but means pre-existing events won't be handled.

2. **Instance ID Propagation**: The `CC_INSTANCE_ID` environment variable MUST be set by `claude.sh`
   for proper instance tracking. Direct execution of `hooks.py` without this will use "unknown"
   instance.

3. **Parallel Audio Processing**: Multiple audio tasks (sound effects + TTS) now run concurrently
   for better performance. Individual audio providers still prevent overlap within their own scope.

4. **Migration Ordering**: Migrations are applied in version order. Never modify existing
   migrations; always create new ones.

5. **Hot Reload Caveats**: When using `--dev` or `--reload`, the server restarts on file changes but
   maintains the same start time to preserve event continuity.

6. **Configuration Location**: Configuration moved from `app/config.py` to root-level `config.py`.
   All imports must be updated accordingly.

7. **TTS Provider Priority**: Provider order in `TTS_PROVIDERS` determines fallback chain. Leftmost
   provider has highest priority.

8. **ElevenLabs Rate Limits**: Be aware of API rate limits when using ElevenLabs as primary
   provider. Consider using gtts or prerecorded as fallbacks.

9. **Translation Fallback**: If OpenRouter translation fails, the system falls back to English text.
   No translation errors will block TTS generation.

10. **TTS Caching Strategy**: Most TTS content is cached for performance, but contextual completion
    messages use `_no_cache` flag to ensure freshness and relevance for each session.

11. **Transcript Parser Limitations**: Requires valid JSONL format Claude Code transcript files.
    Missing transcript or parsing errors will gracefully fall back to default completion messages.

12. **Contextual Message Cost Control**: The `OPENROUTER_CONTEXTUAL_STOP` and
    `OPENROUTER_CONTEXTUAL_PRETOOLUSE` environment variables are disabled by default to prevent
    unexpected API costs. Enable selectively based on your usage needs and budget. Translation
    services remain available regardless of these settings when OpenRouter is enabled.
