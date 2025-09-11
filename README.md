# cc-hooks

Advanced Claude Code hooks processing system with contextual TTS announcements, AI-powered
completion messages, multilingual translation, and event-driven automation.

## Overview

cc-hooks acts as a middleware server between Claude Code and your custom event processing logic. It
queues Claude Code hook events in SQLite and processes them sequentially without blocking Claude
Code operations. Features include:

- **Contextual TTS announcements** with intelligent event mapping
- **AI-powered completion messages** using OpenRouter integration
- **Multi-provider TTS system** (prerecorded, Google TTS, ElevenLabs)
- **Multilingual translation** support
- **Sound effects** and audio feedback
- **Multi-instance Claude Code support** with dedicated servers per instance

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- [Claude Code](https://claude.ai/code) CLI tool
- SQLite (included with Python)

## Installation & Claude Code Integration

1. **Clone and setup dependencies:**

   ```bash
   git clone https://github.com/husniadil/cc-hooks.git
   cd cc-hooks
   ```

2. **Configure environment:**

   ```bash
   cp .env.example .env
   # Edit .env with your preferences (see Environment Variables section)
   ```

3. **Add hooks to Claude Code settings:**

   Edit your Claude Code settings (typically `~/.claude/settings.json`):

   ```json
   {
     "$schema": "https://json.schemastore.org/claude-code-settings.json",
     "model": "sonnet",
     "hooks": {
       "SessionStart": [
         {
           "matcher": "",
           "hooks": [
             {
               "type": "command",
               "command": "uv run /path/to/cc-hooks/hooks.py --announce"
             }
           ]
         }
       ],
       "SessionEnd": [
         {
           "matcher": "",
           "hooks": [
             {
               "type": "command",
               "command": "uv run /path/to/cc-hooks/hooks.py --announce"
             }
           ]
         }
       ],
       "PreToolUse": [
         {
           "matcher": "",
           "hooks": [
             {
               "type": "command",
               "command": "uv run /path/to/cc-hooks/hooks.py --sound-effect=sound_effect_tek.mp3"
             }
           ]
         }
       ],
       "PostToolUse": [
         {
           "matcher": "",
           "hooks": [
             {
               "type": "command",
               "command": "uv run /path/to/cc-hooks/hooks.py --sound-effect=sound_effect_cetek.mp3"
             }
           ]
         }
       ],
       "Notification": [
         {
           "matcher": "",
           "hooks": [
             {
               "type": "command",
               "command": "uv run /path/to/cc-hooks/hooks.py --announce --sound-effect=sound_effect_tung.mp3"
             }
           ]
         }
       ],
       "UserPromptSubmit": [
         {
           "matcher": "",
           "hooks": [
             {
               "type": "command",
               "command": "uv run /path/to/cc-hooks/hooks.py --sound-effect=sound_effect_klek.mp3"
             }
           ]
         }
       ],
       "Stop": [
         {
           "matcher": "",
           "hooks": [
             {
               "type": "command",
               "command": "uv run /path/to/cc-hooks/hooks.py --announce"
             }
           ]
         }
       ],
       "SubagentStop": [
         {
           "matcher": "",
           "hooks": [
             {
               "type": "command",
               "command": "uv run /path/to/cc-hooks/hooks.py --sound-effect=sound_effect_cetek.mp3"
             }
           ]
         }
       ],
       "PreCompact": [
         {
           "matcher": "",
           "hooks": [
             {
               "type": "command",
               "command": "uv run /path/to/cc-hooks/hooks.py --announce"
             }
           ]
         }
       ]
     },
     "statusLine": {
       "type": "command",
       "command": "uv run /path/to/cc-hooks/status-lines/status_line.py"
     }
   }
   ```

   Replace `/path/to/cc-hooks` with the actual absolute path to your cc-hooks installation.

4. **Validate installation:**

   ```bash
   # Basic validation
   ./check_setup.sh

   # Detailed validation with verbose output
   ./check_setup.sh --verbose
   ```

   The setup script validates:
   - System dependencies (Python 3.12+, uv, Claude CLI)
   - Claude Code settings configuration
   - Environment variables and API keys
   - File structure and permissions
   - Functional tests (server startup, hook scripts, TTS)

## Setup Alias

Add this alias to your shell config (`.bashrc`, `.zshrc`, etc.):

```bash
cld() {
    local original_dir="$PWD"
    (cd /path/to/cc-hooks && CC_ORIGINAL_DIR="$original_dir" ./claude.sh "$@")
}
```

This starts both the cc-hooks server and Claude Code with proper lifecycle management while
preserving your current working directory. Claude Code will run from wherever you execute the `cld`
command.

## Environment Variables

Configuration is handled through `.env` file. Key variables:

### Core Settings

- `DB_PATH=events.db` - SQLite database path
- `MAX_RETRY_COUNT=3` - Event retry attempts
- **Note**: Server host/port are now auto-managed per Claude Code instance

### TTS Configuration

- `TTS_PROVIDERS=prerecorded` - Provider priority (comma-separated)
- `TTS_LANGUAGE=en` - Language for TTS generation
- `TTS_CACHE_ENABLED=true` - Enable TTS file caching

### OpenRouter Integration

- `OPENROUTER_ENABLED=false` - Enable AI features
- `OPENROUTER_API_KEY=` - Your API key ([get here](https://openrouter.ai/keys))
- `OPENROUTER_MODEL=openai/gpt-4o-mini` - Model for AI requests
- `OPENROUTER_CONTEXTUAL_STOP=false` - AI completion messages (costs apply!)
- `OPENROUTER_CONTEXTUAL_PRETOOLUSE=false` - AI tool announcements (costs apply!)

### ElevenLabs Configuration

- `ELEVENLABS_API_KEY=` - Your API key ([get here](https://elevenlabs.io/app/developers/api-keys))
- `ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM` - Voice ID (Rachel voice)
  ([find voices](https://elevenlabs.io/app/voice-lab))
- `ELEVENLABS_MODEL_ID=eleven_flash_v2_5` - Model for generation

## Quick Start

```bash
# Start server + Claude Code
./claude.sh

# Or use your alias (recommended)
cld

# Development server with hot reload
uv run server.py --dev
```

## Hook Command Arguments

The hook script (`hooks.py`) supports various command-line arguments that enhance the event
processing experience. These arguments work in synergy with your `.env` configuration.

### Core Arguments

**`--sound-effect=<filename>`**

- Triggers specific sound effect playback during event processing
- Sound files should be placed in the `sound/` directory
- Supports common audio formats (WAV, MP3, OGG, etc.)
- Example: `--sound-effect=sound_effect_tek.mp3`

**`--announce[=<volume>]`**

- Enables TTS (Text-to-Speech) announcements for events
- Optional volume control: `0.0` (silent) to `1.0` (full volume)
- Uses TTS providers configured in your `.env` file
- Example: `--announce=0.5` or just `--announce` (default volume)

**`--debug`**

- Enables verbose logging and debugging output
- Helpful for troubleshooting hook processing issues

### How Arguments Sync with Environment Variables

The command-line arguments work alongside your `.env` configuration:

#### TTS Announcements (`--announce`)

```bash
# .env configuration affects TTS behavior
TTS_PROVIDERS=gtts,prerecorded     # Provider priority chain
TTS_LANGUAGE=en                    # Language for announcements
TTS_CACHE_ENABLED=true            # Cache generated audio files
OPENROUTER_ENABLED=true           # Enable AI translation (if language ≠ en)

# Hook command uses these settings
"command": "uv run hooks.py --announce=0.8"
```

#### Sound Effects (`--sound-effect`)

```bash
# Sound effects work independently of TTS configuration
# But can be combined with TTS announcements
"command": "uv run hooks.py --sound-effect=beep.mp3 --announce"
```

#### AI-Powered Contextual Messages

```bash
# .env configuration for dynamic messages
OPENROUTER_ENABLED=true
OPENROUTER_CONTEXTUAL_STOP=true           # AI completion messages
OPENROUTER_CONTEXTUAL_PRETOOLUSE=true     # AI tool announcements
OPENROUTER_API_KEY=your_key_here

# IMPORTANT: --announce is REQUIRED for contextual features to work
# Without --announce, contextual messages won't be generated
"command": "uv run hooks.py --announce"
```

> **⚠️ Critical Requirement**: Contextual AI features (`OPENROUTER_CONTEXTUAL_STOP` and
> `OPENROUTER_CONTEXTUAL_PRETOOLUSE`) **only work when `--announce` is specified** in your hook
> commands. Without `--announce`, the system won't trigger TTS processing and thus won't generate
> contextual messages.

### Practical Configuration Examples

#### Minimal Setup (Sound Effects Only)

```bash
# .env - minimal configuration
TTS_PROVIDERS=prerecorded

# Claude Code settings
"PreToolUse": [{
  "hooks": [{"command": "uv run hooks.py --sound-effect=click.mp3"}]
}]
```

#### Google TTS with Sound Effects

```bash
# .env - Google TTS enabled
TTS_PROVIDERS=gtts,prerecorded
TTS_LANGUAGE=en
TTS_CACHE_ENABLED=true

# Claude Code settings - combines sound + TTS
"SessionStart": [{
  "hooks": [{"command": "uv run hooks.py --sound-effect=startup.mp3 --announce=0.7"}]
}]
```

#### Premium Setup (ElevenLabs + AI Context)

```bash
# .env - full premium configuration
TTS_PROVIDERS=elevenlabs,gtts,prerecorded
ELEVENLABS_API_KEY=your_key_here
OPENROUTER_ENABLED=true
OPENROUTER_CONTEXTUAL_STOP=true
OPENROUTER_CONTEXTUAL_PRETOOLUSE=true

# Claude Code settings - AI-powered contextual announcements
"Stop": [{
  "hooks": [{"command": "uv run hooks.py --announce"}]
}],
"PreToolUse": [{
  "hooks": [{"command": "uv run hooks.py --sound-effect=tool.mp3 --announce=0.6"}]
}]
```

#### Multilingual Setup (Indonesian)

```bash
# .env - Indonesian TTS with AI translation
TTS_PROVIDERS=gtts,prerecorded
TTS_LANGUAGE=id                           # Indonesian
OPENROUTER_ENABLED=true                   # Required for translation
OPENROUTER_API_KEY=your_key_here

# Hook commands remain the same - translation is automatic
"SessionStart": [{
  "hooks": [{"command": "uv run hooks.py --announce"}]
}]
```

### Testing Your Configuration

```bash
# Test specific event with your settings
echo '{"session_id": "test", "hook_event_name": "SessionStart"}' | uv run hooks.py --announce

# Test sound effect only
echo '{"session_id": "test", "hook_event_name": "PreToolUse"}' | uv run hooks.py --sound-effect=click.mp3

# Test combined sound + TTS
echo '{"session_id": "test", "hook_event_name": "Stop"}' | uv run hooks.py --sound-effect=done.mp3 --announce=0.5

# Test with debug output
echo '{"session_id": "test", "hook_event_name": "Test"}' | uv run hooks.py --debug --announce
```

### Common Issues & Troubleshooting

**Contextual AI messages not working?**

- ✅ Ensure `OPENROUTER_ENABLED=true` in your `.env`
- ✅ Verify `OPENROUTER_API_KEY` is set correctly
- ✅ **Most importantly**: Add `--announce` to your hook commands - contextual features require TTS
  processing to activate
- ✅ Check that `OPENROUTER_CONTEXTUAL_STOP=true` or `OPENROUTER_CONTEXTUAL_PRETOOLUSE=true` are set

**Example of incorrect configuration:**

```json
// ❌ This won't trigger contextual messages (missing --announce)
"Stop": [{"hooks": [{"command": "uv run hooks.py"}]}]

// ✅ This will trigger contextual messages
"Stop": [{"hooks": [{"command": "uv run hooks.py --announce"}]}]
```

## API Key Setup

- **OpenRouter**: Get your key at [openrouter.ai/keys](https://openrouter.ai/keys) - enables AI
  translation and contextual messages
- **ElevenLabs**: Get your key at
  [elevenlabs.io/app/developers/api-keys](https://elevenlabs.io/app/developers/api-keys) - enables
  premium voice synthesis

## Development

For developers extending the codebase, the system uses centralized constants in `utils/constants.py`
for better maintainability:

- **Network settings**: `NetworkConstants.DEFAULT_PORT`, `get_server_url()` helper
- **Date/time formatting**: `DateTimeConstants.ISO_DATETIME_FORMAT`
- **HTTP status codes**: `HTTPStatusConstants.INTERNAL_SERVER_ERROR`
- **Event processing**: `ProcessingConstants` for timing and behavior

This ensures consistent values across the codebase and makes updates easier.

## Credits

Sound effects generated using [ElevenLabs](https://elevenlabs.io) voice synthesis technology.

## License

MIT - see [LICENSE](LICENSE) for details.
