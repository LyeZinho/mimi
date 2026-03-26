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
python agent/main.py &
AGENT_PID=$!
sleep 2
echo -e "${GREEN}✓ Python Agent running (PID: $AGENT_PID)${NC}"

# Start React Frontend
echo -e "${BLUE}⚛️  Starting React Frontend...${NC}"
cd /app/web_avatar
npx vite &
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
