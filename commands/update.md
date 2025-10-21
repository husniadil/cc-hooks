---
allowed-tools: Bash
description: Check for cc-hooks updates and install if available
---

# cc-hooks Update Assistant

Check for cc-hooks updates and install them if available.

## Update Check Flow

### 1. Detect Installation Mode

Determine if cc-hooks is running in plugin mode or standalone mode by checking the hooks
configuration:

```bash
# Detect installation mode
python3 -c "
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
"
```

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

- In plugin mode, hooks are NOT in `~/.claude/settings.json`
- In plugin mode, hooks are in `~/.claude/plugins/marketplaces/cc-hooks-plugin/hooks/hooks.json`
- Must check plugin directory first before checking settings.json

**Example configurations**:

**Plugin mode**: `~/.claude/plugins/marketplaces/cc-hooks-plugin/hooks/hooks.json`

```json
{
  "hooks": {
    "SessionStart": [
      {
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

### 2. Check for Updates

Query the cc-hooks server for version status:

```bash
# Try to get version status from the server
curl -s http://localhost:12222/version/status 2>/dev/null || \
curl -s http://localhost:12223/version/status 2>/dev/null || \
curl -s http://localhost:12224/version/status 2>/dev/null || \
echo '{"error": "Server not running"}'
```

**Important**: Try multiple ports (12222, 12223, 12224) as the server may be running on different
ports for different instances.

### 3. Parse Version Information

From the API response, extract:

- `update_available` (boolean)
- `current_version` (string)
- `latest_version` (string)
- `commits_behind` (number)

### 4. Display Status

**If server is not running or error:**

```
❌ Cannot check for updates: cc-hooks server is not running
💡 Start Claude Code with cc-hooks to check for updates
```

**If no update available:**

```
✅ cc-hooks is up to date
📌 Current version: {current_version}
```

**If update available:**

```
⚠️  Update available for cc-hooks

Current version: {current_version}
Latest version:  {latest_version}
Commits behind:  {commits_behind}

Would you like to update now?
```

### 5. Offer to Update

If update is available, ask the user if they would like to proceed with the update now.

- If the user confirms → Proceed with update
- If the user declines → Skip update and show them how to update manually later

### 6. Execute Update

**For Plugin Mode:**

```bash
claude plugin marketplace update cc-hooks-plugin
```

**For Standalone Mode:**

```bash
cd {repo_root} && npm run update
```

**After update:**

```
✅ cc-hooks has been updated to {latest_version}
⚠️  Please restart your Claude Code session for changes to take effect
```

## Error Handling

**If update command fails:**

```
❌ Update failed. Please try manually:

Plugin mode:
  claude plugin marketplace update cc-hooks-plugin

Standalone mode:
  cd {repo_root}
  npm run update
```

**If the update continues to fail or you encounter a bug:**

Direct the user to report the issue on GitHub: https://github.com/husniadil/cc-hooks/issues/new

**Include in the report:**

- Current version (from error message or `/version/status` endpoint)
- Installation mode (plugin or standalone)
- Full error message
- OS and shell information
- Steps attempted before failure

## Example Session

```
$ /cc-hooks-plugin:update

Checking for cc-hooks updates...

⚠️  Update available for cc-hooks

Current version: v1.0.0
Latest version:  v1.0.1
Commits behind:  3

Would you like to update now? [Yes/No]
> Yes

Updating cc-hooks...
✅ cc-hooks has been updated to v1.0.1
⚠️  Please restart your Claude Code session for changes to take effect
```

## Implementation Notes

- Always check server availability first
- Try multiple ports (race condition during server startup)
- Detect installation mode from current working directory
- Use appropriate update command based on mode
- Always remind user to restart Claude Code after update
- Handle connection errors gracefully
- **If update fails or bugs are found**: Direct users to
  https://github.com/husniadil/cc-hooks/issues/new
