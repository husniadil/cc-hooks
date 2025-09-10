#!/bin/bash
# Claude Code Wrapper

# Configuration
SERVER_SCRIPT="server.py"
REPL_COMMAND="claude"
INSTANCES_DIR=".claude-instances"
INSTANCE_PID=$$
INSTANCE_UUID=$(uuidgen | tr '[:upper:]' '[:lower:]')

# Function to find available port starting from base port
find_available_port() {
    local base_port=12222
    local port=$base_port
    
    # Override base port from .env if available
    if [ -f ".env" ]; then
        # Source .env file to get environment variables
        export $(grep -v '^#' .env | grep -v '^$' | xargs)
        if [ -n "$PORT" ]; then
            base_port=$PORT
            port=$base_port
        fi
    fi
    
    # Find first available port
    while true; do
        if ! curl -s --connect-timeout 1 http://localhost:$port/health >/dev/null 2>&1; then
            # Check if port is actually free (not just unresponsive server)
            if ! netstat -an 2>/dev/null | grep -q ":$port "; then
                echo $port
                return 0
            fi
        fi
        port=$((port + 1))
        
        # Safety limit to prevent infinite loop
        if [ $port -gt $((base_port + 100)) ]; then
            echo "Error: Could not find available port in range $base_port-$((base_port + 100))" >&2
            exit 1
        fi
    done
}

# Find and assign available port for this instance
SERVER_PORT=$(find_available_port)

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

# Function to register this instance with its port
register_instance() {
    mkdir -p "$INSTANCES_DIR"
    echo "$INSTANCE_UUID:$SERVER_PORT" > "$INSTANCES_DIR/$INSTANCE_PID.pid"
    echo "Registered Claude Code instance: $INSTANCE_PID (UUID: $INSTANCE_UUID, Port: $SERVER_PORT)"
}

# Function to unregister this instance
unregister_instance() {
    rm -f "$INSTANCES_DIR/$INSTANCE_PID.pid" 2>/dev/null
    echo "Unregistered Claude Code instance: $INSTANCE_PID (Port: $SERVER_PORT)"
}

# Function to count active instances
count_active_instances() {
    local count=0
    if [ -d "$INSTANCES_DIR" ]; then
        for pidfile in "$INSTANCES_DIR"/*.pid; do
            if [ -f "$pidfile" ]; then
                # Extract PID from filename (not file contents which contains UUID:port)
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

# Each instance gets its own server, so always start one
echo "Starting dedicated cc-hooks server on port $SERVER_PORT..."

# Start server in background with custom port and instance ID, capture errors
STARTUP_LOG="/tmp/cc-hooks-startup-$INSTANCE_UUID.log"
PORT=$SERVER_PORT CC_INSTANCE_ID="$INSTANCE_UUID" uv run "$SERVER_SCRIPT" >"$STARTUP_LOG" 2>&1 &
SERVER_PID=$!

# Wait for server to be ready
for i in {1..10}; do
    if check_server_health; then
        echo "cc-hooks server started successfully on port $SERVER_PORT"
        break
    fi
    
    if ! kill -0 $SERVER_PID 2>/dev/null; then
        echo "Failed to start cc-hooks server on port $SERVER_PORT"
        echo "Server startup error log:"
        cat "$STARTUP_LOG" 2>/dev/null || echo "No startup log available"
        exit 1
    fi
    
    sleep 1
done

if ! check_server_health; then
    echo "cc-hooks server failed to respond on port $SERVER_PORT"
    echo "Server startup log:"
    cat "$STARTUP_LOG" 2>/dev/null || echo "No startup log available"
    kill $SERVER_PID 2>/dev/null || true
    exit 1
fi

# Cleanup function with graceful shutdown
cleanup() {
    echo "Initiating graceful shutdown for instance $INSTANCE_UUID (Port: $SERVER_PORT)..."
    
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
    
    # Stop this instance's dedicated server
    echo "Stopping dedicated cc-hooks server on port $SERVER_PORT..."
    if [ ! -z "$SERVER_PID" ]; then
        kill $SERVER_PID 2>/dev/null || true
        # Wait for graceful shutdown
        for i in {1..3}; do
            if ! kill -0 $SERVER_PID 2>/dev/null; then
                echo "cc-hooks server stopped (Port: $SERVER_PORT)"
                break
            fi
            sleep 1
        done
        # Force kill if still running
        if kill -0 $SERVER_PID 2>/dev/null; then
            kill -9 $SERVER_PID 2>/dev/null || true
            echo "cc-hooks server force stopped (Port: $SERVER_PORT)"
        fi
    fi
    
    # Unregister this instance after cleanup
    unregister_instance
    
    # Show remaining instances
    local remaining_instances=$(count_active_instances)
    echo "Remaining Claude Code instances: $remaining_instances"
    
    # Clean up instances directory if empty
    if [ "$remaining_instances" -eq 0 ] && [ -d "$INSTANCES_DIR" ]; then
        rmdir "$INSTANCES_DIR" 2>/dev/null || true
    fi
    
    exit
}

# Trap cleanup on script exit
trap cleanup EXIT INT TERM

# Set instance ID and port environment variables and start Claude Code with all user arguments
export CC_INSTANCE_ID="$INSTANCE_UUID"
export CC_HOOKS_PORT="$SERVER_PORT"

# If original directory was passed, change to it before starting Claude
if [ -n "$CC_ORIGINAL_DIR" ] && [ -d "$CC_ORIGINAL_DIR" ]; then
    cd "$CC_ORIGINAL_DIR"
fi

echo "Claude Code starting with cc-hooks on port $SERVER_PORT..."
# Clean up startup log on successful start
rm -f "$STARTUP_LOG" 2>/dev/null
$REPL_COMMAND "$@"