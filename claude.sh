#!/bin/bash
# Claude Code Wrapper - Pure Proxy
# SessionStart/SessionEnd hooks handle all server lifecycle and settings management

# Parse cc-hooks specific arguments and set environment variables
CC_TTS_LANGUAGE=""
CC_ELEVENLABS_VOICE_ID=""
CC_ELEVENLABS_MODEL_ID=""
CC_TTS_PROVIDERS=""
CC_TTS_CACHE_ENABLED=""
CC_SILENT_ANNOUNCEMENTS=""
CC_SILENT_EFFECTS=""
CC_OPENROUTER_ENABLED=""
CC_OPENROUTER_MODEL=""
CC_OPENROUTER_CONTEXTUAL_STOP=""
CC_OPENROUTER_CONTEXTUAL_PRETOOLUSE=""
CLAUDE_ARGS=()

for arg in "$@"; do
    case $arg in
        --language=*)
            CC_TTS_LANGUAGE="${arg#*=}"
            ;;
        --elevenlabs-voice-id=*)
            CC_ELEVENLABS_VOICE_ID="${arg#*=}"
            ;;
        --elevenlabs-model=*)
            CC_ELEVENLABS_MODEL_ID="${arg#*=}"
            ;;
        --tts-providers=*)
            CC_TTS_PROVIDERS="${arg#*=}"
            ;;
        --audio=*)
            AUDIO_MODE="${arg#*=}"
            case "$AUDIO_MODE" in
                prerecorded)
                    CC_TTS_PROVIDERS="prerecorded"
                    ;;
                gtts)
                    CC_TTS_PROVIDERS="gtts,prerecorded"
                    ;;
                elevenlabs)
                    CC_TTS_PROVIDERS="elevenlabs,gtts,prerecorded"
                    ;;
                *)
                    echo "Warning: Unknown --audio value '$AUDIO_MODE'. Valid values: prerecorded, gtts, elevenlabs" >&2
                    ;;
            esac
            ;;
        --ai=*)
            AI_MODE="${arg#*=}"
            CC_OPENROUTER_ENABLED="true"
            case "$AI_MODE" in
                basic)
                    CC_OPENROUTER_CONTEXTUAL_STOP="true"
                    CC_OPENROUTER_CONTEXTUAL_PRETOOLUSE="false"
                    ;;
                full)
                    CC_OPENROUTER_CONTEXTUAL_STOP="true"
                    CC_OPENROUTER_CONTEXTUAL_PRETOOLUSE="true"
                    ;;
                *)
                    echo "Warning: Unknown --ai value '$AI_MODE'. Valid values: basic, full" >&2
                    ;;
            esac
            ;;
        --openrouter-model=*)
            CC_OPENROUTER_MODEL="${arg#*=}"
            ;;
        --no-cache)
            CC_TTS_CACHE_ENABLED="false"
            ;;
        --silent=*)
            SILENT_MODE="${arg#*=}"
            case "$SILENT_MODE" in
                announcements)
                    CC_SILENT_ANNOUNCEMENTS="true"
                    ;;
                sound-effects)
                    CC_SILENT_EFFECTS="true"
                    ;;
                all)
                    CC_SILENT_ANNOUNCEMENTS="true"
                    CC_SILENT_EFFECTS="true"
                    ;;
                *)
                    echo "Warning: Unknown --silent value '$SILENT_MODE'. Valid values: announcements, sound-effects, all" >&2
                    ;;
            esac
            ;;
        --silent)
            # Default to 'all' when no value provided
            CC_SILENT_ANNOUNCEMENTS="true"
            CC_SILENT_EFFECTS="true"
            ;;
        *)
            CLAUDE_ARGS+=("$arg")
            ;;
    esac
done

# Export cc-hooks configuration for SessionStart hook to read
# Config is passed via environment to hooks.py which stores in sessions table
if [ -n "$CC_TTS_LANGUAGE" ]; then
    export CC_TTS_LANGUAGE
fi

if [ -n "$CC_ELEVENLABS_VOICE_ID" ]; then
    export CC_ELEVENLABS_VOICE_ID
fi

if [ -n "$CC_ELEVENLABS_MODEL_ID" ]; then
    export CC_ELEVENLABS_MODEL_ID
fi

if [ -n "$CC_TTS_PROVIDERS" ]; then
    export CC_TTS_PROVIDERS
fi

if [ -n "$CC_TTS_CACHE_ENABLED" ]; then
    export CC_TTS_CACHE_ENABLED
fi

if [ -n "$CC_SILENT_ANNOUNCEMENTS" ]; then
    export CC_SILENT_ANNOUNCEMENTS
fi

if [ -n "$CC_SILENT_EFFECTS" ]; then
    export CC_SILENT_EFFECTS
fi

if [ -n "$CC_OPENROUTER_ENABLED" ]; then
    export CC_OPENROUTER_ENABLED
fi

if [ -n "$CC_OPENROUTER_MODEL" ]; then
    export CC_OPENROUTER_MODEL
fi

if [ -n "$CC_OPENROUTER_CONTEXTUAL_STOP" ]; then
    export CC_OPENROUTER_CONTEXTUAL_STOP
fi

if [ -n "$CC_OPENROUTER_CONTEXTUAL_PRETOOLUSE" ]; then
    export CC_OPENROUTER_CONTEXTUAL_PRETOOLUSE
fi

# If original directory was passed, change to it before starting Claude
# This is NOT config - it's operational (where claude should run from)
if [ -n "$CC_ORIGINAL_DIR" ] && [ -d "$CC_ORIGINAL_DIR" ]; then
    cd "$CC_ORIGINAL_DIR"
fi

# Find Claude CLI executable
# Priority: CLAUDE_BIN env var > resolve via user's shell > command in PATH
if [ -n "$CLAUDE_BIN" ] && [ -x "$CLAUDE_BIN" ]; then
    CLAUDE_CMD="$CLAUDE_BIN"
elif [ -n "$SHELL" ]; then
    # Use user's shell to resolve claude (handles aliases and PATH)
    case "$SHELL" in
        */zsh)
            # Use 'which' to resolve aliases in zsh
            WHICH_OUTPUT=$(zsh -i -c 'which claude' 2>/dev/null)
            if echo "$WHICH_OUTPUT" | grep -q "aliased to"; then
                # Format: "claude: aliased to ~/.claude/local/claude"
                CLAUDE_CMD=$(echo "$WHICH_OUTPUT" | sed 's/.*aliased to //')
                CLAUDE_CMD="${CLAUDE_CMD/#\~/$HOME}"
            else
                CLAUDE_CMD="$WHICH_OUTPUT"
            fi
            ;;
        */bash)
            # Use 'type' to resolve aliases in bash
            TYPE_OUTPUT=$(bash -i -c 'type claude' 2>/dev/null)
            if echo "$TYPE_OUTPUT" | grep -q "is aliased to"; then
                # Format: "claude is aliased to `~/.claude/local/claude'"
                CLAUDE_CMD=$(echo "$TYPE_OUTPUT" | sed "s/.*is aliased to \`\(.*\)'/\1/")
                CLAUDE_CMD="${CLAUDE_CMD/#\~/$HOME}"
            else
                CLAUDE_CMD=$(bash -i -c 'command -v claude' 2>/dev/null)
            fi
            ;;
        */fish)
            # Fish uses 'type' with different output format
            TYPE_OUTPUT=$(fish -i -c 'type -P claude' 2>/dev/null)
            if [ -n "$TYPE_OUTPUT" ]; then
                CLAUDE_CMD="$TYPE_OUTPUT"
            else
                # Fallback: check if it's an alias and parse it
                ALIAS_OUTPUT=$(fish -i -c 'alias claude' 2>/dev/null)
                if [ -n "$ALIAS_OUTPUT" ]; then
                    CLAUDE_CMD=$(echo "$ALIAS_OUTPUT" | sed "s/.*alias claude //")
                    CLAUDE_CMD="${CLAUDE_CMD/#\~/$HOME}"
                fi
            fi
            ;;
        *)
            CLAUDE_CMD=$(command -v claude 2>/dev/null)
            ;;
    esac
else
    CLAUDE_CMD=$(command -v claude 2>/dev/null)
fi

# Validate claude executable was found
if [ -z "$CLAUDE_CMD" ] || [ ! -x "$CLAUDE_CMD" ]; then
    echo "Error: Claude CLI not found." >&2
    echo "Please either:" >&2
    echo "  1. Ensure 'claude' is in your PATH or aliased in your shell config, or" >&2
    echo "  2. Set CLAUDE_BIN environment variable: export CLAUDE_BIN=/path/to/claude" >&2
    exit 1
fi

# Pure proxy - exec replaces this shell process with Claude
exec "$CLAUDE_CMD" "${CLAUDE_ARGS[@]}"
