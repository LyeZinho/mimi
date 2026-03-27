#!/bin/bash
set -e

echo "🚀 Mimi Dev Container Starting"
echo "=============================="
echo ""

export PYTHONPATH=/app
export PATH="/opt/venv/bin:/app/web_avatar/node_modules/.bin:/app/node_modules/.bin:$PATH"

# Wait for services to be ready
echo "⏳ Waiting for services to initialize..."
sleep 2

# Terminal colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Start WebSocket Server
echo -e "${BLUE}📡 Starting WebSocket Server...${NC}"
cd /app/web_avatar
node server.js &
WS_PID=$!
sleep 2
echo -e "${GREEN}✓ WebSocket Server running (PID: $WS_PID)${NC}"

# Start Python Agent
echo -e "${BLUE}🤖 Starting Python Agent...${NC}"
cd /app
PYTHONPATH=/app python agent/main.py > /tmp/agent_output.log 2>&1 &
AGENT_PID=$!
sleep 3
echo -e "${GREEN}✓ Python Agent running (PID: $AGENT_PID)${NC}"

# Check health check status
if grep -q "✅ All brains operational" /tmp/agent_output.log 2>/dev/null; then
    echo -e "${GREEN}✅ Health check passed${NC}"
    # Display health check results
    grep "✓.*operational\|⚠.*timeout\|✗.*failed" /tmp/agent_output.log | head -7
elif grep -q "Brain health check issues detected" /tmp/agent_output.log 2>/dev/null; then
    echo -e "${BLUE}⚠️  Health check issues detected${NC}"
    # Display each failed brain with details
    grep "✗.*failed\|⚠.*timeout" /tmp/agent_output.log
    echo -e "${BLUE}Starting agent anyway - some functionality may be degraded${NC}"
elif grep -q "⚠️ Some brains failed" /tmp/agent_output.log 2>/dev/null; then
    echo -e "${BLUE}⚠️  Health check partial - some brains failed${NC}"
    grep "✓.*operational\|⚠.*timeout\|✗.*failed" /tmp/agent_output.log | head -7
else
    echo -e "${BLUE}ℹ️  Health check status: checking logs...${NC}"
    # Show first 5 lines of agent output for debugging
    head -5 /tmp/agent_output.log 2>/dev/null || echo "No agent output available yet"
fi

# Start React Frontend
echo -e "${BLUE}⚛️  Starting React Frontend...${NC}"
cd /app/web_avatar
/app/web_avatar/node_modules/.bin/vite --host 0.0.0.0 --port 5173 &
REACT_PID=$!
sleep 3
echo -e "${GREEN}✓ React Frontend running (PID: $REACT_PID)${NC}"

echo ""
echo "=============================="
echo -e "${GREEN}✅ All services started!${NC}"
echo "=============================="
echo ""
echo "🌐 Frontend: http://localhost:5173"
echo "📡 WebSocket: ws://localhost:8765"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for all processes
wait $WS_PID $AGENT_PID $REACT_PID
