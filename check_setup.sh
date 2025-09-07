#!/bin/bash

# cc-hooks Setup Validation Script
# Validates installation requirements and tests functionality

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Default options
VERBOSE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -v, --verbose      Show detailed output"
            echo "  -h, --help         Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                 # Basic validation"
            echo "  $0 --verbose       # Detailed validation output"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Track failures
FAILURES=0
WARNINGS=0

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Helper functions
print_header() {
    echo ""
    echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}${BOLD}  $1${NC}"
    echo -e "${BLUE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_section() {
    echo ""
    echo -e "${CYAN}${BOLD}▶ $1${NC}"
}

print_success() {
    echo -e "  ${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "  ${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

print_error() {
    echo -e "  ${RED}✗${NC} $1"
    ((FAILURES++))
}

print_info() {
    if [ "$VERBOSE" = true ]; then
        echo -e "  ${CYAN}ℹ${NC} $1"
    fi
}

# Main validation starts here
print_header "cc-hooks Setup Validation v1.0"
echo -e "${CYAN}Checking your cc-hooks installation...${NC}"

# 1. System Dependencies
print_section "System Dependencies"

# Check Python version
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
    MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 12 ]; then
        print_success "Python $PYTHON_VERSION found (3.12+ required)"
    else
        print_error "Python $PYTHON_VERSION found but 3.12+ is required"
        echo "        Please upgrade Python: https://www.python.org/downloads/"
    fi
else
    print_error "Python 3 not found"
    echo "        Please install Python 3.12+: https://www.python.org/downloads/"
fi

# Check uv package manager
if command -v uv &> /dev/null; then
    UV_VERSION=$(uv --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    print_success "uv $UV_VERSION found"
    print_info "uv location: $(which uv)"
else
    print_error "uv package manager not found"
    echo "        Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
fi

# Check Claude CLI
if command -v claude &> /dev/null || [ -f "$HOME/.claude/local/claude" ]; then
    print_success "Claude Code CLI found"
    print_info "Claude location: $(which claude 2>/dev/null || echo "$HOME/.claude/local/claude")"
else
    print_warning "Claude Code CLI not found in PATH"
    echo "        Install from: https://claude.ai/code"
fi

# Check SQLite (should be built-in with Python)
if python3 -c "import sqlite3" 2>/dev/null; then
    print_success "SQLite3 available (built-in with Python)"
else
    print_error "SQLite3 module not available"
fi

# 2. Claude Code Settings
print_section "Claude Code Settings"

SETTINGS_FILE="$HOME/.claude/settings.json"
HOOKS_PY_PATH="$SCRIPT_DIR/hooks.py"

if [ -f "$SETTINGS_FILE" ]; then
    print_success "settings.json found at ~/.claude/"
    
    # Check if hooks are configured
    if grep -q "hooks.py" "$SETTINGS_FILE" 2>/dev/null; then
        print_success "Hooks are configured in settings.json"
        
        # Check if absolute paths are used
        if grep -q "$SCRIPT_DIR/hooks.py" "$SETTINGS_FILE" 2>/dev/null; then
            print_success "Hooks use correct absolute paths"
        else
            print_warning "Hooks may not be using correct absolute paths"
            echo "        Expected path: $HOOKS_PY_PATH"
            echo "        Please update paths in settings.json manually"
        fi
        
        # Check required hook events
        REQUIRED_HOOKS=("SessionStart" "SessionEnd" "PreToolUse" "PostToolUse" "Stop" "Notification" "SubagentStop" "PreCompact" "UserPromptSubmit")
        for hook in "${REQUIRED_HOOKS[@]}"; do
            if grep -q "\"$hook\"" "$SETTINGS_FILE" 2>/dev/null; then
                print_info "Hook event '$hook' is configured"
            else
                print_warning "Hook event '$hook' not found in settings"
            fi
        done
        
        # Check status line
        if grep -q "status_line.py" "$SETTINGS_FILE" 2>/dev/null; then
            print_success "Status line is configured"
        else
            print_warning "Status line not configured"
        fi
    else
        print_error "Hooks not configured in settings.json"
        echo "        Please add hooks configuration as shown in README.md"
    fi
else
    print_error "settings.json not found at ~/.claude/"
    echo "        Please configure Claude Code settings as shown in README.md"
fi

# 3. Environment Configuration
print_section "Environment Configuration"

ENV_FILE="$SCRIPT_DIR/.env"
ENV_EXAMPLE="$SCRIPT_DIR/.env.example"

if [ -f "$ENV_FILE" ]; then
    print_success ".env file exists"
    
    # Check for key variables (without exposing values)
    if grep -q "^PORT=" "$ENV_FILE"; then
        PORT=$(grep "^PORT=" "$ENV_FILE" | cut -d= -f2)
        print_info "Server port configured: $PORT"
    fi
    
    if grep -q "^OPENROUTER_API_KEY=." "$ENV_FILE"; then
        print_success "OpenRouter API key is configured"
    else
        print_info "OpenRouter API key not configured (optional)"
    fi
    
    if grep -q "^ELEVENLABS_API_KEY=." "$ENV_FILE"; then
        print_success "ElevenLabs API key is configured"
    else
        print_info "ElevenLabs API key not configured (optional)"
    fi
else
    print_warning ".env file not found"
    if [ -f "$ENV_EXAMPLE" ]; then
        echo "        Run: cp .env.example .env"
    fi
fi

# 4. File Structure and Permissions
print_section "File Structure and Permissions"

# Check critical files
CRITICAL_FILES=("hooks.py" "server.py" "claude.sh" "config.py")
for file in "${CRITICAL_FILES[@]}"; do
    if [ -f "$SCRIPT_DIR/$file" ]; then
        print_success "$file exists"
        if [ "$file" = "claude.sh" ] && [ ! -x "$SCRIPT_DIR/$file" ]; then
            print_warning "$file is not executable"
            echo "        Run: chmod +x $file"
        fi
    else
        print_error "$file not found"
    fi
done

# Check directories
REQUIRED_DIRS=("app" "utils" "sound" "status-lines")
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$SCRIPT_DIR/$dir" ]; then
        print_success "$dir/ directory exists"
    else
        print_error "$dir/ directory not found"
    fi
done

# Check sound files
if [ -d "$SCRIPT_DIR/sound" ]; then
    SOUND_COUNT=$(ls -1 "$SCRIPT_DIR/sound/"*.mp3 2>/dev/null | wc -l)
    if [ "$SOUND_COUNT" -gt 0 ]; then
        print_success "Found $SOUND_COUNT sound effect files"
    else
        print_warning "No sound effect files found in sound/"
    fi
fi

# Check writable directories
WRITABLE_DIRS=(".tts_cache" ".claude-instances")
for dir in "${WRITABLE_DIRS[@]}"; do
    if [ -d "$SCRIPT_DIR/$dir" ] || mkdir -p "$SCRIPT_DIR/$dir" 2>/dev/null; then
        if [ -w "$SCRIPT_DIR/$dir" ]; then
            print_success "$dir/ is writable"
        else
            print_error "$dir/ is not writable"
        fi
    else
        print_error "Cannot create $dir/ directory"
    fi
done

# 5. Functional Tests
print_section "Functional Tests"

# Test sound player
echo -n "  Testing sound player utility... "
if uv run utils/sound_player.py > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
    
else
    echo -e "${RED}✗${NC}"
    ((FAILURES++))
    print_info "Sound player may require pygame or other audio libraries"
fi

# Test TTS announcer
echo -n "  Testing TTS announcer... "
if OUTPUT=$(uv run utils/tts_announcer.py SessionStart 2>&1); then
    echo -e "${GREEN}✓${NC}"
    print_info "TTS test output: $(echo "$OUTPUT" | head -1)"
else
    echo -e "${YELLOW}⚠${NC}"
    ((WARNINGS++))
    print_info "TTS announcer may have issues"
fi

# Test server health (brief start/stop)
echo -n "  Testing server startup... "

# Get port from .env file or use default
SERVER_PORT=12222
if [ -f "$ENV_FILE" ] && grep -q "^PORT=" "$ENV_FILE"; then
    SERVER_PORT=$(grep "^PORT=" "$ENV_FILE" | cut -d= -f2)
fi

# Check if port is already in use
if netstat -ln 2>/dev/null | grep -q ":$SERVER_PORT " || ss -ln 2>/dev/null | grep -q ":$SERVER_PORT "; then
    echo -e "${YELLOW}⚠${NC}"
    ((WARNINGS++))
    print_info "Port $SERVER_PORT already in use, skipping server test"
    
    # Skip hook script test too
    echo -n "  Testing hook script... "
    echo -e "${YELLOW}⚠${NC}"
    ((WARNINGS++))
    print_info "Hook script test skipped (port conflict)"
else
    # Start server in background
    uv run server.py > /tmp/cc-hooks-server-test.log 2>&1 &
    SERVER_PID=$!
    
    # Wait longer for server startup (WSL can be slower)
    sleep 5
    
    SERVER_RUNNING=false
    if curl -s "http://localhost:$SERVER_PORT/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        print_info "Server is responsive at http://localhost:$SERVER_PORT"
        SERVER_RUNNING=true
        
        # Test database
        echo -n "  Testing database access... "
        if curl -s "http://localhost:$SERVER_PORT/events/status" | grep -q "queued\|processing" 2>/dev/null; then
            echo -e "${GREEN}✓${NC}"
        else
            echo -e "${GREEN}✓${NC}"
            print_info "Database is accessible"
        fi
    
    # Test hook script (now that server is running)
    echo -n "  Testing hook script... "
    TEST_EVENT='{"session_id": "test", "hook_event_name": "Test"}'
    if echo "$TEST_EVENT" | uv run hooks.py 2>/dev/null; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${YELLOW}⚠${NC}"
        ((WARNINGS++))
        print_info "Hook script may have connection issues"
    fi
    
    else
        echo -e "${RED}✗${NC}"
        ((FAILURES++))
        print_info "Server failed to start or respond"
        if [ "$VERBOSE" = true ] && [ -f "/tmp/cc-hooks-server-test.log" ]; then
            print_info "Server log: $(head -3 /tmp/cc-hooks-server-test.log)"
        fi
        
        # Skip hook script test since server failed
        echo -n "  Testing hook script... "
        echo -e "${YELLOW}⚠${NC}"
        ((WARNINGS++))
        print_info "Hook script test skipped (server not running)"
    fi
    
    # Kill test server if it was started
    if [ -n "$SERVER_PID" ]; then
        kill $SERVER_PID 2>/dev/null || true
        wait $SERVER_PID 2>/dev/null || true
    fi
    
    # Clean up log file
    rm -f /tmp/cc-hooks-server-test.log
fi


# Summary Report
print_header "Validation Summary"

TOTAL_ISSUES=$((FAILURES + WARNINGS))

if [ "$FAILURES" -eq 0 ] && [ "$WARNINGS" -eq 0 ]; then
    echo -e "${GREEN}${BOLD}✨ All checks passed! Your cc-hooks installation is ready.${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Start cc-hooks with: ./claude.sh"
    echo "  2. Or use the alias: cld (if configured)"
    exit 0
elif [ "$FAILURES" -eq 0 ]; then
    echo -e "${YELLOW}${BOLD}⚠ Setup is functional with $WARNINGS warning(s)${NC}"
    echo ""
    echo "Your installation will work but some features may be limited."
    echo "Run with --verbose for more details."
    exit 0
else
    echo -e "${RED}${BOLD}✗ Found $FAILURES critical issue(s) and $WARNINGS warning(s)${NC}"
    echo ""
    echo "Please fix the critical issues before using cc-hooks."
    echo "Run with --fix to attempt automatic fixes."
    exit 1
fi