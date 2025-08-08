#!/bin/bash

# Development script to manage API server and MCP server
# Usage: ./dev.sh [logs|start|stop|restart]
# - logs: Show logs from both servers
# - start: Start both servers (default)
# - stop: Stop both servers
# - restart: Restart both servers

API_PORT=9101
MCP_PORT=9102

# Function to rotate logs if they exceed size limit
rotate_logs() {
    local log_file=$1
    local max_size_mb=${2:-10}
    local max_files=${3:-3}
    
    if [ -f "$log_file" ]; then
        local size_mb
        size_mb=$(du -m "$log_file" | cut -f1)
        if [ "$size_mb" -ge "$max_size_mb" ]; then
            echo "🔄 Rotating $log_file (${size_mb}MB)"
            
            # Rotate existing backup files
            for (( i=$((max_files-1)); i>=1; i-- )); do
                if [ -f "${log_file}.$i" ]; then
                    mv "${log_file}.$i" "${log_file}.$((i+1))"
                fi
            done
            
            # Move current log to .1
            mv "$log_file" "${log_file}.1"
            touch "$log_file"
        fi
    fi
}

# Function to show logs with pretty formatting
show_logs() {
    echo "📝 Showing logs from both servers (Ctrl+C to exit)..."
    echo "🔵 API Server logs (logs/api_server.log) | 🟢 MCP Server logs (logs/mcp_server.log)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Create logs directory and log files if they don't exist
    mkdir -p logs
    touch logs/api_server.log logs/mcp_server.log
    
    # Use multitail if available for best experience
    if command -v multitail >/dev/null 2>&1; then
        multitail \
            -ci blue -i logs/api_server.log \
            -ci green -i logs/mcp_server.log
    else
        # Custom log formatting with colors and timestamps
        tail -f logs/api_server.log logs/mcp_server.log | while IFS= read -r line; do
            current_time=$(date '+%H:%M:%S')
            
            if [[ $line =~ ^==\>[[:space:]]logs/api_server\.log[[:space:]]\<==$ ]]; then
                echo -e "\n\033[1;34m╭─ API SERVER ─────────────────────────────────────────────────────\033[0m"
            elif [[ $line =~ ^==\>[[:space:]]logs/mcp_server\.log[[:space:]]\<==$ ]]; then
                echo -e "\n\033[1;32m╭─ MCP SERVER ─────────────────────────────────────────────────────\033[0m"
            elif [[ $line =~ "==>" ]]; then
                # Skip other file headers
                continue
            else
                # Format different log levels with colors
                if [[ $line =~ (ERROR|Error|error) ]]; then
                    echo -e "\033[31m│\033[0m \033[90m$current_time\033[0m \033[1;31m$line\033[0m"
                elif [[ $line =~ (WARNING|Warning|warning|WARN) ]]; then
                    echo -e "\033[33m│\033[0m \033[90m$current_time\033[0m \033[1;33m$line\033[0m"
                elif [[ $line =~ (INFO|Info|info) ]]; then
                    echo -e "\033[36m│\033[0m \033[90m$current_time\033[0m \033[36m$line\033[0m"
                elif [[ $line =~ (DEBUG|Debug|debug) ]]; then
                    echo -e "\033[35m│\033[0m \033[90m$current_time\033[0m \033[35m$line\033[0m"
                elif [[ $line =~ (SUCCESS|Success|success|✅) ]]; then
                    echo -e "\033[32m│\033[0m \033[90m$current_time\033[0m \033[1;32m$line\033[0m"
                else
                    echo -e "\033[37m│\033[0m \033[90m$current_time\033[0m $line"
                fi
            fi
        done
    fi
}

# Function to kill process tree recursively
kill_process_tree() {
    local pid=$1
    local signal=${2:-TERM}
    
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        # Get all child processes
        local children
        children=$(pgrep -P "$pid" 2>/dev/null || true)
        
        # Recursively kill children first
        for child in $children; do
            kill_process_tree "$child" "$signal"
        done
        
        # Kill the parent process
        kill -"$signal" "$pid" 2>/dev/null || true
    fi
}

# Function to stop servers with comprehensive cleanup
stop_servers() {
    echo "🛑 Stopping servers..."
    
    # Read stored PIDs if they exist
    API_STORED_PID=""
    MCP_STORED_PID=""
    LOG_MONITOR_STORED_PID=""
    
    if [ -f "logs/api.pid" ]; then
        API_STORED_PID=$(cat logs/api.pid 2>/dev/null)
    fi
    if [ -f "logs/mcp.pid" ]; then
        MCP_STORED_PID=$(cat logs/mcp.pid 2>/dev/null)
    fi
    if [ -f "logs/rotation.pid" ]; then
        LOG_MONITOR_STORED_PID=$(cat logs/rotation.pid 2>/dev/null)
    fi
    
    # Find API server processes using multiple methods
    API_PIDS=""
    
    # Method 1: Stored PID
    if [ -n "$API_STORED_PID" ] && kill -0 "$API_STORED_PID" 2>/dev/null; then
        API_PIDS="$API_STORED_PID"
    fi
    
    # Method 2: Pattern matching for uvicorn with our app
    PATTERN_API_PIDS=$(pgrep -f "uvicorn.*apps\.backend\.src\.main:app" 2>/dev/null || true)
    if [ -n "$PATTERN_API_PIDS" ]; then
        API_PIDS="$API_PIDS $PATTERN_API_PIDS"
    fi
    
    # Method 3: Port-based detection
    PORT_API_PIDS=$(ss -tulpn | grep ":$API_PORT " | awk '{print $7}' | cut -d',' -f2 | cut -d'=' -f2 2>/dev/null || true)
    if [ -n "$PORT_API_PIDS" ]; then
        API_PIDS="$API_PIDS $PORT_API_PIDS"
    fi
    
    # Remove duplicates and kill API processes
    API_PIDS=$(echo "$API_PIDS" | tr ' ' '\n' | sort -u | tr '\n' ' ')
    if [ -n "$API_PIDS" ]; then
        echo "🛑 Killing API server processes: $API_PIDS"
        for pid in $API_PIDS; do
            if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
                kill_process_tree "$pid" "TERM"
            fi
        done
        
        # Wait and force kill if needed
        sleep 3
        for pid in $API_PIDS; do
            if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
                echo "💀 Force killing API process: $pid"
                kill_process_tree "$pid" "KILL"
            fi
        done
    else
        echo "✅ No API server processes found"
    fi

    # Find and kill MCP server processes using multiple methods
    MCP_PIDS=""
    
    # Method 1: Stored PID
    if [ -n "$MCP_STORED_PID" ] && kill -0 "$MCP_STORED_PID" 2>/dev/null; then
        MCP_PIDS="$MCP_STORED_PID"
    fi
    
    # Method 2: Pattern matching
    PATTERN_MCP_PIDS=$(pgrep -f "python.*apps/backend/src/mcp/server\.py" 2>/dev/null || true)
    if [ -n "$PATTERN_MCP_PIDS" ]; then
        MCP_PIDS="$MCP_PIDS $PATTERN_MCP_PIDS"
    fi
    
    # Method 3: Port-based detection
    PORT_MCP_PIDS=$(ss -tulpn | grep ":$MCP_PORT " | awk '{print $7}' | cut -d',' -f2 | cut -d'=' -f2 2>/dev/null || true)
    if [ -n "$PORT_MCP_PIDS" ]; then
        MCP_PIDS="$MCP_PIDS $PORT_MCP_PIDS"
    fi
    
    # Remove duplicates and kill MCP processes
    MCP_PIDS=$(echo "$MCP_PIDS" | tr ' ' '\n' | sort -u | tr '\n' ' ')
    if [ -n "$MCP_PIDS" ]; then
        echo "🛑 Killing MCP server processes: $MCP_PIDS"
        for pid in $MCP_PIDS; do
            if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
                kill_process_tree "$pid" "TERM"
            fi
        done
        
        # Wait and force kill if needed
        sleep 3
        for pid in $MCP_PIDS; do
            if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
                echo "💀 Force killing MCP process: $pid"
                kill_process_tree "$pid" "KILL"
            fi
        done
    else
        echo "✅ No MCP server processes found"
    fi
    
    # Kill log rotation monitor
    if [ -n "$LOG_MONITOR_STORED_PID" ] && kill -0 "$LOG_MONITOR_STORED_PID" 2>/dev/null; then
        echo "🔄 Stopping log rotation monitor: $LOG_MONITOR_STORED_PID"
        kill_process_tree "$LOG_MONITOR_STORED_PID" "TERM"
        sleep 1
        if kill -0 "$LOG_MONITOR_STORED_PID" 2>/dev/null; then
            kill_process_tree "$LOG_MONITOR_STORED_PID" "KILL"
        fi
    fi
    
    # Additional cleanup: Kill any orphaned infrastructor-related Python processes
    echo "🧹 Cleaning up orphaned processes..."
    ORPHANED_PIDS=$(pgrep -f "infrastructor" | grep -E "^[0-9]+$" || true)
    for pid in $ORPHANED_PIDS; do
        # Check if it's a Python process in our project directory
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            PROC_CMD=$(ps -p "$pid" -o cmd --no-headers 2>/dev/null || true)
            if echo "$PROC_CMD" | grep -q "python.*apps/backend\|uvicorn.*apps\.backend"; then
                echo "🧹 Killing orphaned process $pid: $(echo "$PROC_CMD" | cut -c1-60)..."
                kill_process_tree "$pid" "TERM"
                sleep 1
                if kill -0 "$pid" 2>/dev/null; then
                    kill_process_tree "$pid" "KILL"
                fi
            fi
        fi
    done
    
    # Clean up PID files
    rm -f logs/api.pid logs/mcp.pid logs/rotation.pid
    
    echo "✅ All processes stopped and cleaned up"
}

# Function to start servers
start_servers() {
    echo "🚀 Starting both API server and MCP server in background..."
    echo "📍 API Server: http://localhost:$API_PORT"
    echo "📚 API Documentation: http://localhost:$API_PORT/docs"
    echo "🔧 MCP Server: http://localhost:$MCP_PORT/mcp"

    # Ensure logs directory exists
    mkdir -p logs

    # Rotate logs if they're getting too large
    echo "🔄 Checking log rotation..."
    rotate_logs "logs/api_server.log" 10 3
    rotate_logs "logs/mcp_server.log" 10 3

    # Start the API server in background with log rotation
    echo "⚡ Starting API server..."
    nohup uv run uvicorn apps.backend.src.main:app --host 0.0.0.0 --port $API_PORT --reload > logs/api_server.log 2>&1 &
    API_PID=$!
    echo "$API_PID" > logs/api.pid

    # Start the MCP server in background with log rotation and environment variables
    echo "⚡ Starting MCP server..."
    # Source environment variables for MCP server
    if [ -f ".env" ]; then
        export $(grep -v '^#' .env | grep -v '^$' | xargs)
    fi
    nohup uv run python apps/backend/src/mcp/server.py > logs/mcp_server.log 2>&1 &
    MCP_PID=$!
    echo "$MCP_PID" > logs/mcp.pid

    echo "📊 API Server started with PID: $API_PID"
    echo "📊 MCP Server started with PID: $MCP_PID"
    echo "📝 API Logs: tail -f logs/api_server.log"
    echo "📝 MCP Logs: tail -f logs/mcp_server.log"
    echo "🛑 To stop API: kill $API_PID"
    echo "🛑 To stop MCP: kill $MCP_PID"

    # Wait a moment for servers to start
    echo "⏳ Waiting for servers to start..."
    sleep 5

    # Simple health check for API server
    echo "🩺 Checking API server health..."
    HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$API_PORT/health 2>/dev/null)
    if [ "$HEALTH_RESPONSE" = "200" ]; then
        echo "✅ API Server started successfully"
    else
        echo "⚠️  API Server may still be starting (health check returned: $HEALTH_RESPONSE)"
        echo "📝 Check logs with: ./dev.sh logs"
    fi

    echo ""
    echo "✨ Both servers running in background!"
    echo "🛑 To stop all: kill $API_PID $MCP_PID"
    echo "📝 To view logs: ./dev.sh logs"
    
    # Start background log rotation monitor
    (
        while true; do
            sleep 300  # Check every 5 minutes
            rotate_logs "logs/api_server.log" 10 3
            rotate_logs "logs/mcp_server.log" 10 3
        done
    ) &
    LOG_MONITOR_PID=$!
    echo "$LOG_MONITOR_PID" > logs/rotation.pid
    echo "🔄 Log rotation monitor started with PID: $LOG_MONITOR_PID"
}

# Parse command line arguments
case "${1:-start}" in
    "logs")
        show_logs
        ;;
    "stop")
        stop_servers
        ;;
    "start")
        stop_servers
        sleep 2
        start_servers
        ;;
    "restart")
        stop_servers
        sleep 2
        start_servers
        ;;
    *)
        echo "Usage: $0 [logs|start|stop|restart]"
        echo "  logs    - Show logs from both servers"
        echo "  start   - Start both servers (default)"
        echo "  stop    - Stop both servers"  
        echo "  restart - Restart both servers"
        exit 1
        ;;
esac