# Ollama Integration & Project Setup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate Ollama API (with provided API key) into Mimi project and perform complete project setup (Python + Node.js + frontend).

**Architecture:** 
- Create `.env` with Ollama API credentials (using provided key for remote service)
- Setup Python 3.10+ venv with all dependencies (core + voice + tts optional)
- Setup Node.js dependencies for WebSocket server and React frontend
- Verify Ollama connectivity and test agent→LLM communication
- Create initialization scripts for easy startup

**Tech Stack:** Python 3.10+, Node.js 18+, Ollama API, asyncio, httpx, React 18, Vite

---

## Task 1: Create Environment Configuration

**Files:**
- Create: `.env` (root)
- Create: `.env.example` (root)

**Step 1: Create .env.example template**

This documents all environment variables needed:

```
# Ollama Configuration
OLLAMA_HOST=https://api.ollama.example.com
OLLAMA_API_KEY=your_api_key_here
LLM_MODEL=phi3:mini

# Avatar Configuration
AVATAR_TYPE=web
WEBSOCKET_HOST=localhost
WEBSOCKET_PORT=8765

# Database
DB_PATH=data/memory.db
PERSONA_PATH=data/persona.json

# Frontend
VITE_WS_URL=ws://localhost:8765
```

**Step 2: Create actual .env with provided key**

```
OLLAMA_HOST=https://api.ollama.ai
OLLAMA_API_KEY=7d5fefd71866442f848242162671602e.BscZ3cc5eQc6cx9d6-yhXhiC
LLM_MODEL=phi3:mini

AVATAR_TYPE=web
WEBSOCKET_HOST=localhost
WEBSOCKET_PORT=8765

DB_PATH=data/memory.db
PERSONA_PATH=data/persona.json

VITE_WS_URL=ws://localhost:8765
```

**Step 3: Update .gitignore to exclude .env**

```
.env
.env.local
.env.*.local
```

**Step 4: Commit**

```bash
git add .env.example .gitignore
git commit -m "config: add env template and update gitignore"
```

---

## Task 2: Update Python LLM Client for API Key Support

**Files:**
- Modify: `agent/config.py`
- Modify: `agent/llm/client.py`

**Step 1: Update config.py to load API key**

Replace lines 18-20 in `agent/config.py`:

OLD:
```python
# LLM
LLM_MODEL = os.getenv("LLM_MODEL", "phi3:mini")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
```

NEW:
```python
# LLM (Ollama)
LLM_MODEL = os.getenv("LLM_MODEL", "phi3:mini")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")  # For remote Ollama API
```

**Step 2: Update LLMClient to use API key**

Modify `agent/llm/client.py` lines 37-48 in the `_chat` method:

OLD:
```python
async def _chat(self, messages: list[dict[str, str]]) -> str:
    """Envia mensagens para a API de chat do Ollama."""
    url = f"{self.base_url}/api/chat"
    payload = {
        "model": self.model,
        "messages": messages,
        "stream": False,
    }
    resp = await self._client.post(url, json=payload)
    resp.raise_for_status()
    data = resp.json()
    return data.get("message", {}).get("content", "")
```

NEW:
```python
async def _chat(self, messages: list[dict[str, str]]) -> str:
    """Envia mensagens para a API de chat do Ollama."""
    from agent.config import OLLAMA_API_KEY
    
    url = f"{self.base_url}/api/chat"
    headers = {}
    if OLLAMA_API_KEY:
        headers["Authorization"] = f"Bearer {OLLAMA_API_KEY}"
    
    payload = {
        "model": self.model,
        "messages": messages,
        "stream": False,
    }
    
    resp = await self._client.post(url, json=payload, headers=headers if headers else None)
    resp.raise_for_status()
    data = resp.json()
    return data.get("message", {}).get("content", "")
```

**Step 3: Verify no type errors**

```bash
python -m py_compile agent/config.py agent/llm/client.py
```

Expected: No output (success)

**Step 4: Commit**

```bash
git add agent/config.py agent/llm/client.py
git commit -m "feat: add Ollama API key support for remote service"
```

---

## Task 3: Setup Python Virtual Environment & Dependencies

**Files:**
- Modified: `pyproject.toml` (if needed)
- Run: `pip install` commands

**Step 1: Create virtual environment**

```bash
python3 -m venv .venv
```

Expected: `.venv/` directory created

**Step 2: Activate venv**

On Linux/Mac:
```bash
source .venv/bin/activate
```

On Windows:
```bash
.venv\Scripts\activate.bat
```

**Step 3: Upgrade pip, setuptools, wheel**

```bash
pip install --upgrade pip setuptools wheel
```

**Step 4: Install core dependencies**

```bash
pip install -r requirements.txt
```

Expected: All packages from requirements.txt installed

**Step 5: Install optional voice dependencies (for future STT)**

```bash
pip install sounddevice>=0.4 webrtcvad>=2.0 faster-whisper>=0.9
```

**Step 6: Install optional TTS dependencies (for future TTS)**

```bash
pip install piper-tts>=1.0
```

**Step 7: Verify installation**

```bash
python -c "import pydantic; import httpx; import websockets; print('✓ Core deps OK')"
```

Expected: `✓ Core deps OK`

**Step 8: No commit needed** (venv is in .gitignore)

---

## Task 4: Create Persona JSON Configuration

**Files:**
- Create: `data/persona.json`

**Step 1: Create data directory**

```bash
mkdir -p data
```

**Step 2: Create persona.json**

```json
{
  "name": "Mimi",
  "description": "assistente de IA multimodal amigável e expressiva",
  "instructions": [
    "Responda sempre em português português.",
    "Seja amigável e empática.",
    "Se não souber, pergunte ou use ferramentas para buscar informações.",
    "Mantenha respostas concisas (1-3 frases).",
    "Use humor quando apropriado."
  ],
  "intents": [
    "speak",
    "use_tool",
    "change_state",
    "ask_clarification"
  ],
  "emotions": [
    "neutral",
    "happy",
    "curious",
    "confused",
    "thoughtful"
  ],
  "max_history_items": 5
}
```

**Step 3: No commit needed** (data/ is in .gitignore)

---

## Task 5: Setup Node.js Dependencies (WebSocket Server)

**Files:**
- Already present: `web_avatar/package.json`
- Already present: `web_avatar/server.js`

**Step 1: Install Node dependencies at root**

```bash
npm install
```

Expected: node_modules/ created at root with ws package

**Step 2: Install Node dependencies in web_avatar**

```bash
cd web_avatar && npm install && cd ..
```

Expected: web_avatar/node_modules/ with React, Vite, Three.js, @pixiv/three-vrm

**Step 3: Verify Node version**

```bash
node --version
```

Expected: v18.x or higher

**Step 4: No commit needed** (node_modules/ is in .gitignore)

---

## Task 6: Test Ollama Connectivity

**Files:**
- Create: `tests/test_ollama_connectivity.py`

**Step 1: Write test for Ollama connection**

```python
"""Test Ollama connectivity with API key."""
import pytest
import asyncio
import os
from agent.llm.client import LLMClient
from agent.config import OLLAMA_HOST, OLLAMA_API_KEY, LLM_MODEL

@pytest.mark.asyncio
async def test_ollama_api_connectivity():
    """Verify we can connect to Ollama API with provided key."""
    if not OLLAMA_API_KEY:
        pytest.skip("No OLLAMA_API_KEY in .env")
    
    client = LLMClient(model=LLM_MODEL, base_url=OLLAMA_HOST)
    try:
        # Simple test message
        result = await client.get_intent(
            user_message="Hello, are you working?",
            history=[],
            state={"mood": "neutral"},
            context=None,
            tools=None
        )
        assert "intent" in result
        assert result["intent"] in ["speak", "use_tool", "ask_clarification"]
        print(f"✓ Ollama responded: {result}")
    finally:
        await client.close()

@pytest.mark.asyncio
async def test_ollama_tool_recognition():
    """Verify LLM can recognize tool-use intent."""
    if not OLLAMA_API_KEY:
        pytest.skip("No OLLAMA_API_KEY in .env")
    
    client = LLMClient(model=LLM_MODEL, base_url=OLLAMA_HOST)
    try:
        # Ask something that should trigger tool use
        result = await client.get_intent(
            user_message="What's the weather in Lisbon?",
            history=[],
            state={"mood": "neutral"},
            context=None,
            tools=[
                {
                    "name": "weather",
                    "description": "Get weather for a location"
                }
            ]
        )
        assert "intent" in result
        print(f"✓ LLM intent: {result['intent']}")
    finally:
        await client.close()
```

**Step 2: Run test to verify connectivity**

```bash
source .venv/bin/activate  # Ensure venv is active
pytest tests/test_ollama_connectivity.py -v -s
```

Expected: PASS (both tests should pass if API key is valid)

**Step 3: If test fails, diagnose**

Common issues:
- Invalid API key → check `.env` has correct key
- Wrong OLLAMA_HOST → should be `https://api.ollama.ai` or local `http://localhost:11434`
- Model not available → check LLM_MODEL matches available models on service
- Network issue → verify internet connectivity

**Step 4: Commit**

```bash
git add tests/test_ollama_connectivity.py
git commit -m "test: add Ollama connectivity verification tests"
```

---

## Task 7: Create Quick Start Script

**Files:**
- Create: `start_dev.sh` (Linux/Mac)
- Create: `start_dev.bat` (Windows)

**Step 1: Create start_dev.sh**

```bash
#!/bin/bash
set -e

echo "🚀 Mimi Dev Environment Startup"
echo "================================"

# Activate Python venv
if [ ! -d ".venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv .venv
fi

echo "✓ Activating Python venv..."
source .venv/bin/activate

# Check Ollama connectivity
echo "🔗 Testing Ollama connectivity..."
python -c "
import asyncio
from agent.llm.client import LLMClient
from agent.config import OLLAMA_HOST, OLLAMA_API_KEY, LLM_MODEL

async def test():
    client = LLMClient()
    try:
        result = await client.get_intent(
            user_message='Hi',
            history=[],
            state={'mood': 'neutral'}
        )
        print('✓ Ollama connected!')
    except Exception as e:
        print(f'✗ Ollama error: {e}')
    finally:
        await client.close()

asyncio.run(test())
" || echo "⚠️  Ollama test failed - check OLLAMA_HOST and API_KEY in .env"

echo ""
echo "📝 Next steps:"
echo "  1. Terminal 1: cd web_avatar && node server.js"
echo "  2. Terminal 2: python agent/main.py"
echo "  3. Terminal 3: cd web_avatar && npm run dev"
echo ""
echo "🌐 Open: http://localhost:5173"
```

**Step 2: Create start_dev.bat (Windows)**

```batch
@echo off
echo 🚀 Mimi Dev Environment Startup
echo ================================

if not exist ".venv" (
    echo 📦 Creating Python virtual environment...
    python -m venv .venv
)

echo ✓ Activating Python venv...
call .venv\Scripts\activate.bat

echo 🔗 Testing Ollama connectivity...
python -c "import asyncio; from agent.llm.client import LLMClient; asyncio.run(LLMClient().get_intent('Hi', [], {'mood': 'neutral'}))" || echo ⚠️  Ollama test failed

echo.
echo 📝 Next steps:
echo   1. Terminal 1: cd web_avatar ^&^& node server.js
echo   2. Terminal 2: python agent/main.py
echo   3. Terminal 3: cd web_avatar ^&^& npm run dev
echo.
echo 🌐 Open: http://localhost:5173
```

**Step 3: Make scripts executable**

On Linux/Mac:
```bash
chmod +x start_dev.sh
```

**Step 4: Commit**

```bash
git add start_dev.sh start_dev.bat
git commit -m "chore: add quick start scripts for dev environment"
```

---

## Task 8: Update README with Setup Instructions

**Files:**
- Modify: `README.md`

**Step 1: Add setup section after 🚀 Início rápido**

Insert after line 31:

```markdown
## ⚙️ Setup Completo (Primeiro Uso)

### Pré-requisitos
- Python 3.10+
- Node.js 18+
- API key Ollama (fornecida)

### 1. Configuração de Ambiente

```bash
# Clone e entre no diretório
git clone <repo-url>
cd Mimi

# Crie arquivo .env com credenciais
cp .env.example .env
# Edite .env e adicione: OLLAMA_API_KEY=<sua_chave>
```

### 2. Setup Python

```bash
# Crie venv e instale dependências
python3 -m venv .venv
source .venv/bin/activate  # ou .venv\Scripts\activate no Windows

# Instale dependências
pip install -r requirements.txt

# Opcional: instale voz e TTS
pip install sounddevice webrtcvad faster-whisper piper-tts
```

### 3. Setup Node.js

```bash
# Instale dependências do servidor WebSocket
npm install

# Instale dependências do frontend
cd web_avatar && npm install && cd ..
```

### 4. Teste Conectividade Ollama

```bash
pytest tests/test_ollama_connectivity.py -v
```

Expected: ✓ Todos os testes passam

### 5. Inicie o Sistema

Abra **3 terminais** no diretório raiz:

**Terminal 1 - WebSocket Server:**
```bash
cd web_avatar && node server.js
```
Esperado: `WebSocket/HTTP server rodando em ws://localhost:8765`

**Terminal 2 - Agent Python:**
```bash
source .venv/bin/activate
python agent/main.py
```
Esperado: `Conectando ao backend em ws://localhost:8765...`

**Terminal 3 - React Frontend:**
```bash
cd web_avatar && npm run dev
```
Esperado: `Local: http://localhost:5173/`

### 6. Acesse a Interface

- **Web**: http://localhost:5173
- **OBS Stream**: http://localhost:5173/obs.html
- **Chat**: Digite mensagens ou use microfone (após implementar STT)
```

**Step 2: Verify README renders correctly**

```bash
cat README.md | head -100
```

**Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add comprehensive setup instructions"
```

---

## Task 9: Create Docker Setup (Optional, for Easy Deploy)

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`

**Step 1: Create Dockerfile**

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install Node.js
RUN apt-get update && apt-get install -y nodejs npm && rm -rf /var/lib/apt/lists/*

# Copy files
COPY requirements.txt pyproject.toml ./
COPY agent/ ./agent/
COPY web_avatar/ ./web_avatar/

# Setup Python
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip && pip install -r requirements.txt

# Setup Node.js
RUN npm install && cd web_avatar && npm install && cd ..

# Expose ports
EXPOSE 8765 5173

# Start all services
CMD ["sh", "-c", "node web_avatar/server.js & python agent/main.py & cd web_avatar && npm run dev"]
```

**Step 2: Create docker-compose.yml**

```yaml
version: '3.8'

services:
  mimi:
    build: .
    ports:
      - "8765:8765"  # WebSocket server
      - "5173:5173"  # Frontend
    environment:
      - OLLAMA_HOST=${OLLAMA_HOST}
      - OLLAMA_API_KEY=${OLLAMA_API_KEY}
      - LLM_MODEL=${LLM_MODEL}
      - WEBSOCKET_HOST=0.0.0.0
    volumes:
      - ./data:/app/data

  # Optional: Ollama service (if running locally)
  # ollama:
  #   image: ollama/ollama:latest
  #   ports:
  #     - "11434:11434"
```

**Step 3: Document Docker usage in README**

Add to README:

```markdown
## 🐳 Docker Setup (Alternativo)

```bash
docker-compose up
```

Acessar em: http://localhost:5173
```

**Step 4: Commit**

```bash
git add Dockerfile docker-compose.yml
git commit -m "chore: add Docker setup for easy deployment"
```

---

## Summary

| Task | Purpose | Time | Status |
|------|---------|------|--------|
| 1 | Environment config (.env) | 5 min |📋 Ready |
| 2 | LLM client API key support | 10 min | 📋 Ready |
| 3 | Python venv + dependencies | 10 min | 📋 Ready |
| 4 | Persona JSON | 5 min | 📋 Ready |
| 5 | Node.js setup | 5 min | 📋 Ready |
| 6 | Ollama connectivity tests | 10 min | 📋 Ready |
| 7 | Quick start scripts | 10 min | 📋 Ready |
| 8 | README setup docs | 10 min | 📋 Ready |
| 9 | Docker setup | 15 min | ⭐ Optional |

**Total estimated time:** ~80 minutes (or ~60 min without Docker)

---

## Execution Notes

- **API Key:** Use provided `7d5fefd71866442f848242162671602e.BscZ3cc5eQc6cx9d6-yhXhiC`
- **Ollama Host:** Default is `https://api.ollama.ai` (remote) or `http://localhost:11434` (local)
- **Model:** Default `phi3:mini` — adjust in `.env` if needed
- **Testing:** Always run Task 6 tests to verify connectivity before starting services
- **Troubleshooting:** Check logs in each terminal for clear error messages
