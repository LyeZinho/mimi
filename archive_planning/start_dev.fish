#!/usr/bin/env fish
# Fish shell compatible venv activation
set VENV_PATH (pwd)/.venv

if not test -d $VENV_PATH
    echo "📦 Creating Python virtual environment..."
    python3 -m venv $VENV_PATH
end

echo "✓ Activating Python venv..."
source $VENV_PATH/bin/activate.fish

echo ""
echo "📝 To start Mimi, open 3 terminals and run:"
echo ""
echo "Terminal 1 (WebSocket Server):"
echo "  cd web_avatar && node server.js"
echo ""
echo "Terminal 2 (Python Agent):"
echo "  source .venv/bin/activate.fish"
echo "  python agent/main.py"
echo ""
echo "Terminal 3 (Frontend):"
echo "  cd web_avatar && npm run dev"
echo ""
echo "🌐 Then open: http://localhost:5173"
echo ""
