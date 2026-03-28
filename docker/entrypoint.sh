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

# Start Python Agent with auto-restart
echo -e "${BLUE}🤖 Starting Python Agent...${NC}"
cd /app
(
  while true; do
    PYTHONPATH=/app python agent/main.py > /tmp/agent_output.log 2>&1
    echo -e "${BLUE}Agent exited, restarting in 3s...${NC}"
    sleep 3
  done
) &
AGENT_PID=$!
sleep 8
echo -e "${GREEN}✓ Python Agent running (PID: $AGENT_PID)${NC}"

# Check health check status (wait for health checks to complete)
sleep 1
if grep -q "✅ All brains operational" /tmp/agent_output.log 2>/dev/null; then
    echo -e "${GREEN}✅ All brains operational${NC}"
    grep "| ✓.*operational" /tmp/agent_output.log | head -7
elif grep -q "Brain health check issues detected" /tmp/agent_output.log 2>/dev/null; then
    echo -e "${BLUE}⚠️  Brain health check issues detected:${NC}"
    grep "| ✗\|| ⚠" /tmp/agent_output.log
    echo -e "${BLUE}Starting agent anyway - some functionality may be degraded${NC}"
else
    echo -e "${BLUE}ℹ️  Health check status: checking logs...${NC}"
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
