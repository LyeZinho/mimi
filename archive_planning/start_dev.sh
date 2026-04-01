#!/bin/bash
set -e

echo "🚀 Mimi Dev Environment Startup"
echo "================================"

# Verify venv exists, create if not
if [ ! -d ".venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv .venv
fi

echo "✓ Virtual environment ready"
echo ""

# Show next steps
echo "📝 To start Mimi, open 3 terminals and run:"
echo ""
echo "Terminal 1 (WebSocket Server):"
echo "  cd web_avatar && node server.js"
echo ""
echo "Terminal 2 (Python Agent):"
echo "  source .venv/bin/activate"
echo "  python agent/main.py"
echo ""
echo "Terminal 3 (Frontend):"
echo "  cd web_avatar && npm run dev"
echo ""
echo "🌐 Then open: http://localhost:5173"
echo ""
