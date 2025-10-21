# cc-hooks

![cc-hooks Banner](public/banner.png)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![DeepWiki](https://img.shields.io/badge/DeepWiki-cc--hooks-blue)](https://deepwiki.com/husniadil/cc-hooks)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Enhanced-orange)](https://www.anthropic.com/claude-code)
[![Audio](https://img.shields.io/badge/Audio-TTS%20%2B%20Sound%20Effects-purple)]()

**Give Claude Code a voice!** Transform your coding experience with intelligent audio feedback,
multilingual TTS announcements, and AI-powered contextual messages.

## Why cc-hooks?

Working with Claude Code is powerful, but it can feel silent and disconnected. **cc-hooks** brings
your coding sessions to life:

- 🎯 **Stay in the flow** - Audio cues keep you informed without breaking focus
- 🔊 **Instant feedback** - Know when tools start, complete, or when Claude needs your attention
- 🗣️ **Smart announcements** - Context-aware messages that understand what you're working on
- 🌍 **Your language** - TTS support for multiple languages (English, Indonesian, Spanish, and more)
- ⚡ **Zero config** - Works out of the box, customize when you need it
- 🎛️ **Flexible control** - From complete silence to premium AI voices, you choose

## Quick Demo

[![ElevenLabs TTS Demo](public/thumbnail.png)](https://www.youtube.com/watch?v=VXkKhgeZ-xU)

_Watch cc-hooks in action with premium ElevenLabs text-to-speech_

## Features

### 🎵 Audio Feedback System

- **Sound effects** for different events (tool execution, notifications, completions)
- **Voice announcements** for session lifecycle and task completions
- **Multiple TTS providers**: Prerecorded sounds (offline), Google TTS (free), ElevenLabs (premium)
- **Smart fallback chain** - automatically tries next provider if one fails

### 🤖 AI-Powered Intelligence (Optional)

- **Contextual completion messages** - "I've successfully implemented the authentication system you
  requested"
- **Smart tool announcements** - Understands what Claude is doing and why
- **Automatic translation** - AI messages in your preferred language
- **Cost optimized** - Disabled by default, enable per session when needed

### ⚙️ Advanced Capabilities

- **Multi-instance support** - Run multiple Claude sessions with different audio configs
- **Granular silent modes** - Disable just announcements or just sound effects
- **Per-session configuration** - Change settings without editing config files
- **Auto-cleanup** - Smart session management prevents resource leaks
- **Status line integration** - See current session info in Claude Code UI

## Installation

### Choose Your Installation Mode

| Feature               | Plugin Mode ⭐ Recommended | Standalone Mode               |
| --------------------- | -------------------------- | ----------------------------- |
| **Setup Complexity**  | ✅ Simple (3 commands)     | ⚠️ Manual hooks configuration |
| **Updates**           | ✅ One command             | ⚠️ Git pull + restart         |
| **Slash Commands**    | ✅ Built-in                | ❌ Not available              |
| **Hooks Config**      | ✅ Automatic               | ⚠️ Manual (settings.json)     |
| **Installation Path** | Fixed location             | ✅ User-defined               |
| **For Contributors**  | ⚠️ Limited                 | ✅ Full source access         |
| **Recommended for**   | **Most users**             | Developers, testers           |

[**→ Continue with Plugin Installation**](#plugin-installation-recommended) |
[**→ Standalone Installation**](STANDALONE_README.md)

---

### Plugin Installation (Recommended)

#### Prerequisites

- **Python 3.12+** (recommended: 3.12.7)
- **[uv](https://docs.astral.sh/uv/)** package manager
- **Claude Code** CLI installed

#### Quick Install

**Option 1: CLI (Recommended - No REPL needed)**

```bash
# Add marketplace
claude plugin marketplace add https://github.com/husniadil/cc-hooks.git

# Install plugin
claude plugin install cc-hooks@cc-hooks-plugin

# Done! Start Claude to use
claude
```

**Option 2: Inside Claude REPL**

```bash
# Start Claude first
claude

# Then in the REPL:
/plugin marketplace add https://github.com/husniadil/cc-hooks.git
/plugin install cc-hooks@cc-hooks-plugin

# Restart Claude Code
```

**Start using!** Audio feedback works immediately with default prerecorded sounds. 🎉

#### Post-Installation Setup (Recommended)

After installation, use the interactive setup wizard:

```bash
# Inside Claude REPL
/cc-hooks-plugin:setup
```

This wizard helps you:

- ✅ Check system requirements (uv installation)
- ✅ Set up convenient shell aliases (`cld` command)
- ✅ Configure status line
- ✅ Set up API keys for premium features
- ✅ Choose preset configurations
- ✅ Test your installation

**Quick setup modes:**

```bash
/cc-hooks-plugin:setup check    # Check requirements and config only
/cc-hooks-plugin:setup apikeys  # Focus on API key setup
/cc-hooks-plugin:setup test     # Run installation tests
```

#### Status Line Setup (Optional)

The plugin includes a status line feature that shows session info in Claude Code UI. **This is not
configured automatically** and requires manual setup in `~/.claude/settings.json`:

```jsonc
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  // ...
  "statusLine": {
    "type": "command",
    "command": "uv run ~/.claude/plugins/marketplaces/cc-hooks-plugin/status-lines/status_line.py"
  }
}
```

**Benefits:**

- Shows current TTS provider, language, and AI mode
- Displays session info at a glance
- Real-time status updates

## Usage

### Quick Start

**Automated Setup (Easiest):**

```bash
# Inside Claude REPL
/cc-hooks-plugin:setup
```

**Manual Setup:**

Add shell alias to your `.bashrc` or `.zshrc`:

```bash
alias cld='~/.claude/plugins/marketplaces/cc-hooks-plugin/claude.sh'
```

Then reload: `source ~/.bashrc` or `source ~/.zshrc`

### Usage Examples

```bash
# Default: prerecorded sounds (offline, no config needed)
cld

# Google TTS in Indonesian
cld --audio=gtts --language=id

# Premium ElevenLabs voice
cld --audio=elevenlabs

# With AI-powered contextual messages
cld --audio=gtts --ai=full --language=id

# Silent mode for meetings
cld --silent
```

## Configuration

### CLI Flags Reference

#### Audio Providers

```bash
cld --audio=prerecorded  # Offline sounds (default, no API key)
cld --audio=gtts         # Google TTS (free, requires internet)
cld --audio=elevenlabs   # Premium quality (requires API key)
```

| Provider        | Quality | Cost | Requires Internet | API Key |
| --------------- | ------- | ---- | ----------------- | ------- |
| **prerecorded** | Good    | Free | ❌ No             | ❌ No   |
| **gtts**        | Great   | Free | ✅ Yes            | ❌ No   |
| **elevenlabs**  | Premium | Paid | ✅ Yes            | ✅ Yes  |

#### Language

```bash
cld --audio=gtts --language=id  # Indonesian
cld --audio=gtts --language=es  # Spanish
cld --audio=gtts --language=fr  # French
```

Supports any Google TTS or ElevenLabs language: `en`, `id`, `es`, `fr`, `de`, `ja`, and many more!

#### AI Features

```bash
cld --ai=basic  # Contextual completion messages only
cld --ai=full   # Completion + intelligent tool announcements
```

**Requires**: OpenRouter API key (`export OPENROUTER_API_KEY=your_key`)

**What you get:**

- "I've successfully implemented the authentication system you requested"
- "Running tests to validate the changes we just made"
- Messages automatically translated to your language

**Cost**: Very affordable (~$0.15 per 1M tokens)

#### Silent Modes

```bash
cld --silent                    # Complete silence
cld --silent=announcements      # No TTS, keep sound effects
cld --silent=sound-effects      # No sound effects, keep TTS
```

#### Advanced Flags

```bash
--elevenlabs-voice-id=ID        # Custom ElevenLabs voice
--elevenlabs-model=MODEL        # ElevenLabs model (default: eleven_flash_v2_5)
--openrouter-model=MODEL        # AI model (default: openai/gpt-4o-mini)
--no-cache                      # Disable TTS caching (for testing)
```

### API Keys Setup

For ElevenLabs or AI features, set API keys as environment variables:

```bash
# Add to your .bashrc or .zshrc
export ELEVENLABS_API_KEY=your_key_here
export OPENROUTER_API_KEY=your_key_here
```

**Get your keys:**

- **ElevenLabs**:
  [elevenlabs.io/app/developers/api-keys](https://elevenlabs.io/app/developers/api-keys)
- **OpenRouter**: [openrouter.ai/keys](https://openrouter.ai/keys) (free credits available)

### Configuration File (Recommended)

**Set your defaults once** - no need to use CLI flags every time!

**Location**: `~/.claude/.cc-hooks/config.yaml`

**Why use it?**

- ✅ **For Zed/Editors**: Only way to customize (editors can't pass CLI flags)
- ✅ **For Terminal**: Set once, run `claude` or `cld` - your preferences auto-apply
- ✅ **Still flexible**: CLI flags override config when needed

**Create config file:**

```bash
# Inside Claude REPL
/cc-hooks-plugin:setup

# Or manually create with defaults
uv run ~/.claude/plugins/marketplaces/cc-hooks-plugin/utils/config_loader.py --create-example

# Edit to your preferences
nano ~/.claude/.cc-hooks/config.yaml
```

**Example config** (Indonesian with Google TTS):

```yaml
audio:
  providers: gtts,prerecorded
  language: id
  cache_enabled: true

openrouter:
  enabled: false
```

**Example config** (Premium with AI):

```yaml
audio:
  providers: elevenlabs,gtts,prerecorded
  language: en
  cache_enabled: true

elevenlabs:
  voice_id: 21m00Tcm4TlvDq8ikWAM
  model_id: eleven_flash_v2_5

openrouter:
  enabled: true
  model: openai/gpt-4o-mini
  contextual_stop: true
```

**Priority**: CLI flags > Environment variables > Config file > Defaults

**This means:**

- Config file provides defaults for all sessions
- Run `cld --language=es` to override for one session
- Perfect for both Zed and terminal users!

### Example Configurations

```bash
# Work setup: Indonesian TTS with Google
cld --audio=gtts --language=id

# Premium experience: ElevenLabs + AI features
cld --audio=elevenlabs --ai=full

# Meeting mode: Sound effects only
cld --silent=announcements

# Testing: Premium voice without cache
cld --audio=elevenlabs --no-cache

# Multi-session workflow
# Terminal 1: Work project
cd ~/work-project
cld --audio=gtts --language=id

# Terminal 2: Side project with premium
cd ~/side-project
cld --audio=elevenlabs --ai=full

# Terminal 3: Silent for meetings
cd ~/meeting-notes
cld --silent
```

## Audio Event Mapping

| Event            | Sound Effect | TTS Announcement               |
| ---------------- | ------------ | ------------------------------ |
| SessionStart     | -            | ✅ Always                      |
| SessionEnd       | -            | ✅ Always                      |
| PreToolUse       | tek.mp3      | ✅ With AI=full                |
| PostToolUse      | cetek.mp3    | -                              |
| UserPromptSubmit | klek.mp3     | -                              |
| Notification     | tung.mp3     | -                              |
| Stop             | -            | ✅ Always (contextual with AI) |
| SubagentStop     | cetek.mp3    | -                              |
| PreCompact       | -            | ✅ Always                      |

**Notes:**

- Sound effects play regardless of `--audio` flag (unless `--silent` or `--silent=sound-effects`)
- TTS announcements use the configured provider (`--audio=prerecorded|gtts|elevenlabs`)
- PreToolUse only announces with `--ai=full` (contextual tool messages)
- Stop always announces, but uses AI contextual messages when `--ai=basic` or `--ai=full` is enabled

## Updating cc-hooks

### Check for Updates

Inside Claude REPL:

```bash
/cc-hooks-plugin:update
```

Or via CLI:

```bash
claude plugin marketplace update cc-hooks-plugin
```

**The update command will:**

- Detect your installation mode automatically
- Check for available updates
- Show current vs latest version
- Install updates with your confirmation
- Remind you to restart Claude Code

**Alternative methods:**

```bash
# CLI (outside Claude REPL)
claude plugin marketplace update cc-hooks-plugin

# Inside Claude REPL
/plugin update cc-hooks@cc-hooks-plugin
```

**Important**: Restart Claude Code session after updating.

## Troubleshooting

### Quick Diagnostics

Run `/cc-hooks-plugin:setup check` to verify your configuration.

### Plugin Hook Metadata Error?

**Error message:**

```
⎿  SessionStart:startup says: Plugin hook error: Reading inline script metadata from `~/.claude/plugins/marketplaces/cc-hooks-plugin//hooks.py`
   Installed 28 packages in 115ms
```

**Cause:** This typically occurs when Claude CLI is being auto-updated by Anthropic in the
background.

**Solution:** Simply restart your Claude session. The error should disappear after the update
completes.

### No audio at all?

1. Check system audio is working
2. Verify plugin is installed: `/plugin`
3. Run setup wizard: `/cc-hooks-plugin:setup test`
4. Check logs: `tail -f ~/.claude/.cc-hooks/logs/*.log`
5. Test manually: `uv run ~/.claude/plugins/marketplaces/cc-hooks-plugin/utils/sound_player.py`

### Google TTS not working?

1. Check internet connection
2. Test:
   `uv run ~/.claude/plugins/marketplaces/cc-hooks-plugin/utils/tts_announcer.py --provider gtts SessionStart`

### ElevenLabs not working?

1. Verify API key: `printenv ELEVENLABS_API_KEY`
2. Check quota at [elevenlabs.io](https://elevenlabs.io)
3. Test:
   `uv run ~/.claude/plugins/marketplaces/cc-hooks-plugin/utils/tts_announcer.py --provider elevenlabs SessionStart`

### AI contextual messages not working?

1. Verify API key: `printenv OPENROUTER_API_KEY`
2. Use `--ai=basic` or `--ai=full` flag when starting
3. Check OpenRouter API quota at [openrouter.ai](https://openrouter.ai)

### Database Issues

Check database exists:

```bash
ls -la ~/.claude/.cc-hooks/events.db
```

View recent events:

```bash
sqlite3 ~/.claude/.cc-hooks/events.db "SELECT id, hook_event_name, status FROM events ORDER BY created_at DESC LIMIT 10;"
```

## Data Storage

The plugin uses a shared data directory for persistence:

```
~/.claude/.cc-hooks/
├── events.db          # Event queue database
├── logs/              # Per-session logs
│   └── {pid}.log
└── .tts_cache/        # Cached TTS audio (if enabled)
```

**Why shared?** This directory persists across plugin updates, allowing seamless upgrades without
losing data.

## FAQ

**Q: Do I need API keys to use cc-hooks?**

No! Default mode uses prerecorded sounds and works completely offline with no API keys required.

**Q: Which TTS provider should I use?**

- **Prerecorded**: Fastest, offline, no costs (great for starting)
- **Google TTS**: Free, good quality, requires internet
- **ElevenLabs**: Premium quality, costs money, best voices

**Q: Can I use my own voice with ElevenLabs?**

Yes! Upload your voice at [elevenlabs.io/app/voice-lab](https://elevenlabs.io/app/voice-lab), then
use `--elevenlabs-voice-id=your_voice_id`

**Q: How much do AI features cost?**

OpenRouter has free credits to start. After that, costs vary by model. Use `--ai=basic` for minimal
costs (only completion messages). The default model is very cheap (~$0.15 per 1M tokens).

**Q: Can I run multiple Claude sessions with different audio settings?**

Yes! Each session is independent. Run `cld --audio=gtts` in one terminal and `cld --silent` in
another.

**Q: Does cc-hooks slow down Claude Code?**

No! cc-hooks uses a "fire-and-forget" pattern - hooks return immediately. Audio processing happens
in the background without blocking Claude.

**Q: What languages are supported?**

Any language supported by Google TTS or ElevenLabs. Common ones: English (en), Indonesian (id),
Spanish (es), French (fr), German (de), Japanese (ja), etc.

**Q: Can I disable just the voice but keep sound effects?**

Yes! Use `--silent=announcements` to disable TTS while keeping sound effects.

**Q: How do I migrate from standalone mode?**

See [MIGRATION.md](MIGRATION.md) for a comprehensive step-by-step guide.

**Q: Can I use cc-hooks in CI/CD?**

Yes, use `--silent` mode to disable all audio in automated environments.

**Q: Where are audio files cached?**

TTS cache is in `~/.claude/.cc-hooks/.tts_cache/` directory. Delete it with
`rm -rf ~/.claude/.cc-hooks/.tts_cache` to regenerate all audio.

**Q: How do I contribute?**

Pull requests welcome! For development, use [Standalone Mode](STANDALONE_README.md). See
[CLAUDE.md](CLAUDE.md) for development guide.

## Advanced Usage

### Custom ElevenLabs Voice

1. Upload voice at [elevenlabs.io/app/voice-lab](https://elevenlabs.io/app/voice-lab)
2. Get voice ID
3. Use with flag:
   ```bash
   cld --audio=elevenlabs --elevenlabs-voice-id=your_voice_id
   ```

### Custom AI Model

Use different AI models for contextual messages:

```bash
cld --ai=full --openrouter-model=google/gemini-2.5-flash-lite  # Faster, cheaper
cld --ai=full --openrouter-model=anthropic/claude-3-haiku      # Better quality
```

### Multi-Instance Support

Run multiple Claude sessions with different configurations simultaneously:

```bash
# Terminal 1: Work project with Indonesian TTS
cld --audio=gtts --language=id

# Terminal 2: Side project with premium voice + AI
cld --audio=elevenlabs --ai=full

# Terminal 3: Meeting mode (silent)
cld --silent

# Terminal 4: Testing with prerecorded only
cld --audio=prerecorded
```

Each session runs independently with its own server and configuration!

## Slash Commands Reference

cc-hooks provides convenient slash commands for management:

### Setup Command

Configure and test your installation:

```bash
/cc-hooks-plugin:setup           # Interactive setup wizard
/cc-hooks-plugin:setup check     # Check system requirements
/cc-hooks-plugin:setup apikeys   # Configure API keys
/cc-hooks-plugin:setup test      # Test installation
```

### Update Command

Keep cc-hooks up to date:

```bash
/cc-hooks-plugin:update          # Check and install updates
```

## Migrating from Standalone

If you previously used standalone installation, see [MIGRATION.md](MIGRATION.md) for a comprehensive
migration guide.

**Quick summary:**

1. Remove hooks from `~/.claude/settings.json`
2. Install plugin via `claude plugin install cc-hooks@cc-hooks-plugin`
3. Update shell alias to point to plugin path
4. Export API keys to shell environment (if using)
5. Test with `/cc-hooks-plugin:setup check`

Your data in `~/.claude/.cc-hooks/` is automatically preserved!

## Support

- **Issues**: [GitHub Issues](https://github.com/husniadil/cc-hooks/issues)
- **Documentation**: [Main README](README.md) (this file) | [Standalone](STANDALONE_README.md) |
  [Migration](MIGRATION.md)
- **Development**: [CLAUDE.md](CLAUDE.md) for technical details
- **Updates**: Use `/cc-hooks-plugin:update` inside Claude REPL

## Credits

- **Sound effects**: Generated using [ElevenLabs](https://elevenlabs.io) voice synthesis
- **TTS**: [Google TTS](https://github.com/pndurette/gTTS), [ElevenLabs](https://elevenlabs.io)
- **AI**: [OpenRouter](https://openrouter.ai)

## License

MIT - see [LICENSE](LICENSE) for details.

---

**Made with ❤️ for the Claude Code community**

Enjoy your enhanced coding experience! 🎉
