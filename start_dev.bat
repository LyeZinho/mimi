@echo off
setlocal

echo 🚀 Mimi Dev Environment Startup
echo ================================

if not exist ".venv" (
    echo 📦 Creating Python virtual environment...
    python -m venv .venv
)

echo ✓ Virtual environment ready
echo.

echo 📝 To start Mimi, open 3 terminals and run:
echo.
echo Terminal 1 (WebSocket Server):
echo   cd web_avatar ^&^& node server.js
echo.
echo Terminal 2 (Python Agent):
echo   .venv\Scripts\activate.bat
echo   python agent/main.py
echo.
echo Terminal 3 (Frontend):
echo   cd web_avatar ^&^& npm run dev
echo.
echo 🌐 Then open: http://localhost:5173
echo.

endlocal
