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
        local size_mb=$(du -m "$log_file" | cut -f1)
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
    echo "🔵 API Server logs (api_server.log) | 🟢 MCP Server logs (mcp_server.log)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Create log files if they don't exist
    touch api_server.log mcp_server.log
    
    # Use multitail if available for best experience
    if command -v multitail >/dev/null 2>&1; then
        multitail \
            -ci blue -i api_server.log \
            -ci green -i mcp_server.log
    else
        # Custom log formatting with colors and timestamps
        tail -f api_server.log mcp_server.log | while IFS= read -r line; do
            current_time=$(date '+%H:%M:%S')
            
            if [[ $line =~ "==> api_server.log <==" ]]; then
                echo -e "\n\033[1;34m╭─ API SERVER ─────────────────────────────────────────────────────\033[0m"
            elif [[ $line =~ "==> mcp_server.log <==" ]]; then
                echo -e "\n\033[1;32m╭─ MCP SERVER ─────────────────────────────────────────────────────\033[0m"
            elif [[ $line =~ "==>" ]]; then
                # Skip other file headers
                continue
            else
                # Format different log levels with colors
                if [[ $line =~ "ERROR"|"Error"|"error" ]]; then
                    echo -e "\033[31m│\033[0m \033[90m$current_time\033[0m \033[1;31m$line\033[0m"
                elif [[ $line =~ "WARNING"|"Warning"|"warning"|"WARN" ]]; then
                    echo -e "\033[33m│\033[0m \033[90m$current_time\033[0m \033[1;33m$line\033[0m"
                elif [[ $line =~ "INFO"|"Info"|"info" ]]; then
                    echo -e "\033[36m│\033[0m \033[90m$current_time\033[0m \033[36m$line\033[0m"
                elif [[ $line =~ "DEBUG"|"Debug"|"debug" ]]; then
                    echo -e "\033[35m│\033[0m \033[90m$current_time\033[0m \033[35m$line\033[0m"
                elif [[ $line =~ "SUCCESS"|"Success"|"success"|"✅" ]]; then
                    echo -e "\033[32m│\033[0m \033[90m$current_time\033[0m \033[1;32m$line\033[0m"
                else
                    echo -e "\033[37m│\033[0m \033[90m$current_time\033[0m $line"
                fi
            fi
        done
    fi
}

# Function to stop servers
stop_servers() {
    echo "🛑 Stopping servers..."
    
    # Find and kill API server processes
    API_PIDS=$(lsof -ti:$API_PORT 2>/dev/null)
    if [ -n "$API_PIDS" ]; then
        echo "🛑 Killing API server processes on port $API_PORT: $API_PIDS"
        kill -9 $API_PIDS
    else
        echo "✅ No API server processes found on port $API_PORT"
    fi

    # Find and kill MCP server processes
    MCP_PIDS=$(lsof -ti:$MCP_PORT 2>/dev/null)
    if [ -n "$MCP_PIDS" ]; then
        echo "🛑 Killing MCP server processes on port $MCP_PORT: $MCP_PIDS"
        kill -9 $MCP_PIDS
    else
        echo "✅ No MCP server processes found on port $MCP_PORT"
    fi
    
    # Kill any log rotation monitor processes
    LOG_MONITOR_PIDS=$(pgrep -f "sleep 300.*rotate_logs" 2>/dev/null)
    if [ -n "$LOG_MONITOR_PIDS" ]; then
        echo "🔄 Stopping log rotation monitor: $LOG_MONITOR_PIDS"
        kill -9 $LOG_MONITOR_PIDS 2>/dev/null
    fi
}

# Function to start servers
start_servers() {
    echo "🚀 Starting both API server and MCP server in background..."
    echo "📍 API Server: http://localhost:$API_PORT"
    echo "📚 API Documentation: http://localhost:$API_PORT/docs"
    echo "🔧 MCP Server: http://localhost:$MCP_PORT/mcp"

    # Rotate logs if they're getting too large
    echo "🔄 Checking log rotation..."
    rotate_logs "api_server.log" 10 3
    rotate_logs "mcp_server.log" 10 3

    # Start the API server in background with log rotation
    echo "⚡ Starting API server..."
    nohup uv run uvicorn apps.backend.src.main:app --host 0.0.0.0 --port $API_PORT --reload > api_server.log 2>&1 &
    API_PID=$!

    # Start the MCP server in background with log rotation
    echo "⚡ Starting MCP server..."
    nohup python mcp_server.py > mcp_server.log 2>&1 &
    MCP_PID=$!

    echo "📊 API Server started with PID: $API_PID"
    echo "📊 MCP Server started with PID: $MCP_PID"
    echo "📝 API Logs: tail -f api_server.log"
    echo "📝 MCP Logs: tail -f mcp_server.log"
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
            rotate_logs "api_server.log" 10 3
            rotate_logs "mcp_server.log" 10 3
        done
    ) &
    LOG_MONITOR_PID=$!
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