# Migration Guide: Standalone → Plugin Mode

This guide helps you migrate from **standalone installation** to **plugin mode** for easier updates
and maintenance.

## Why Migrate to Plugin Mode?

| Feature               | Plugin Mode ⭐           | Standalone Mode            |
| --------------------- | ------------------------ | -------------------------- |
| **Setup**             | 3 commands, automatic    | Manual hooks configuration |
| **Updates**           | One command              | Git pull + manual restart  |
| **Slash Commands**    | Built-in (`/cc-hooks-*`) | Not available              |
| **Hook Config**       | Automatic via hooks.json | Manual in settings.json    |
| **Installation Path** | Fixed location           | User-defined (flexible)    |
| **For Development**   | Limited (read-only)      | Full access to source      |

**Recommendation**: Most users should use plugin mode. Keep standalone mode for development or
contributing.

## Before You Start

### Pre-Migration Checklist

- [ ] **Close all Claude Code sessions** - No active cc-hooks processes
- [ ] **Backup your settings** - Copy `~/.claude/settings.json` to a safe location
- [ ] **Note your current setup**:
  - [ ] Installation path (output of `pwd` in cc-hooks directory)
  - [ ] API keys (check `.env` file or environment variables)
  - [ ] Custom modifications (if any)
  - [ ] Current alias in your shell config (`.bashrc`, `.zshrc`, etc.)

### What Gets Preserved?

✅ **Automatically preserved** (shared data directory):

- Event database (`~/.claude/.cc-hooks/events.db`)
- TTS cache (`~/.claude/.cc-hooks/.tts_cache/`)
- Session logs (`~/.claude/.cc-hooks/logs/`)
- **Config file** (`~/.claude/.cc-hooks/config.yaml`) - if you created one

⚠️ **Needs manual migration**:

- API keys (if using `.env` → recommended: create config file or export to shell environment)
- Shell alias (needs path update)
- Status line configuration (needs path update)
- Custom sound files (if modified)

## Step-by-Step Migration

### Step 1: Export API Keys

If you're using API keys, export them to your shell environment:

```bash
# Check if you have API keys in .env file
cd /path/to/your/standalone/cc-hooks
cat .env

# If you see ELEVENLABS_API_KEY or OPENROUTER_API_KEY, copy them
# Then add to your shell config (~/.bashrc or ~/.zshrc):
export ELEVENLABS_API_KEY="your_key_here"
export OPENROUTER_API_KEY="your_key_here"

# Apply changes
source ~/.bashrc  # or source ~/.zshrc
```

**Alternative: Use Config File (Recommended)**

Instead of exporting API keys to shell environment, you can create a config file that works across
both modes:

```bash
# Create config file (use the example generator)
cd ~/.claude/plugins/marketplaces/cc-hooks-plugin
uv run utils/config_loader.py --create-example

# Then edit ~/.claude/.cc-hooks/config.yaml with your preferences
```

**Example config**:

```yaml
# ~/.claude/.cc-hooks/config.yaml
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

**Note**: Add API keys themselves to shell environment (not in config file):

```bash
# In ~/.bashrc or ~/.zshrc
export ELEVENLABS_API_KEY="your_key_here"
export OPENROUTER_API_KEY="your_key_here"
```

**Benefits of config file**:

- Works in both terminal and editors (Zed, VSCode, etc.)
- No need to type CLI flags every session
- Automatically preserved during migration (shared data directory)
- Can still override with CLI flags when needed

### Step 2: Remove Standalone Hooks

Edit `~/.claude/settings.json` and **remove** all cc-hooks hook entries:

**Before:**

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
            "command": "uv run /path/to/cc-hooks/hooks.py"
          }
        ]
      }
    ],
    "SessionEnd": [...],
    // ... other hooks
  }
}
```

**After:**

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "model": "sonnet"
}
```

**Note**: Remove the entire `hooks` object, or if you have other custom hooks, only remove the
cc-hooks entries.

### Step 3: Install Plugin

```bash
# Add cc-hooks marketplace
claude plugin marketplace add https://github.com/husniadil/cc-hooks.git

# Install cc-hooks plugin
claude plugin install cc-hooks@cc-hooks-plugin

# Verify installation
claude plugin list
```

You should see `cc-hooks@cc-hooks-plugin` in the list.

### Step 4: Update Shell Alias

Update your shell configuration (`~/.bashrc`, `.zshrc`, etc.):

**Before:**

```bash
alias cld='/path/to/your/standalone/cc-hooks/claude.sh'
```

**After:**

```bash
alias cld='~/.claude/plugins/marketplaces/cc-hooks-plugin/claude.sh'
```

Apply changes:

```bash
source ~/.bashrc  # or source ~/.zshrc
```

### Step 5: Update Status Line (If Configured)

If you configured status line in `~/.claude/settings.json`, update the path:

**Before:**

```json
{
  "statusLine": {
    "type": "command",
    "command": "uv run /path/to/standalone/cc-hooks/status-lines/status_line.py"
  }
}
```

**After:**

```json
{
  "statusLine": {
    "type": "command",
    "command": "uv run ~/.claude/plugins/marketplaces/cc-hooks-plugin/status-lines/status_line.py"
  }
}
```

### Step 6: Test Installation

Run the setup wizard to verify everything works:

```bash
# Start Claude Code
cld

# Inside Claude REPL, run setup check
/cc-hooks-plugin:setup check
```

The wizard will verify:

- ✅ uv installation
- ✅ Plugin installation
- ✅ API keys (if configured)
- ✅ Audio system

### Step 7: Test Audio Feedback

Start a simple session to test audio:

```bash
# Test with default (prerecorded) sounds
cld

# Ask Claude a simple question - you should hear:
# - Sound effect when Claude uses tools
# - Voice announcement when session ends
```

If you configured API keys, test premium features:

```bash
# Test Google TTS
cld --audio=gtts --language=en

# Test ElevenLabs (if API key configured)
cld --audio=elevenlabs

# Test AI features (if OpenRouter key configured)
cld --ai=basic
```

### Step 8: Optional Cleanup

Once you've verified everything works, you can optionally remove the standalone installation:

```bash
# Remove the standalone directory
rm -rf /path/to/your/standalone/cc-hooks

# Remove old alias entry from shell config (already updated in Step 4)
# Remove old statusLine entry from settings.json (already updated in Step 5)
```

**⚠️ Warning**: Don't delete `~/.claude/.cc-hooks/` - this is the shared data directory used by both
modes!

## Verification

After migration, verify your setup:

```bash
# 1. Check plugin is installed
claude plugin list | grep cc-hooks

# 2. Check hooks are NOT in settings.json
grep -A 5 "hooks.py" ~/.claude/settings.json  # Should return nothing

# 3. Check alias points to plugin
type cld  # Should show plugin path

# 4. Check API keys (if configured)
printenv | grep -E "(ELEVENLABS|OPENROUTER)"

# 5. Test audio
cld
```

## Troubleshooting

### "No audio after migration"

1. Verify plugin installation: `claude plugin list`
2. Check uv is installed: `uv --version`
3. Test audio directly:
   `uv run ~/.claude/plugins/marketplaces/cc-hooks-plugin/utils/sound_player.py`
4. Check logs: `tail -f ~/.claude/.cc-hooks/logs/*.log`

### "API keys not working"

1. Verify keys are in shell environment: `printenv | grep -E "(ELEVENLABS|OPENROUTER)"`
2. Make sure you sourced your shell config: `source ~/.bashrc` or `source ~/.zshrc`
3. Restart Claude Code after exporting keys

### "Slash commands not available"

1. Make sure plugin is installed: `claude plugin list`
2. Try reinstalling:
   `claude plugin uninstall cc-hooks@cc-hooks-plugin && claude plugin install cc-hooks@cc-hooks-plugin`
3. Restart Claude Code

### "Hooks still running from old standalone installation"

1. Check settings.json doesn't have old hooks: `cat ~/.claude/settings.json | grep hooks.py`
2. Kill any orphaned processes: `pkill -f "uv run.*hooks.py"`
3. Restart Claude Code

## Rollback to Standalone

If you need to rollback:

1. **Uninstall plugin**:

   ```bash
   claude plugin uninstall cc-hooks@cc-hooks-plugin
   ```

2. **Restore hooks** in `~/.claude/settings.json` (from your backup)

3. **Restore shell alias** to point to standalone installation

4. **Restart Claude Code**

Your data in `~/.claude/.cc-hooks/` remains intact throughout.

## Edge Cases

### Custom Sound Files

If you modified files in the standalone `/sound` directory:

1. Copy custom sounds from standalone to plugin:
   ```bash
   cp /path/to/standalone/cc-hooks/sound/*.mp3 \
      ~/.claude/plugins/marketplaces/cc-hooks-plugin/sound/
   ```

### Custom Code Modifications

If you modified cc-hooks source code:

**Option 1**: Keep standalone mode (recommended for contributors)

- Don't migrate, stay on standalone
- See [STANDALONE_README.md](STANDALONE_README.md)

**Option 2**: Port changes to plugin

- Apply same modifications to `~/.claude/plugins/marketplaces/cc-hooks-plugin/`
- Note: Updates will overwrite your changes

**Option 3**: Contribute upstream

- Submit PR to main repository
- Benefit everyone!

### Multiple Installations

You can run both modes simultaneously (not recommended):

- Different projects can use different modes
- Use different aliases: `cld-plugin` vs `cld-standalone`
- Both share same data directory (`~/.claude/.cc-hooks/`)

## Need Help?

- **Issues**: [GitHub Issues](https://github.com/husniadil/cc-hooks/issues)
- **Documentation**: [README.md](README.md) (plugin mode) |
  [STANDALONE_README.md](STANDALONE_README.md) (standalone mode)
- **Updates**: Use `/cc-hooks-plugin:update` inside Claude REPL

---

**Migration complete!** Enjoy easier updates with plugin mode. 🎉
