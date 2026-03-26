# 🐳 Docker Development Setup

This guide shows how to run Mimi entirely in Docker for local development.

## Quick Start

### 1. Copy Environment File

```bash
cp .env.docker .env
```

### 2. Build and Start

```bash
docker-compose -f docker-compose.dev.yml up
```

Wait for all services to start (~15 seconds). You should see:

```
✅ All services started!

🌐 Frontend: http://localhost:5173
📡 WebSocket: ws://localhost:8765
```

### 3. Open Browser

Visit: **http://localhost:5173**

---

## How It Works

### Services

The Docker container runs **all 3 services** simultaneously:

1. **Node.js WebSocket Server** (port 8765)
   - Manages avatar state
   - Routes messages between agent and frontend

2. **Python Agent** (internal)
   - Runs LLM inference
   - Manages memory and tools
   - Communicates via WebSocket

3. **React Frontend** (port 5173)
   - Vite dev server with hot-reload
   - Three.js avatar rendering
   - Chat interface

### Volume Mounts

```yaml
volumes:
  - .:/app                         # Source code (live edit)
  - /app/node_modules              # NPM cache (prevent sync)
  - /app/web_avatar/node_modules   # NPM cache (prevent sync)
  - /app/.venv                     # Python venv cache
```

This setup allows **live code editing** — changes instantly reflect in the running container.

### Environment Variables

All config comes from `.env.docker`:

```
OLLAMA_HOST=https://api.ollama.ai
OLLAMA_API_KEY=your_key_here
PYTHONPATH=/app  # Critical for module resolution
WEBSOCKET_HOST=0.0.0.0
```

---

## Development Workflow

### Edit Python Code

```bash
# Edit agent code (while container running)
nano agent/agent/main.py

# Agent automatically reloads (thanks to PYTHONPATH)
# Check logs in running container
```

### Edit React Code

```bash
# Edit React components (while container running)
nano web_avatar/src/App.jsx

# Vite hot-reload triggers automatically
# Browser updates instantly
```

### Check Logs

In another terminal:

```bash
# View all logs
docker-compose -f docker-compose.dev.yml logs -f

# View only Python agent logs
docker-compose -f docker-compose.dev.yml logs -f mimi | grep "agent"

# View only WebSocket server logs
docker-compose -f docker-compose.dev.yml logs -f mimi | grep "WebSocket"
```

---

## Stopping Services

```bash
# Stop gracefully (Ctrl+C in terminal where docker-compose is running)
# Or in another terminal:
docker-compose -f docker-compose.dev.yml down
```

---

## Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose -f docker-compose.dev.yml logs

# Rebuild without cache
docker-compose -f docker-compose.dev.yml build --no-cache
```

### Port already in use

```bash
# Change ports in docker-compose.dev.yml
ports:
  - "8766:8765"  # Changed 8765 → 8766
  - "5174:5173"  # Changed 5173 → 5174
```

Then visit: `http://localhost:5174`

### Python module import errors

```bash
# Verify PYTHONPATH in container
docker-compose -f docker-compose.dev.yml exec mimi printenv PYTHONPATH

# Should show: /app
# If not, rebuild container
docker-compose -f docker-compose.dev.yml build --no-cache
```

### "Cannot reach api.ollama.ai"

Verify `.env.docker` has your API key:

```bash
cat .env.docker | grep OLLAMA
```

Should show both `OLLAMA_HOST` and `OLLAMA_API_KEY`.

---

## Comparison: Docker vs Local Setup

| Aspect | Local | Docker |
|--------|-------|--------|
| **Setup time** | 15 minutes | 30 seconds |
| **Shell compatibility** | Fish/Bash/Zsh issues | Works everywhere |
| **Module imports** | PYTHONPATH issues | Pre-configured |
| **Dependencies** | Manual venv/npm | Automatic |
| **Cross-platform** | Path issues on Windows | Identical everywhere |
| **Live edit** | Requires restart | Hot-reload works |
| **Development speed** | Setup friction | Instant startup |

---

## Next Steps

1. Run: `docker-compose -f docker-compose.dev.yml up`
2. Wait for startup message
3. Open: http://localhost:5173
4. Start developing!

See also:
- `docs/SETUP_COMPLETE.md` — Full project overview
- `Dockerfile.dev` — Development Dockerfile
- `docker/entrypoint.sh` — Service startup script
