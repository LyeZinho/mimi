# 🚀 Mimi - Quick Start Guide

## One-Command Startup (Docker - Recommended)

```bash
docker-compose -f docker-compose.dev.yml up
```

Then open: **http://localhost:5173**

## Services

- 🌐 **React Frontend**: http://localhost:5173
- 📡 **WebSocket Server**: ws://localhost:8765
- 🤖 **Python Agent**: Runs inside container
- 🧠 **Ollama API**: Remote (https://api.ollama.ai)

## Development

### Edit Python Code
```bash
nano agent/agent/main.py
# Changes auto-reload in running container
```

### Edit React Code
```bash
nano web_avatar/src/App.jsx
# Vite hot-reload works automatically
```

### Check Logs
```bash
docker-compose -f docker-compose.dev.yml logs -f
```

### Stop Services
```bash
docker-compose -f docker-compose.dev.yml down
```

## Alternative: Local Setup (No Docker)

### Fish Shell
```fish
source start_dev.fish
```

### Bash/Zsh
```bash
./start_dev.sh
# Then open 3 terminals:
# Terminal 1: cd web_avatar && node server.js
# Terminal 2: source .venv/bin/activate && python agent/main.py
# Terminal 3: cd web_avatar && npm run dev
```

## Troubleshooting

**Port in use**: Edit `docker-compose.dev.yml` and change port numbers  
**ModuleNotFoundError**: Docker sets `PYTHONPATH=/app` automatically  
**Vite errors**: All dependencies pre-installed in container  

## Files

- `docker-compose.dev.yml` — Development setup
- `.env.docker` — Environment template (copy to .env)
- `docs/DOCKER_DEV_SETUP.md` — Detailed guide
- `COMPLETION_SUMMARY.md` — Full project summary

---

**Status**: ✅ Ready to develop!
