# cc-hooks

Advanced Claude Code hooks processing system with contextual TTS announcements, AI-powered completion messages, multilingual translation, and event-driven automation.

## Overview

cc-hooks acts as a middleware server between Claude Code and your custom event processing logic. It queues Claude Code hook events in SQLite and processes them sequentially without blocking Claude Code operations. Features include:

- **Contextual TTS announcements** with intelligent event mapping
- **AI-powered completion messages** using OpenRouter integration  
- **Multi-provider TTS system** (prerecorded, Google TTS, ElevenLabs)
- **Multilingual translation** support
- **Sound effects** and audio feedback
- **Multi-instance Claude Code support** with shared server architecture

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
       "SessionStart": [{
         "matcher": "",
         "hooks": [{
           "type": "command",
           "command": "uv run /path/to/cc-hooks/hooks.py --announce"
         }]
       }],
       "SessionEnd": [{
         "matcher": "",
         "hooks": [{
           "type": "command", 
           "command": "uv run /path/to/cc-hooks/hooks.py --announce"
         }]
       }],
       "PreToolUse": [{
         "matcher": "",
         "hooks": [{
           "type": "command",
           "command": "uv run /path/to/cc-hooks/hooks.py --sound-effect=sound_effect_tek.mp3"
         }]
       }],
       "PostToolUse": [{
         "matcher": "",
         "hooks": [{
           "type": "command",
           "command": "uv run /path/to/cc-hooks/hooks.py --sound-effect=sound_effect_cetek.mp3"
         }]
       }],
       "Notification": [{
         "matcher": "",
         "hooks": [{
           "type": "command",
           "command": "uv run /path/to/cc-hooks/hooks.py --announce --sound-effect=sound_effect_tung.mp3"
         }]
       }],
       "UserPromptSubmit": [{
         "matcher": "",
         "hooks": [{
           "type": "command",
           "command": "uv run /path/to/cc-hooks/hooks.py --sound-effect=sound_effect_klek.mp3"
         }]
       }],
       "Stop": [{
         "matcher": "",
         "hooks": [{
           "type": "command",
           "command": "uv run /path/to/cc-hooks/hooks.py --announce"
         }]
       }],
       "SubagentStop": [{
         "matcher": "",
         "hooks": [{
           "type": "command",
           "command": "uv run /path/to/cc-hooks/hooks.py --sound-effect=sound_effect_cetek.mp3"
         }]
       }],
       "PreCompact": [{
         "matcher": "",
         "hooks": [{
           "type": "command",
           "command": "uv run /path/to/cc-hooks/hooks.py --announce"
         }]
       }]
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

This starts both the cc-hooks server and Claude Code with proper lifecycle management while preserving your current working directory. Claude Code will run from wherever you execute the `cld` command.

## Environment Variables

Configuration is handled through `.env` file. Key variables:

### Core Settings
- `HOST=0.0.0.0` - Server host
- `PORT=12222` - Server port
- `DB_PATH=events.db` - SQLite database path

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
- `ELEVENLABS_VOICE_ID=iWydkXKoiVtvdn4vLKp9` - Voice ID ([find voices](https://elevenlabs.io/app/voice-lab))
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

## API Key Setup

- **OpenRouter**: Get your key at [openrouter.ai/keys](https://openrouter.ai/keys) - enables AI translation and contextual messages
- **ElevenLabs**: Get your key at [elevenlabs.io/app/developers/api-keys](https://elevenlabs.io/app/developers/api-keys) - enables premium voice synthesis

## Credits

Sound effects generated using [ElevenLabs](https://elevenlabs.io) voice synthesis technology.

## License

MIT - see [LICENSE](LICENSE) for details.