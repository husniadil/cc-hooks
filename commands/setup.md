---
allowed-tools: Read, Bash, Edit, Write
description: Setup and configure cc-hooks plugin
argument-hint: [check|apikeys|test]
---

# cc-hooks Setup Assistant

Help the user set up and configure the cc-hooks plugin. Follow these steps:

## 1. System Requirements Check

Check if `uv` is installed:

```bash
uv --version
```

If not installed, guide the user to install it:

- **macOS/Linux**: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Windows**: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`

## 2. Shell Alias Setup

### 2.1. Check `cld` Alias Availability

Check if `cld` command is available using BOTH methods:

```bash
# Detect user's shell
echo $SHELL

# Method 1: Test if cld works in current shell
type cld 2>/dev/null && echo "cld: available in current shell" || echo "cld: not found in current shell"

# Method 2: Check if cld is configured in shell config files
grep -h "alias cld=" ~/.zshrc ~/.bashrc ~/.bash_profile ~/.profile 2>/dev/null && echo "cld: found in shell config" || echo "cld: not found in shell config"
```

**Decision logic:**

- If **EITHER** method finds `cld` → Skip to checking wrapper alias (Section 2.2)
- If **BOTH** methods fail → Offer to create `cld` alias

### Creating `cld` Alias (only if not found)

If `cld` is not available in either current shell or config files, guide the user to add it:

**For zsh users** (~/.zshrc):

```bash
alias cld='~/.claude/plugins/marketplaces/cc-hooks-plugin/claude.sh'
```

**For bash users** (~/.bashrc or ~/.bash_profile):

```bash
alias cld='~/.claude/plugins/marketplaces/cc-hooks-plugin/claude.sh'
```

Ask the user if they would like to add the `cld` alias to their shell configuration for convenience.

If the user agrees, add the appropriate alias to their shell config file and remind them to run
`source ~/.zshrc` (or appropriate config file) or restart their terminal.

### 2.2. Check for Wrapper Alias (Optional)

After confirming `cld` is available (either in current shell or config files), check if a wrapper
alias already exists:

```bash
# Check for any alias that wraps cld with arguments
grep -h "alias.*='cld " ~/.zshrc ~/.bashrc ~/.bash_profile ~/.profile 2>/dev/null | grep -v "^#"
```

**If wrapper alias exists:**

- Show the user what's configured (e.g., "Found wrapper alias: cc='cld --audio=gtts --ai=full'")
- Skip to step 3

**If no wrapper exists:**

Inform the user that they can optionally create a convenient wrapper alias with their preferred
default settings. Present the available preset configurations:

**Preset configurations:**

1. **Basic**: `alias cc='cld'` - Prerecorded audio only
2. **Enhanced**: `alias cc='cld --audio=gtts --ai=basic'` - Google TTS with AI (requires OpenRouter)
3. **Full**: `alias cc='cld --audio=gtts --ai=full'` - Google TTS with all AI features (requires
   OpenRouter)
4. **Premium**: `alias cc='cld --audio=elevenlabs --ai=full'` - ElevenLabs with AI (requires both
   API keys)
5. **Silent**: `alias cc='cld --silent'` - No audio, visual only
6. **Skip**: Continue without creating a wrapper alias

**Implementation:**

- If the user wants a preset, ask which one they prefer
- Optionally offer to customize with language flag (e.g., `--language=id`)
- Add the chosen alias to their shell config file
- Remind them to run `source ~/.zshrc` (or appropriate config file) or restart their terminal
- Explain that they can still use `cld` with different flags when needed

**Example:**

```bash
# Enhanced preset with Indonesian language
alias cc='cld --audio=gtts --ai=basic --language=id'
```

## 3. Status Line Configuration Check

Check if statusline is configured properly in `~/.claude/settings.json`:

```bash
# Read the settings file
cat ~/.claude/settings.json | grep -A 2 '"statusLine"'
```

**Expected configuration**:

```json
"statusLine": {
  "type": "command",
  "command": "uv run ~/.claude/plugins/marketplaces/cc-hooks-plugin/status-lines/status_line.py"
}
```

**If not configured or pointing to wrong path**, offer to update it automatically or guide the user
to add/update the statusLine configuration.

## 4. Environment Variables Check

**IMPORTANT**: Plugin updates will delete and redownload all plugin files. Therefore, API keys and
environment variables MUST be stored outside the plugin directory (e.g., in shell config files like
`~/.zshrc` or `~/.bashrc`, or in separate files loaded by your shell).

### Check if API Keys are Available

First, check if API keys are available in the current environment:

```bash
# Check for API keys in current environment (DO NOT print values)
env | grep -E "OPENROUTER_API_KEY|ELEVENLABS_API_KEY" | sed 's/=.*/=[SET]/' || echo "No API keys found"
```

**If API keys ARE available** (regardless of how they're loaded):

- ✅ Confirm that API keys are set and ready to use
- Skip offering to add them (user has their own setup)
- Continue to next step

**If API keys ARE NOT available**, check shell config files:

```bash
# Check for API keys in shell config (DO NOT print values)
grep -h "OPENROUTER_API_KEY\|ELEVENLABS_API_KEY" ~/.zshrc ~/.bashrc ~/.bash_profile ~/.profile 2>/dev/null | sed 's/=.*/=[REDACTED]/' || echo "No API keys found in shell config"
```

### API Keys to Configure

**OpenRouter** (for AI contextual messages):

- `OPENROUTER_API_KEY`: Get from https://openrouter.ai/keys
- Required only if using `--ai=basic` or `--ai=full`
- **If provided**: Recommend starting with `cld --audio=gtts --ai=full` (or `--ai=basic`)

**ElevenLabs** (for premium TTS):

- `ELEVENLABS_API_KEY`: Get from https://elevenlabs.io/
- Required only if using `--audio=elevenlabs`

### Configuring Environment Variables

**Only offer this if API keys are NOT available in the current environment.**

Guide the user to add them to their shell config:

**For zsh users** (~/.zshrc):

```bash
# cc-hooks API Keys
export OPENROUTER_API_KEY="your-key-here"
export ELEVENLABS_API_KEY="your-key-here"
```

**For bash users** (~/.bashrc or ~/.bash_profile):

```bash
# cc-hooks API Keys
export OPENROUTER_API_KEY="your-key-here"
export ELEVENLABS_API_KEY="your-key-here"
```

**After adding:**

- Remind them to run `source ~/.zshrc` (or appropriate config file) or restart their terminal
- Explain that only the keys they need should be added (OpenRouter for AI, ElevenLabs for premium
  TTS)
- Note that they can also load keys from separate files (e.g., `source ~/.api-keys` in their shell
  config)

**SECURITY NOTE**: Never print actual API key values in output. Always redact or mask them.

## 5. Configuration File Setup (Recommended)

**This step is OPTIONAL but highly recommended** - it provides a better experience for all users.

### Why Use a Config File?

The config file (`~/.claude/.cc-hooks/config.yaml`) lets you set default preferences without using
CLI flags:

**Benefits for Zed/Editor users:**

- ✅ **Editors can't pass CLI flags** → Config file enables customization
- ✅ Set audio provider, language, AI features → Works automatically in Zed

**Benefits for Terminal users:**

- ✅ No need to type flags every time → Just run `cld` or `claude`
- ✅ Set your preferred defaults → Consistent experience
- ✅ Can still override with CLI flags when needed

### Check if Config Exists

```bash
# Check if config file already exists
ls -la ~/.claude/.cc-hooks/config.yaml
```

**If config exists:**

- Show the user their current settings
- Ask if they want to modify it
- Skip to next section if they're happy

**If config doesn't exist:**

- Offer to create one with their preferences

### Creating Config File

If the user wants to create a config file:

**Option 1: Create with default example (Recommended)**

```bash
# Create example config with all options documented
uv run ~/.claude/plugins/marketplaces/cc-hooks-plugin/utils/config_loader.py --create-example

# Show the created file
cat ~/.claude/.cc-hooks/config.yaml
```

**Option 2: Interactive configuration**

Ask the user for their preferences:

1. **Audio provider**: prerecorded (default), gtts (free), or elevenlabs (premium)
2. **Language**: en (default), id, es, fr, etc.
3. **AI features**: disabled (default), basic, or full
4. **Silent modes**: none (default), announcements, or sound-effects

Then create a customized config file based on their answers.

**Example for Indonesian user with Google TTS:**

```yaml
audio:
  providers: gtts,prerecorded
  language: id
  cache_enabled: true

openrouter:
  enabled: false
```

**Example for premium setup (requires API keys):**

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
  contextual_pretooluse: false
```

### Explain Priority System

After creating the config, explain to the user:

**Configuration Priority** (highest to lowest):

1. **CLI flags** → `cld --language=es` (terminal usage, session override)
2. **Environment variables** → `export CC_TTS_LANGUAGE=es` (temporary override)
3. **Config file** → `~/.claude/.cc-hooks/config.yaml` (your defaults) ← **NEW!**
4. **Hardcoded defaults** → Built-in fallback values

**This means:**

- Config file provides your defaults for all sessions
- Terminal users can override with `cld --flag` when needed
- Zed/editor users get config defaults automatically
- Everyone benefits from "set once, forget" workflow

### Verify Config Works

```bash
# Test that config is loaded (check with a simple session)
cld

# Or test config loading directly
cd ~/.claude/plugins/marketplaces/cc-hooks-plugin
uv run utils/config_loader.py
```

## 6. Configuration Options (CLI Flags)

Users can configure cc-hooks using **command-line arguments** which override config file and
environment variables:

### Audio Control

```bash
cld --audio=gtts                    # Google TTS (free, internet required)
cld --audio=elevenlabs              # Premium TTS (requires API key)
cld --audio=prerecorded             # Built-in audio files (default)
cld --language=id                   # Language (id, es, en, etc.)
cld --silent                        # Disable all audio
cld --silent=announcements          # Keep sound effects, disable TTS
cld --silent=sound-effects          # Keep TTS, disable sound effects
```

### AI Features (requires OpenRouter API key)

```bash
cld --ai=basic                      # Contextual Stop messages only
cld --ai=full                       # All contextual messages (Stop + PreToolUse)
```

### Combined Examples

```bash
cld --audio=gtts --language=id --ai=full
cld --audio=elevenlabs --ai=basic
cld --silent=announcements
```

**Note**: CLI arguments override config file and environment variables for that session only.

## 7. Test Setup

If the user requests testing, run these verification checks:

### Basic Audio Test

```bash
cd ~/.claude/plugins/marketplaces/cc-hooks-plugin
uv run utils/sound_player.py --list
uv run utils/sound_player.py sound_effect_cetek.mp3
```

### TTS Test

```bash
cd ~/.claude/plugins/marketplaces/cc-hooks-plugin
uv run utils/tts_announcer.py --list
uv run utils/tts_announcer.py SessionStart
```

### Server Test

Check if server can start:

```bash
cd ~/.claude/plugins/marketplaces/cc-hooks-plugin
timeout 5 uv run server.py --port 12299 || echo "Server test completed"
```

## 8. Usage Examples

Show the user how to start Claude with different configurations:

**With config file (Recommended for most users):**

```bash
# Just run claude directly - uses your config file settings
claude

# Or if you set up the cld alias
cld
```

**With CLI flags (Power users - per-session overrides):**

**If default alias was created (e.g., `cc`):**

```bash
# Use your default configuration
cc

# Override with different settings
cld --audio=gtts --language=id
cld --silent
```

**Using `cld` directly with various configurations:**

```bash
# Basic usage with prerecorded audio (default)
cld

# Google TTS in Indonesian
cld --audio=gtts --language=id

# ElevenLabs TTS with AI features
cld --audio=elevenlabs --ai=full

# Silent mode (no audio)
cld --silent

# Silent announcements only (keep sound effects)
cld --silent=announcements
```

## 9. Troubleshooting

Common issues and solutions:

### Audio Not Playing

- Check system volume
- Test with: `uv run utils/sound_player.py`
- Check if pygame is installed: `uv pip list | grep pygame`

### Server Won't Start

- Check if port is in use: `lsof -i :12222`
- Check logs: `tail -f ~/.claude/.cc-hooks/logs/*.log`
- Try different port: `CC_HOOKS_PORT=12223 ./claude.sh`

### TTS Not Working

- Check if API keys are set in shell config (redacted):
  `env | grep -E "OPENROUTER_API_KEY|ELEVENLABS_API_KEY" | sed 's/=.*/=[SET]/' || echo "No API keys found"`
- Test provider directly: `uv run utils/tts_announcer.py --provider gtts SessionStart`
- Check internet connection (required for gtts and elevenlabs)
- Verify shell config was sourced: restart terminal or run `source ~/.zshrc`

### Setup Cannot Complete or Bug Found

If you encounter issues that prevent setup from completing, or you've found a bug:

**Report the issue on GitHub:** https://github.com/husniadil/cc-hooks/issues/new

**Include in your report:**

- What step failed (e.g., "Step 2: Shell Alias Setup")
- Error message or unexpected behavior
- Your OS and shell (from `echo $SHELL`)
- Relevant logs from `~/.claude/.cc-hooks/logs/`

## Argument Handling

If the user provides an argument:

- **check**: Run system requirements and configuration check only
- **apikeys**: Focus on API key setup and validation
- **test**: Run all test suites to verify installation

If no argument provided, run the full interactive setup wizard.

## Important Notes

- **CRITICAL**: Never print or expose API key values in any output - always redact them
- Do NOT create or modify `.env` files in the plugin directory (they will be deleted on updates)
- API keys MUST be stored in shell config files (~/.zshrc, ~/.bashrc, etc.)
- Always confirm before writing/modifying files
- Direct the user to documentation for advanced configuration: https://github.com/husniadil/cc-hooks
- **If setup fails or you encounter a bug**: Guide the user to report the issue at
  https://github.com/husniadil/cc-hooks/issues/new
