#!/bin/bash
# Claude Code Wrapper

# Configuration
SERVER_SCRIPT="server.py"
REPL_COMMAND="claude"
INSTANCES_DIR=".claude-instances"
INSTANCE_PID=$$
INSTANCE_UUID=$(uuidgen | tr '[:upper:]' '[:lower:]')

# Load port from .env file or use default
SERVER_PORT=12222
if [ -f ".env" ]; then
    # Source .env file to get environment variables
    export $(grep -v '^#' .env | grep -v '^$' | xargs)
fi
# Use PORT environment variable if available
if [ -n "$PORT" ]; then
    SERVER_PORT=$PORT
fi

# Function to check if server is responding
check_server_health() {
    curl -s --connect-timeout 2 http://localhost:$SERVER_PORT/health >/dev/null 2>&1
}

# Function to check if last event is still pending for this instance
check_last_event_pending() {
    local response
    response=$(curl -s --connect-timeout 2 http://localhost:$SERVER_PORT/instances/$INSTANCE_UUID/last-event 2>/dev/null)
    if [ $? -eq 0 ]; then
        # Extract has_pending boolean from JSON response - improved pattern
        echo "$response" | grep -o '"has_pending":\(true\|false\)' | grep -o '\(true\|false\)'
    else
        echo "false"  # Default to false if API call fails
    fi
}

# Function to register this instance
register_instance() {
    mkdir -p "$INSTANCES_DIR"
    echo "$INSTANCE_UUID" > "$INSTANCES_DIR/$INSTANCE_PID.pid"
    echo "Registered Claude Code instance: $INSTANCE_PID (UUID: $INSTANCE_UUID)"
}

# Function to unregister this instance
unregister_instance() {
    rm -f "$INSTANCES_DIR/$INSTANCE_PID.pid" 2>/dev/null
    echo "Unregistered Claude Code instance: $INSTANCE_PID"
}

# Function to count active instances
count_active_instances() {
    local count=0
    if [ -d "$INSTANCES_DIR" ]; then
        for pidfile in "$INSTANCES_DIR"/*.pid; do
            if [ -f "$pidfile" ]; then
                # Extract PID from filename (not file contents which contains UUID)
                local pid=$(basename "$pidfile" .pid)
                # Check if process is still running
                if kill -0 "$pid" 2>/dev/null; then
                    count=$((count + 1))
                else
                    # Clean up stale PID file
                    rm -f "$pidfile"
                fi
            fi
        done
    fi
    echo $count
}

# Clean up any stale PID files from previous runs
if [ -d "$INSTANCES_DIR" ]; then
    stale_count=0
    for pidfile in "$INSTANCES_DIR"/*.pid; do
        if [ -f "$pidfile" ]; then
            # Extract PID from filename (not file contents which contains UUID)
            pid=$(basename "$pidfile" .pid)
            if ! kill -0 "$pid" 2>/dev/null; then
                rm -f "$pidfile"
                stale_count=$((stale_count + 1))
            fi
        fi
    done
    if [ $stale_count -gt 0 ]; then
        echo "Cleaned up $stale_count stale instance(s)"
    fi
fi

# Register this instance BEFORE starting server
register_instance

# Show current active instances after registration
active_count=$(count_active_instances)
echo "Active Claude Code instances: $active_count"

# Check if cc-hooks server is running
if check_server_health; then
    echo "cc-hooks server already running on port $SERVER_PORT"
else
    # Kill any existing server processes
    pkill -f "uv run.*$SERVER_SCRIPT" 2>/dev/null || true
    sleep 1
    
    # Start server silently in background
    uv run "$SERVER_SCRIPT" >/dev/null 2>&1 &
    SERVER_PID=$!
    
    # Wait for server to be ready
    for i in {1..10}; do
        if check_server_health; then
            echo "cc-hooks server started on port $SERVER_PORT"
            break
        fi
        
        if ! kill -0 $SERVER_PID 2>/dev/null; then
            echo "Failed to start cc-hooks server"
            exit 1
        fi
        
        sleep 1
    done
    
    if ! check_server_health; then
        echo "cc-hooks server failed to respond"
        kill $SERVER_PID 2>/dev/null || true
        exit 1
    fi
fi

# Store PID for cleanup
if [ -z "$SERVER_PID" ]; then
    SERVER_PID=$(pgrep -f "uv run.*$SERVER_SCRIPT" | head -n1)
fi

# Cleanup function with graceful shutdown
cleanup() {
    echo "Initiating graceful shutdown for instance $INSTANCE_UUID..."
    
    # Check if last event is still pending before unregistering
    local has_pending=$(check_last_event_pending)
    echo "Last event pending status for this instance: $has_pending"
    
    # Wait for last event to complete (max 10 seconds)
    if [ "$has_pending" = "true" ]; then
        echo "Waiting for last event to complete..."
        local wait_count=0
        while [ "$has_pending" = "true" ] && [ "$wait_count" -lt 10 ]; do
            sleep 1
            has_pending=$(check_last_event_pending)
            wait_count=$((wait_count + 1))
            if [ "$has_pending" = "true" ]; then
                echo "Still waiting for last event... (${wait_count}s elapsed)"
            fi
        done
        
        if [ "$has_pending" = "true" ]; then
            echo "Warning: Force exiting with last event still pending after 10s timeout"
        else
            echo "Last event completed successfully"
        fi
    fi
    
    # Unregister this instance after waiting for events
    unregister_instance
    
    # Check how many instances are still running
    local remaining_instances=$(count_active_instances)
    echo "Remaining Claude Code instances: $remaining_instances"
    
    # Only stop server if this was the last instance
    if [ "$remaining_instances" -eq 0 ]; then
        echo "Last instance exiting, stopping cc-hooks server..."
        if [ ! -z "$SERVER_PID" ]; then
            kill $SERVER_PID 2>/dev/null || true
            # Wait for graceful shutdown
            for i in {1..3}; do
                if ! kill -0 $SERVER_PID 2>/dev/null; then
                    echo "cc-hooks server stopped"
                    break
                fi
                sleep 1
            done
            # Force kill if still running
            if kill -0 $SERVER_PID 2>/dev/null; then
                kill -9 $SERVER_PID 2>/dev/null || true
                echo "cc-hooks server force stopped"
            fi
        fi
        pkill -f "uv run.*$SERVER_SCRIPT" 2>/dev/null || true
        
        # Clean up instances directory
        rm -rf "$INSTANCES_DIR"
    else
        echo "Other Claude Code instances still running, keeping cc-hooks server alive"
    fi
    exit
}

# Trap cleanup on script exit
trap cleanup EXIT INT TERM

# Set instance ID environment variable and start Claude Code with all user arguments
export CC_INSTANCE_ID="$INSTANCE_UUID"

# If original directory was passed, change to it before starting Claude
if [ -n "$CC_ORIGINAL_DIR" ] && [ -d "$CC_ORIGINAL_DIR" ]; then
    cd "$CC_ORIGINAL_DIR"
fi

$REPL_COMMAND "$@"