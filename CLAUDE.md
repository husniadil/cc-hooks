# CLAUDE.md

Development guide for cc-hooks - a Claude Code hooks processing system with TTS announcements and
contextual AI.

## Documentation Structure

- **[README.md](README.md)** - Plugin installation (recommended for most users)
- **[STANDALONE_README.md](STANDALONE_README.md)** - Standalone installation (for
  developers/contributors)
- **[MIGRATION.md](MIGRATION.md)** - Migration guide from standalone to plugin mode
- **[CLAUDE.md](CLAUDE.md)** - This file: Development and technical guide

## Best Practices

### PEP 723 for Standalone Scripts

**All test scripts, utilities, and one-off tools MUST use PEP 723** for dependency management:

```python
#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["aiosqlite", "python-dotenv"]
# ///
```

**Why:**

- Self-contained with explicit dependencies
- No global environment pollution
- Works across different machines
- Easy to run: `uv run script.py`

### Database Migrations

**CRITICAL RULES:**

1. **One SQL statement per migration** - Never combine multiple statements
2. **Append-only** - Never modify existing migrations that are deployed
3. **Sequential versions** - Always increment from the latest version

### Code Style

- Clean, readable code with minimal single-line comments
- Self-contained, reusable components
- Direct communication (no sugar-coating in error messages)
- Practical over perfect

## Quick Start

**Plugin Mode (Recommended)**:

```bash
# Set up alias first (add to .bashrc/.zshrc)
alias cld='~/.claude/plugins/marketplaces/cc-hooks-plugin/claude.sh'

# Start Claude Code with cc-hooks
cld

# Common configurations
cld --audio=gtts --language=id
cld --audio=elevenlabs --ai=full
cld --silent=announcements
```

**Standalone Mode**:

```bash
# From cc-hooks directory
./claude.sh

# Common configurations
./claude.sh --audio=gtts --language=id
./claude.sh --audio=elevenlabs --ai=full
./claude.sh --silent=announcements
```

## Project Overview

**Purpose**: Middleware that processes Claude Code hook events with audio feedback and contextual AI
messages.

**Core Flow**:

```
Claude Code → hooks.py → FastAPI server → Event processor → [TTS + Sound effects]
```

**Key Features**:

- Sequential event processing with SQLite queue
- TTS announcements (prerecorded/Google/ElevenLabs)
- Contextual AI completion messages via OpenRouter
- Per-instance servers for concurrent sessions
- Granular audio control (silent modes, provider selection)

## Data Directory

**All runtime data is stored in** `~/.claude/.cc-hooks/`

This directory is **shared across both installation modes** (standalone and plugin) to ensure
seamless migration and data persistence across updates.

**Directory Structure**:

```
~/.claude/.cc-hooks/
├── events.db           # SQLite database (events, sessions, migrations, version_checks)
├── logs/               # Per-session server logs
│   └── {claude_pid}.log
└── .tts_cache/         # TTS audio cache (when enabled)
    ├── prerecorded/
    ├── gtts/
    └── elevenlabs/
```

**Key Files**:

- **events.db**: Main SQLite database containing all events, sessions, and metadata
- **logs/**: Server logs named by Claude PID (e.g., `12345.log`)
- **.tts_cache/**: Generated TTS audio files organized by provider

**Note**: The data directory persists across updates and uninstallation, allowing you to:

- Switch between standalone and plugin modes without losing data
- Update cc-hooks while preserving event history and session state
- Manually inspect logs and database for debugging

## Installation Modes

cc-hooks supports two installation modes:

### 1. Standalone Mode

**Installation**: Can be installed anywhere on the filesystem (user's choice)

**Hooks Configuration**: Defined in `~/.claude/settings.json` (manual setup required)

**Use Case**: Development, testing, custom installation paths

**Setup**:

```json
{
  "hooks": {
    "SessionStart": {
      "type": "command",
      "command": "uv run /path/to/cc-hooks/hooks.py"
    }
    // ... other hooks
  }
}
```

### 2. Plugin Mode (Recommended)

**Installation**: Installed at `~/.claude/plugins/marketplaces/cc-hooks-plugin` (via Claude plugin
system)

**Hooks Configuration**: Defined in
`~/.claude/plugins/marketplaces/cc-hooks-plugin/hooks/hooks.json` (automatic)

**Use Case**: Production use, easy updates, no manual hook configuration

**Installation**:

```bash
# Via CLI (recommended)
claude plugin marketplace add https://github.com/husniadil/cc-hooks.git
claude plugin install cc-hooks@cc-hooks-plugin

# Or inside Claude REPL
/plugin marketplace add https://github.com/husniadil/cc-hooks.git
/plugin install cc-hooks@cc-hooks-plugin
```

**Key Differences**:

| Feature           | Standalone                         | Plugin                                           |
| ----------------- | ---------------------------------- | ------------------------------------------------ |
| Installation path | User-defined                       | `~/.claude/plugins/marketplaces/cc-hooks-plugin` |
| Hooks config      | Manual (`~/.claude/settings.json`) | Automatic (`hooks/hooks.json` in plugin)         |
| Updates           | Git pull                           | `/plugin update cc-hooks@cc-hooks-plugin`        |
| Data directory    | `~/.claude/.cc-hooks/` (shared)    | `~/.claude/.cc-hooks/` (shared)                  |

**Note**: Both modes share the same data directory (`~/.claude/.cc-hooks/`) for seamless migration
and persistence across updates.

### Detecting Installation Mode

To programmatically detect which mode cc-hooks is running in, you must check TWO locations in the
correct order:

**Detection Logic**:

1. **Check Plugin Mode First**:
   - Look for `~/.claude/plugins/marketplaces/cc-hooks-plugin/hooks/hooks.json`
   - Verify it contains valid `hooks` configuration
   - Verify `hooks.py` exists at `~/.claude/plugins/marketplaces/cc-hooks-plugin/hooks.py`
   - If all checks pass → **Plugin mode**

2. **Check Standalone Mode**:
   - Read `~/.claude/settings.json`
   - Check the `hooks` field (MUST be exactly `hooks`, not `#hooks_disabled`)
   - Look for any hook command containing `hooks.py`
   - If found → **Standalone mode**

3. **If neither**:
   - Result: **Unknown** (cc-hooks not configured)

**Why this order matters**:

- In **plugin mode**, hooks are NOT in `~/.claude/settings.json`
- In **plugin mode**, hooks are in `~/.claude/plugins/marketplaces/cc-hooks-plugin/hooks/hooks.json`
- Must check plugin directory first before checking settings.json

**Example Detection Script**:

```bash
# Detect installation mode
mode=$(python3 -c "
import json, sys, os

# Check 1: Plugin mode - hooks defined in plugin directory
plugin_hooks_file = os.path.expanduser('~/.claude/plugins/marketplaces/cc-hooks-plugin/hooks/hooks.json')
if os.path.isfile(plugin_hooks_file):
    try:
        with open(plugin_hooks_file, 'r') as f:
            config = json.load(f)
            # Verify it has hooks configuration
            if config.get('hooks') and len(config['hooks']) > 0:
                # Verify hooks.py exists
                plugin_hooks_py = os.path.expanduser('~/.claude/plugins/marketplaces/cc-hooks-plugin/hooks.py')
                if os.path.isfile(plugin_hooks_py):
                    print('plugin')
                    sys.exit(0)
    except:
        pass

# Check 2: Standalone mode - hooks defined in settings.json
settings_file = os.path.expanduser('~/.claude/settings.json')
if os.path.isfile(settings_file):
    try:
        with open(settings_file, 'r') as f:
            config = json.load(f)
            hooks = config.get('hooks', {})
            # Check if any hook points to hooks.py
            for event_hooks in hooks.values():
                if isinstance(event_hooks, list):
                    for matcher_group in event_hooks:
                        for hook in matcher_group.get('hooks', []):
                            command = hook.get('command', '')
                            if 'hooks.py' in command:
                                print('standalone')
                                sys.exit(0)
    except:
        pass

print('unknown')
" 2>/dev/null || echo "unknown")

# Display result
if [ "$mode" = "plugin" ]; then
    echo "Running in Plugin mode"
elif [ "$mode" = "standalone" ]; then
    echo "Running in Standalone mode"
else
    echo "Not configured or unknown mode"
fi
```

**Example Configurations**:

**Plugin mode**: `~/.claude/plugins/marketplaces/cc-hooks-plugin/hooks/hooks.json`

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [{ "type": "command", "command": "uv run ${CLAUDE_PLUGIN_ROOT}/hooks.py" }]
      }
    ]
  }
}
```

**Standalone mode**: `~/.claude/settings.json`

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [{ "type": "command", "command": "uv run /Users/username/cc-hooks/hooks.py" }]
      }
    ]
  }
}
```

**Use Cases**:

- Update scripts need to use different commands (`claude plugin marketplace update` vs `npm run update`)
- Detection is used by `/cc-hooks-plugin:update` slash command
- Diagnostic tools showing current installation configuration

## Architecture

### Core Components

| Component       | File                     | Purpose                                                  |
| --------------- | ------------------------ | -------------------------------------------------------- |
| Hook Script     | `hooks.py`               | Entry point, receives events from Claude Code            |
| API Server      | `server.py`              | FastAPI server, queues events, runs background processor |
| Event Processor | `app/event_processor.py` | Background task that processes queued events             |
| Event DB        | `app/event_db.py`        | SQLite operations, orphan cleanup                        |
| API Routes      | `app/api.py`             | REST endpoints for events, sessions, health              |
| Claude Wrapper  | `claude.sh`              | CLI parser, environment bridge, launches Claude          |

### Event Flow

1. **Hook receives event** → `hooks.py` via stdin from Claude Code
2. **Detect/start server** → Per-instance server on auto-assigned port (12222+)
3. **Queue event** → POST to `/events`, immediately returns 200 (fire-and-forget)
4. **Background processing** → Processor polls DB for PENDING events
5. **Execute handler** → Play sound effect and/or TTS announcement
6. **Update status** → Mark as COMPLETED or FAILED (max 3 retries)

### Critical Patterns

**Fire-and-Forget**:

- Hooks return immediately after queuing
- No waiting for processing
- Keeps Claude Code responsive

**Per-Instance Servers**:

- Each Claude session gets dedicated server on unique port
- Auto-discovery via SessionStart, lookup via session_id
- Session isolation prevents resource contention

**Auto-Cleanup**:

- SessionEnd kills orphaned server processes and cleans up sessions
- Port binding check protects active servers during cleanup
- Conservative cleanup (keeps processes when uncertain)

**Session Isolation**:

- Temporal filtering: Only process events created >= server_start_time
- Ownership filtering: Only process events where session.server_port == this_server_port

**Instance ID Pattern**:

- Format: `"{claude_pid}:{server_port}"` (e.g., "12345:12222")
- Stored in events table for debugging
- Preserved after session deletion

## Database Schema

### events table

```sql
id, session_id, hook_event_name, payload (JSON), status,
instance_id, created_at, processed_at,
retry_count, error_message
```

Indexes: `(status, created_at, id)`, `(session_id)`

### sessions table

```sql
session_id (PK), claude_pid, server_port,
tts_language, tts_providers, tts_cache_enabled,
elevenlabs_voice_id, elevenlabs_model_id,
silent_announcements, silent_effects,
openrouter_enabled, openrouter_model,
openrouter_contextual_stop, openrouter_contextual_pretooluse
```

Indexes: `unique(server_port)`, `(claude_pid)`

### version_checks table

```sql
id, last_checked, current_version, latest_version,
commits_behind, update_available
```

### migrations table

Tracks 11 schema migrations (append-only, never modify existing).

## Configuration

### Layered Approach

**Precedence**: Session DB > CLI Flags > Environment Variables > YAML Config File > Hardcoded
Defaults

**Layer 1: Hardcoded Defaults** (`config.py`):

- TTS providers: "prerecorded"
- Language: "en"
- ElevenLabs voice: "21m00Tcm4TlvDq8ikWAM" (Rachel)
- ElevenLabs model: "eleven_flash_v2_5"
- OpenRouter model: "openai/gpt-4o-mini"

**Layer 2: Shell Environment Variables** (Recommended - API keys):

**⚠️ IMPORTANT: Plugin vs Standalone Mode**

- **Plugin Mode** (`~/.claude/plugins/marketplaces/`): Plugin updates DELETE all files including
  `.env` → MUST use shell environment variables
- **Standalone Mode** (user-cloned directory): `.env` is gitignored and safe, but shell environment
  recommended for consistency

**Recommended Approach (Works for Both Modes)**:

Add to your shell config (`~/.bashrc`, `~/.zshrc`, etc.):

```bash
# cc-hooks API Keys
export ELEVENLABS_API_KEY="your_key_here"
export OPENROUTER_API_KEY="your_key_here"
```

Then reload: `source ~/.bashrc` or `source ~/.zshrc`

**Standalone Mode Alternative (.env file)**:

If using standalone installation, you can optionally create `.env` file in the project directory:

```bash
# .env (standalone mode only - gitignored)
ELEVENLABS_API_KEY=your_key_here
OPENROUTER_API_KEY=your_key_here
```

**API Key Resolution Priority**:

1. **If both .env and shell env exist** → use .env (standalone mode only)
2. **If only shell env exists** → use shell env (works for both modes)
3. **If both are empty** → features disabled

**Layer 3: YAML Config File** (Global defaults - recommended):

Location: `~/.claude/.cc-hooks/config.yaml`

**Purpose**: Set default preferences without CLI flags - enables customization for editors (Zed) and
convenience for terminal users.

**Structure**:

```yaml
# Audio Settings
audio:
  providers: gtts,prerecorded # Provider chain
  language: id # Language code
  cache_enabled: true # Enable TTS cache

# ElevenLabs (requires API key)
elevenlabs:
  voice_id: 21m00Tcm4TlvDq8ikWAM
  model_id: eleven_flash_v2_5

# Silent Modes
silent:
  announcements: false # Disable TTS announcements
  effects: false # Disable sound effects

# OpenRouter (AI features - requires API key)
openrouter:
  enabled: false # Enable AI features
  model: openai/gpt-4o-mini # AI model
  contextual_stop: false # Contextual completion messages
  contextual_pretooluse: false # Contextual tool messages
```

**Creating config file**:

```bash
# Create example config with all options documented
uv run ~/.claude/plugins/marketplaces/cc-hooks-plugin/utils/config_loader.py --create-example

# Edit to your preferences
nano ~/.claude/.cc-hooks/config.yaml
```

**Use cases**:

- **Zed/editors**: Only way to customize (editors can't pass CLI flags)
- **Terminal (`claude` binary)**: Set once, forget - no flags needed
- **Terminal (`cld` wrapper)**: Set defaults, override with flags when needed

**Mapping to environment variables**:

Config keys are mapped to `CC_*` environment variables:

- `audio.providers` → `CC_TTS_PROVIDERS`
- `audio.language` → `CC_TTS_LANGUAGE`
- `elevenlabs.voice_id` → `CC_ELEVENLABS_VOICE_ID`
- `openrouter.enabled` → `CC_OPENROUTER_ENABLED`
- etc.

**Layer 4: CLI Flags** (Per-session - power users):

```bash
# Audio control
--audio=prerecorded|gtts|elevenlabs  # Sets CC_TTS_PROVIDERS chain
--language=ja|id|es|en               # Sets CC_TTS_LANGUAGE (ISO 639-1 codes)
--no-cache                           # Sets CC_TTS_CACHE_ENABLED=false

# AI features (requires OpenRouter API key)
--ai=basic                           # Contextual Stop messages only
--ai=full                            # Stop + PreToolUse contextual messages

# Silent modes
--silent                             # Disable everything
--silent=announcements               # Disable TTS only, keep sound effects
--silent=sound-effects               # Disable sound effects, keep TTS

# Advanced
--elevenlabs-voice-id=abc123         # Override voice per session
--elevenlabs-model=eleven_turbo_v2_5 # Override ElevenLabs model
--openrouter-model=google/gemini-2.5-flash-lite
```

**Important: Language Codes**

Use **ISO 639-1** language codes (2-letter codes), not country codes:

- ✅ Correct: `--language=ja` (Japanese language)
- ❌ Wrong: `--language=jp` (Japan country code)

Common codes: `ja` (Japanese), `id` (Indonesian), `es` (Spanish), `fr` (French), `de` (German), `zh`
(Chinese), `ko` (Korean)

For a complete reference, see [docs/language-codes.md](docs/language-codes.md).

### Configuration Flow

```
Priority (highest to lowest):
1. CLI Flags (claude.sh)            → CC_* env vars
2. YAML Config File                  → CC_* env vars (if not set)
3. Shell Environment Variables       → API keys + CC_* defaults
4. Hardcoded Defaults                → Fallback values

Flow:
claude.sh flags → CC_* env vars → hooks.py (loads YAML config) → SessionStart hook → sessions table
                                                                → Event processor reads session settings
                                                                → TTS manager uses session-specific config

Note: .env file (standalone mode only) is loaded by config.py, merges with shell environment
```

## Audio System

### TTS Provider Chain

**Factory Pattern** (`utils/tts_providers/factory.py`):

- Registry: prerecorded, gtts, elevenlabs
- Tries providers left-to-right until success
- Smart parameter filtering based on provider capabilities

**Providers**:

- **Prerecorded**: Maps events to sound files in `/sound` (always available)
- **GTTS**: Google TTS via gtts library (free, internet required)
- **ElevenLabs**: Premium TTS (requires API key)

**TTSManager** (`utils/tts_manager.py`):

- Holds ordered provider list
- `get_sound()` tries each provider sequentially
- Global instance via `initialize_tts_manager()`

### Audio Mappings

**Events with TTS announcements**:

- **Always**: SessionStart, SessionEnd, Stop, PreCompact
- **Conditional** (only with `--ai=full`): PreToolUse

**Events with sound effects**:

- PreToolUse: `sound_effect_tek.mp3`
- PostToolUse: `sound_effect_cetek.mp3`
- UserPromptSubmit: `sound_effect_klek.mp3`
- Notification: `sound_effect_tung.mp3`
- SubagentStop: `sound_effect_cetek.mp3`

**Note**: PreToolUse has BOTH sound effect (always) AND announcement (only with `--ai=full` for
contextual tool messages)

**Status Line Indicators**:

The status line provides visual feedback about audio system state:

- **TTS Status**: Shows "🔇 Muted" when `--silent=announcements` is active
- **Sound Effects Status**: Shows "🔕 Effects" when `--silent=sound-effects` is active
- **OpenRouter Status**: Shows "Disabled (silent mode)" when announcements are muted
- **Example** (all audio muted):
  `🎧 🟢 cc-hooks:12222  🔇 Muted  🔕 Effects  🔀 Disabled (silent mode)`

### Text Processing

**TTS Announcer** (`utils/tts_announcer.py`):

1. Gets session-specific TTS settings from DB
2. Prepares text (contextual AI or fallback)
3. Cleans text (removes markdown, converts camelCase)
4. Calls TTSManager to generate audio
5. Plays via sound_player

**Text Cleaning**:

- Removes backticks, markdown formatting
- Keeps link text, removes URLs
- Converts underscores to spaces
- Converts camelCase to "spaced words"
- Removes symbols, lowercases

## AI Features

### OpenRouter Integration

**Disabled by default** (cost control). Enable with `--ai=basic` or `--ai=full`.

**Service** (`utils/openrouter_service.py`):

- `translate_text()`: Translate to target language
- `generate_completion_message()`: Contextual Stop messages
- `generate_pre_tool_message()`: Contextual PreToolUse messages

**Contextual Messages**:

- Uses transcript parser to extract conversation context
- OpenRouter generates dynamic messages based on user prompts and Claude responses
- No-cache strategy ensures freshness

**Cost Optimization**:

- **Silent mode optimization**: When `--silent=announcements` is active, OpenRouter API calls are
  automatically skipped to save costs
- The `announce_event` function exits early before calling `_prepare_text_for_event`, preventing
  expensive OpenRouter calls for contextual messages that won't be played
- Status line displays "Disabled (silent mode)" to indicate OpenRouter is inactive due to silent
  announcements mode

### Transcript Parsing

**Purpose**: Extract conversation context for AI features.

**Parser** (`utils/transcript_parser.py`):

- Reads JSONL transcript file
- Finds last user prompt + Claude response
- Deduplicates via SHA256 hashing
- Tracks via `/tmp/cc-hooks-transcripts/last-processed-{session_id}.txt`
- Cleans old tracking files (> 24 hours)

## Development

### Running the System

**Standalone Mode**:

```bash
# From cc-hooks directory
./claude.sh                    # Start server + Claude Code
npm run dev                    # Development server with hot reload
uv run server.py --dev         # Alternative dev server
uv run server.py               # Server only (testing)
npm run format                 # Format code
```

**Plugin Mode**:

```bash
# Using CLI wrapper (recommended)
~/.claude/plugins/marketplaces/cc-hooks-plugin/claude.sh

# Or set up alias (add to .bashrc/.zshrc)
alias cld='~/.claude/plugins/marketplaces/cc-hooks-plugin/claude.sh'
cld                            # Start with audio feedback

# Development/testing from plugin directory
cd ~/.claude/plugins/marketplaces/cc-hooks-plugin
uv run server.py --dev         # Dev server
npm run format                 # Format code
```

**Note**: Both modes use the same `claude.sh` script with identical flags. Only the path differs.

### Testing

```bash
# Start test server
uv run server.py &
SERVER_PID=$!

# Test hook manually
echo '{"session_id": "test", "hook_event_name": "SessionStart"}' | \
  CC_INSTANCE_ID="test-123" CC_HOOKS_PORT=12222 uv run hooks.py --announce=0.5

# Test with sound effect
echo '{"session_id": "test", "hook_event_name": "PreToolUse", "tool_name": "Bash"}' | \
  CC_INSTANCE_ID="test-123" CC_HOOKS_PORT=12222 uv run hooks.py --sound-effect=sound_effect_tek.mp3

# Test contextual messages (requires OpenRouter)
echo '{"session_id": "test", "hook_event_name": "Stop", "transcript_path": "/path/to/transcript.jsonl"}' | \
  CC_INSTANCE_ID="test-123" CC_HOOKS_PORT=12222 uv run hooks.py --announce=0.8

# Test language override
export CC_TTS_LANGUAGE=id
echo '{"session_id": "test", "hook_event_name": "SessionStart"}' | \
  CC_INSTANCE_ID="test-123" CC_HOOKS_PORT=12222 uv run hooks.py --announce=0.5

# Clean up
kill $SERVER_PID
```

### Testing Utilities

```bash
# Sound player
uv run utils/sound_player.py                          # Play default sound
uv run utils/sound_player.py sound_effect_cetek.mp3   # Play specific sound
uv run utils/sound_player.py --list                   # List available sounds
uv run utils/sound_player.py --volume 0.3 sound_effect_tek.mp3

# TTS announcer
uv run utils/tts_announcer.py --list                  # Show TTS system status
uv run utils/tts_announcer.py SessionStart            # Test announcement
uv run utils/tts_announcer.py --provider gtts SessionStart
uv run utils/tts_announcer.py --provider prerecorded Stop

# Transcript parser
uv run utils/transcript_parser.py /path/to/transcript.jsonl              # JSON output
uv run utils/transcript_parser.py --format text /path/to/transcript.jsonl
uv run utils/transcript_parser.py --verbose /path/to/transcript.jsonl
uv run utils/transcript_parser.py --start-line 10 --end-line 20 /path/to/transcript.jsonl
```

### API Endpoints

```bash
# Health check
curl http://localhost:12222/health

# Submit event
curl -X POST http://localhost:12222/events \
  -H "Content-Type: application/json" \
  -d '{"data": {"session_id": "test", "hook_event_name": "SessionStart"}, "arguments": {"sound_effect": "sound_effect_cetek.mp3"}}'

# Check for updates
curl http://localhost:12222/version/status
curl http://localhost:12222/version/status?force=true  # Force fresh check

# Session management
curl http://localhost:12222/sessions/{session_id}
curl http://localhost:12222/sessions/count
curl -X POST http://localhost:12222/sessions  # Create new session
curl -X DELETE http://localhost:12222/sessions/{session_id}

# Event queries
curl http://localhost:12222/events  # Query events

# Instance management
curl http://localhost:12222/instances/{instance_id}/last-event  # Get last event status
curl http://localhost:12222/instances/{claude_pid}/settings    # Get instance settings

# Database
curl http://localhost:12222/migrations/status  # Get migration status

# Shutdown
curl -X POST http://localhost:12222/shutdown
```

### Database Management

```bash
# View recent events
sqlite3 ~/.claude/.cc-hooks/events.db "SELECT id, session_id, hook_event_name, status, instance_id FROM events ORDER BY created_at DESC LIMIT 10;"

# View events for specific instance
sqlite3 ~/.claude/.cc-hooks/events.db "SELECT id, hook_event_name, status FROM events WHERE instance_id = '12345:12222' ORDER BY created_at DESC LIMIT 10;"

# View events for specific session
sqlite3 ~/.claude/.cc-hooks/events.db "SELECT id, hook_event_name, status, instance_id FROM events WHERE session_id = 'your-session-id' ORDER BY created_at DESC LIMIT 10;"

# Clear failed events
sqlite3 ~/.claude/.cc-hooks/events.db "DELETE FROM events WHERE status = 'failed';"
sqlite3 ~/.claude/.cc-hooks/events.db "DELETE FROM events WHERE status = 'failed' AND instance_id = '12345:12222';"
```

## Updating cc-hooks

### Plugin Mode (Recommended)

```bash
# Update via Claude plugin system
claude plugin marketplace update cc-hooks-plugin

# Or inside Claude REPL
/plugin update cc-hooks@cc-hooks-plugin

# Check for updates (via API)
curl http://localhost:12222/version/status
```

### Standalone Mode

```bash
# Update to latest version
npm run update
# or: ./update.sh

# Check for updates
npm run version:check
curl http://localhost:12222/version/status
```

**Update Process (Standalone)**:

1. Stashes uncommitted changes (if any)
2. Fetches latest from origin
3. Pulls changes from main branch
4. Verifies `uv` installation
5. Restores stashed changes

**Important**: Restart Claude Code session after updating in either mode.

## Adding Features

### New Event Handler

Add to `HOOK_AUDIO_MAPPINGS` in `utils/audio_mappings.py`:

```python
"YourEvent": AudioConfig(
    sound_effect="your_sound.mp3",  # Optional
    has_announcement=True,           # Whether to generate TTS
),
```

Update `EVENT_CONFIGS` in `app/event_processor.py` if needed:

```python
HookEvent.YOUR_EVENT.value: {
    "log_message": "Session {session_id}: Your event triggered",
    "clear_tracking": False,
    "use_tool_name": False,
}
```

### New TTS Provider

1. Create class in `utils/tts_providers/` inheriting from `TTSProvider`
2. Implement: `generate()`, `get_supported_params()`, `is_available()`
3. Register in `utils/tts_providers/factory.py`
4. Add to CLI flag handling in `claude.sh`

### Hook Arguments

Arguments automatically parsed from `--key=value` format:

```bash
# In hook call
uv run hooks.py --sound-effect=custom.mp3 --announce=0.5 --debug

# Access in event processor
arguments.get('sound_effect')  # "custom.mp3"
arguments.get('announce')      # "0.5"
arguments.get('debug')         # True (flag without value)
```

## Dependencies

### Main Application

**PEP 723 inline declarations** in `server.py` and `hooks.py` (managed by `uv`):

- FastAPI/Uvicorn: API server
- aiosqlite: Async database
- pygame: Cross-platform audio
- gtts, elevenlabs: TTS providers
- openai: OpenRouter integration
- psutil: Process management
- coloredlogs: Per-component colored logging

### Standalone Scripts

**All utility scripts and test files use PEP 723** for dependency isolation:

```python
# /// script
# dependencies = ["aiosqlite", "python-dotenv"]
# ///
```

This pattern allows:

- Self-contained scripts with explicit dependencies
- No global environment pollution
- Easy testing and debugging
- Run directly with `uv run script.py`

**Benefits:**

- Each script declares only what it needs
- Version conflicts isolated per script
- Works across different environments
- No need for separate requirements.txt for dev tools

## Important Gotchas

1. **Temporal Filtering**: Only events created AFTER server startup are processed (prevents old
   events)
2. **Port Auto-assignment**: Each instance finds available port starting from 12222
3. **Migration Safety**: Migrations are append-only, never modify existing ones
4. **Contextual Costs**: OpenRouter features disabled by default (enable with `--ai=basic|full`)
5. **Silent Mode Optimization**: When `--silent=announcements` is active, OpenRouter API calls are
   automatically skipped to save costs (announcements won't be played anyway)
6. **Session Lookup**: Port discovery tries 12222-12271 (50 ports) to handle race conditions
7. **Cleanup Race Window**: Port binding check prevents killing servers during registration
8. **Conservative Cleanup**: Better to keep possibly-valid processes than kill valid ones
9. **Fire-and-Forget**: hooks.py returns immediately, no error feedback from processing
10. **Event Ownership**: Each server only processes its own session's events (critical for
    isolation)
11. **Async/Sync Bridge**: Uses `loop.run_in_executor()` for sync TTS operations in async context
12. **Plugin Hook Metadata Error**: If you see "Plugin hook error: Reading inline script metadata"
    during SessionStart, this typically happens when Claude CLI is being auto-updated by Anthropic.
    Solution: Simply restart your Claude session after the update completes.

## Key Files Reference

| File                        | Lines | Purpose                           |
| --------------------------- | ----- | --------------------------------- |
| hooks.py                    | 723   | Entry point, lifecycle management |
| server.py                   | 157   | FastAPI server startup            |
| app/event_processor.py      | 546   | Background event processing       |
| app/event_db.py             | 871   | SQLite operations, orphan cleanup |
| app/api.py                  | 537   | REST API endpoints                |
| utils/tts_announcer.py      | 749   | TTS orchestration                 |
| utils/transcript_parser.py  | 552   | Conversation context extraction   |
| utils/openrouter_service.py | 688   | AI service integration            |
| utils/tts_manager.py        | 194   | Provider chain management         |
| utils/version_checker.py    | 337   | Update detection                  |

## Environment Variables Reference

### Per-Session (via CLI flags, stored in DB)

**Audio Control**:

- `CC_TTS_PROVIDERS`: TTS provider chain (e.g., "elevenlabs,gtts,prerecorded")
- `CC_TTS_LANGUAGE`: Language code (e.g., "id", "es", "en")
- `CC_TTS_CACHE_ENABLED`: Enable/disable TTS cache (true/false)
- `CC_ELEVENLABS_VOICE_ID`: ElevenLabs voice ID override
- `CC_ELEVENLABS_MODEL_ID`: ElevenLabs model override

**AI Features**:

- `CC_OPENROUTER_ENABLED`: Enable OpenRouter (true/false)
- `CC_OPENROUTER_MODEL`: AI model override
- `CC_OPENROUTER_CONTEXTUAL_STOP`: Enable contextual Stop messages
- `CC_OPENROUTER_CONTEXTUAL_PRETOOLUSE`: Enable contextual PreToolUse messages

**Silent Mode**:

- `CC_SILENT_ANNOUNCEMENTS`: Disable TTS announcements (true/false)
- `CC_SILENT_EFFECTS`: Disable sound effects (true/false)

### Global (via .env file)

**API Keys**:

- `ELEVENLABS_API_KEY`: ElevenLabs API key
- `OPENROUTER_API_KEY`: OpenRouter API key

**Global Defaults** (optional):

- `TTS_PROVIDERS`: Default provider chain
- `TTS_LANGUAGE`: Default language
- `TTS_CACHE_ENABLED`: Default cache setting

### Internal (set by hooks.py)

- `CC_HOOKS_PORT`: Server port for this session
- `CC_INSTANCE_ID`: Instance identifier "{claude_pid}:{server_port}"

## Common Development Tasks

### Add New Sound Effect

1. Add MP3 file to `/sound` directory
2. Update `HOOK_AUDIO_MAPPINGS` in `utils/audio_mappings.py`
3. Test with: `uv run utils/sound_player.py your_sound.mp3`

### Add New Hook Event

1. Add to `HookEvent` enum in `utils/constants.py`
2. Add audio mapping in `utils/audio_mappings.py`
3. Add event config in `app/event_processor.py` (if needed)
4. Test with manual hook call

### Debug Event Processing

1. Check server logs: `tail -f ~/.claude/.cc-hooks/logs/{claude_pid}.log`
2. Check database:
   `sqlite3 ~/.claude/.cc-hooks/events.db "SELECT * FROM events ORDER BY created_at DESC LIMIT 5;"`
3. Check session settings: `sqlite3 ~/.claude/.cc-hooks/events.db "SELECT * FROM sessions;"`
4. Test TTS directly: `uv run utils/tts_announcer.py SessionStart`

### Change TTS Provider Priority

Update provider order (left = highest priority):

```bash
./claude.sh --audio=elevenlabs  # elevenlabs,gtts,prerecorded
./claude.sh --audio=gtts        # gtts,prerecorded
./claude.sh --audio=prerecorded # prerecorded only
```

### Add New Language Support

1. Test GTTS: `uv run utils/tts_announcer.py --provider gtts SessionStart` with
   `CC_TTS_LANGUAGE=your_lang`
2. Update OpenRouter prompts if needed for translations
3. Test with: `./claude.sh --language=your_lang`

### Create Test/Utility Scripts

**Always use PEP 723** for standalone scripts:

```python
#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["aiosqlite", "python-dotenv", "coloredlogs"]
# ///

"""Brief description of what this script does"""

import asyncio
# Import from codebase
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from app.some_module import some_function

async def main():
    # Your logic here
    pass

if __name__ == "__main__":
    asyncio.run(main())
```

**Key points:**

- Add shebang for direct execution: `#!/usr/bin/env -S uv run --script`
- Declare dependencies in PEP 723 header
- Add docstring describing purpose
- Use `sys.path.insert(0, ...)` to import from codebase
- Run with: `uv run your_script.py` or make executable and run directly

### Add New Database Migration

**CRITICAL RULES:**

1. **One statement per migration** - Never combine multiple SQL statements in single migration
2. **Append-only** - Never modify existing migrations that are deployed
3. **Use PEP 723** - For testing migrations, use inline script dependencies

**Example:**

```python
# Add to MIGRATIONS list in app/migrations.py
{
    "version": 11,
    "description": "Add new column to sessions",
    "sql": "ALTER TABLE sessions ADD COLUMN new_field TEXT NULL",
},
```

**Testing migrations:**

Create a standalone test script with PEP 723:

```python
#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["aiosqlite", "python-dotenv", "coloredlogs"]
# ///

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from app.migrations import run_migrations, get_migration_status

async def main():
    await run_migrations()
    status = await get_migration_status()
    print(f"Current version: {status['current_version']}")

asyncio.run(main())
```

Run with: `uv run test_migration.py` or `chmod +x test_migration.py && ./test_migration.py`
