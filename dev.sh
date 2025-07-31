#!/bin/bash

# Development script to restart both API server and MCP server
# Kills any processes using ports 9101 and 9102, then starts both servers

API_PORT=9101
MCP_PORT=9102

echo "🔍 Checking for processes using ports $API_PORT and $MCP_PORT..."

# Find processes using the API port
API_PIDS=$(lsof -ti:$API_PORT 2>/dev/null)
if [ -n "$API_PIDS" ]; then
    echo "🛑 Killing API server processes on port $API_PORT: $API_PIDS"
    kill -9 $API_PIDS
else
    echo "✅ No API server processes found on port $API_PORT"
fi

# Find processes using the MCP port
MCP_PIDS=$(lsof -ti:$MCP_PORT 2>/dev/null)
if [ -n "$MCP_PIDS" ]; then
    echo "🛑 Killing MCP server processes on port $MCP_PORT: $MCP_PIDS"
    kill -9 $MCP_PIDS
else
    echo "✅ No MCP server processes found on port $MCP_PORT"
fi

sleep 2

echo "🚀 Starting both API server and MCP server in background..."
echo "📍 API Server: http://localhost:$API_PORT"
echo "📚 API Documentation: http://localhost:$API_PORT/docs"
echo "🔧 MCP Server: http://localhost:$MCP_PORT/mcp"

# Start the API server in background
echo "⚡ Starting API server..."
nohup uv run uvicorn apps.backend.src.main:app --host 0.0.0.0 --port $API_PORT --reload > api_server.log 2>&1 &
API_PID=$!

# Start the MCP server in background
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
    echo "📝 Check logs with: tail -f api_server.log"
fi

echo ""
echo "✨ Both servers running in background!"
echo "🛑 To stop all: kill $API_PID $MCP_PID"