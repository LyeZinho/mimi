# 🏗️ Estrutura Completa do Projeto Mimi

**Data**: 27 de Março de 2026  
**Status**: Documentação Atualizada  
**Última Modificação**: Estrutura completa catalogada e documentada

---

## 📊 Visão Geral do Projeto

**Mimi** é um agente de IA interativo multimodal com:
- Backend Python com 7 brains autônomos (Input, Reasoning, Planning, Execution, Sentiment, Avatar, Output)
- Frontend React com Three.js + VRM para avatar 3D
- WebSocket middleware Node.js para comunicação em tempo real
- Integração com OBS Studio para streaming

| Métrica | Valor |
|---------|-------|
| **LOC Python** | ~5.200 linhas |
| **LOC React/JS** | ~2.800 linhas |
| **Componentes React** | 10+ componentes |
| **Brains Python** | 7 (cada um autônomo) |
| **Testes** | 30+ testes unitários |
| **Dependências Python** | 10+ principais |
| **Dependências Node** | 8 principais |

---

## 📁 Estrutura de Diretórios

```
mimi/
├── agent/                          # Backend Python (5.2K LOC)
│   ├── __init__.py
│   ├── config.py                  # Configuração centralizada
│   ├── main.py                    # Entry point daemon
│   ├── orchestrator.py            # Orquestrador de brains
│   ├── brain_config.py            # Config de brains
│   │
│   ├── core/                       # Agent Core (núcleo)
│   │   ├── agent.py              # Classe AgentCore
│   │   ├── state.py              # AgentState (mood, context)
│   │   ├── memory.py             # Memória (curta/longa prazo)
│   │   ├── event_bus.py          # Event Bus (pub/sub async)
│   │   └── messaging/            # Message types e handlers
│   │
│   ├── brains/                     # Os 7 Brains Autônomos
│   │   ├── input_brain.py        # 🎙️ VAD + STT
│   │   ├── reasoning_brain.py    # 🧠 LLM Inference
│   │   ├── planning_brain.py     # 📋 Action Planning
│   │   ├── execution_brain.py    # ⚙️ Tool Execution
│   │   ├── sentiment_brain.py    # 💭 Emotion Detection
│   │   ├── avatar_brain.py       # 🎭 Avatar Control
│   │   ├── output_brain.py       # 🔊 TTS + Streaming
│   │   └── browser_brain.py      # 🌐 Browser Automation (FUTURE)
│   │
│   ├── llm/                        # LLM Integration
│   │   ├── client.py             # Client Ollama/OpenAI
│   │   ├── prompts.py            # Prompt templates
│   │   └── streaming.py          # Streaming responses
│   │
│   ├── input/                      # Input Managers
│   │   ├── text_input.py         # Text input handler
│   │   ├── voice_input.py        # Voice/STT handler
│   │   └── utils.py
│   │
│   ├── output/                     # Output/Action System
│   │   ├── actions.py            # ActionRouter dispatcher
│   │   ├── tts.py                # TTS engines
│   │   └── tools.py              # Tool wrappers
│   │
│   ├── tools/                      # Tool Registry
│   │   ├── registry.py           # Tool registry + discovery
│   │   ├── search_tool.py        # DuckDuckGo search
│   │   ├── weather_tool.py       # Weather info
│   │   └── __init__.py
│   │
│   ├── avatar/                     # Avatar Interface
│   │   ├── interface.py          # WebAvatar class
│   │   ├── dummy.py              # DummyAvatar (testing)
│   │   └── connection.py         # WebSocket connection
│   │
│   ├── audio/                      # Audio Processing
│   │   ├── buffer.py             # RingBuffer + ChunkQueue
│   │   ├── vad.py                # Voice Activity Detection
│   │   └── processor.py          # Audio processing
│   │
│   ├── buffers/                    # Buffer Management
│   │   ├── ring_buffer.py        # Ring buffer (3s history)
│   │   ├── chunk_queue.py        # FIFO chunk queue
│   │   └── manager.py            # BufferManager coordinator
│   │
│   ├── ml/                         # ML Models
│   │   ├── emotion.py            # Emotion detection models
│   │   └── intent.py             # Intent classification
│   │
│   └── browser/                    # Browser Control (FUTURE PHASE 2)
│       ├── __init__.py
│       ├── command_tracker.py    # Audit trail for commands
│       └── browser_controller.py # Puppeteer integration (TODO)
│
├── web_avatar/                     # Frontend React (2.8K LOC)
│   ├── server.js                   # Node.js WebSocket server (484 LOC)
│   ├── index.html                  # Entry HTML
│   ├── obs.html                    # OBS streaming page
│   ├── mirror.html                 # Mirror stream endpoint (inline)
│   ├── vite.config.js              # Vite configuration
│   ├── package.json                # npm dependencies
│   │
│   ├── src/
│   │   ├── main.jsx               # React entry point
│   │   ├── App.jsx                # Main App component
│   │   ├── obs.jsx                # OBS page component
│   │   │
│   │   ├── components/            # React Components (~1200 LOC)
│   │   │   ├── AvatarCanvas.jsx      # Three.js + VRM rendering
│   │   │   ├── DebugPanel.jsx        # Multimodal debug display
│   │   │   ├── ChatInterface.jsx     # Chat input/output
│   │   │   ├── ExpressionControls.jsx # Expression buttons
│   │   │   ├── AnimationControls.jsx  # Animation controls
│   │   │   ├── ModelUpload.jsx        # VRM/FBX upload
│   │   │   ├── WebSocketStatus.jsx    # Connection status
│   │   │   ├── ModelStatusCard.jsx    # Agent metrics (PHASE 1)
│   │   │   ├── FilterBar.jsx          # Debug filters (PHASE 1)
│   │   │   ├── LatencyChart.jsx       # Latency graph (PHASE 1)
│   │   │   └── SummaryStats.jsx       # Summary stats (PHASE 1)
│   │   │
│   │   ├── logic/                 # Business Logic (~600 LOC)
│   │   │   ├── WebSocketClient.js    # WebSocket wrapper
│   │   │   ├── AvatarViewer.js       # Avatar 3D viewer
│   │   │   ├── AvatarStateManager.js # Avatar state machine
│   │   │   ├── AnimationManager.js   # Animation playback
│   │   │   ├── ExpressionController.js # Expression control
│   │   │   ├── PosePlayer.js         # Pose animation
│   │   │   └── __tests__/            # Unit tests
│   │   │
│   │   ├── __tests__/             # Integration tests
│   │   │   ├── integration.test.js
│   │   │   ├── backward-compat.test.js
│   │   │   └── components/**/*.test.jsx
│   │   │
│   │   └── styles/                # CSS/styling
│   │       └── index.css
│   │
│   ├── public/                     # Static assets
│   │   ├── models/                # VRM models (Mimi.vrm)
│   │   └── animations/            # Animation files
│   │
│   └── node_modules/              # npm packages (excluded from git)
│
├── tests/                          # Test Suite (~500 LOC)
│   ├── test_ollama_connectivity.py   # Ollama integration test
│   ├── agent/
│   │   ├── avatar/                   # Avatar tests
│   │   ├── core/                     # Core agent tests
│   │   ├── output/                   # Output/action tests
│   │   └── __init__.py
│   ├── integration/
│   │   └── test_full_flow.py        # End-to-end tests
│   └── __init__.py
│
├── docs/                           # Documentation
│   ├── INDEX.md                    # Documentation hub
│   ├── ARCHITECTURE.md             # Architecture overview
│   ├── STATUS.md                   # Current status
│   ├── project.md                  # Project info
│   ├── MULTI_BRAIN_GUIDE.md        # 7-brain system guide
│   │
│   ├── plans/                      # Implementation Plans
│   │   ├── 2026-03-27-browser-control-debug-panel-design.md
│   │   ├── 2026-03-27-browser-control-debug-panel-implementation.md ← CURRENT PLAN
│   │   ├── 2026-03-26-mirror-llm-control-design.md
│   │   └── 2026-03-26-ollama-setup.md
│   │
│   ├── avatar_architecture/        # Avatar architecture docs
│   │   ├── overview.md
│   │   ├── layers.md
│   │   ├── best_practices.md
│   │   ├── technologies.md
│   │   └── project_organization.md
│   │
│   ├── guides/                      # Setup guides
│   │   ├── QUICK_START.md
│   │   ├── DOCKER_DEV_SETUP.md
│   │   ├── OBS_SETUP.md
│   │   └── FISH_SHELL_SETUP.md
│   │
│   └── reference/                   # API Reference
│       ├── MIRROR_AND_CONTROL.md
│       ├── SYNC_GUIDE.md
│       ├── TOOLS.md
│       └── walkthrough.md
│
├── examples/                        # Example scripts
│   ├── test_avatar.py              # Test avatar commands
│   └── demo_web_avatar.py          # Web avatar demo
│
├── scripts/                         # Utility scripts
│   ├── start_dev.sh                # Linux/Mac start
│   └── start.bat                   # Windows start
│
├── docker/                          # Docker configuration
│   └── Dockerfile                  # Container config
│
├── data/                            # Data directory (runtime)
│   ├── memory.db                   # SQLite memory database
│   └── persona.json                # Agent persona
│
├── htmlcov/                         # Coverage reports
├── .pytest_cache/                   # Pytest cache
├── .sisyphus/                       # Sisyphus AI config
│   └── plans/                       # AI-generated plans
│
├── .env.example                     # Environment template
├── .env                             # Environment (not committed)
├── .gitignore                       # Git ignore rules
├── README.md                        # Main project README
├── requirements.txt                 # Python dependencies
├── package-lock.json                # npm lock
└── pytest.ini                       # Pytest config
```

---

## 🧠 Os 7 Brains Autônomos

Cada brain é independente, se comunica via Event Bus, e processa dados em paralelo:

| Brain | Função | Entrada | Saída | LLM? |
|-------|--------|---------|-------|------|
| **Input** | Captura áudio, VAD, STT | Microfone | Texto transcrito | Não |
| **Reasoning** | Inferência LLM | Texto | Resposta streaming | **Sim** |
| **Planning** | Schema de ações | Intent | Lista de ações | Não |
| **Execution** | Dispatcher de ferramentas | Ações | Resultados | Não |
| **Sentiment** | Detecção de emoção | Texto | Emoção (lexical) | Não |
| **Avatar** | Controle 3D + animações | Emoção | Animações VRM | Não |
| **Output** | TTS + streaming audio | Texto | Áudio stream | Não |

**Arquitetura Event Bus:**
```
Input Brain → "TRANSCRIPTION_COMPLETE" → Event Bus
                                            ↓
                        Reasoning Brain (LLM)
                        Sentiment Brain (Emotion)
                        Avatar Brain (animate)
                                            ↓
                        "INTENT_DETECTED" → Planning Brain
                                            ↓
                        "TOOLS_QUEUED" → Execution Brain
                                            ↓
                        "TOOL_RESULT" → Output Brain (TTS)
```

---

## 🔌 Dependências Principais

### Python (`requirements.txt`)

| Dependência | Versão | Uso |
|-------------|--------|-----|
| `pydantic` | >=2.0 | Validação de dados |
| `httpx` | >=0.25 | HTTP async client |
| `websockets` | >=12.0 | WebSocket (agent → server) |
| `aiohttp` | >=3.9.0 | HTTP server + async |
| `duckduckgo-search` | >=5.0.0 | Search tool |
| `python-dotenv` | >=1.0.0 | .env configuration |
| `pytest` | >=7.0 | Testing framework |
| `pytest-asyncio` | >=0.21 | Async test support |

**Opcionais (comentados):**
- `sounddevice` - Audio capture
- `webrtcvad` - Voice activity detection
- `faster-whisper` - STT local
- `piper-tts` - TTS local
- `coqui-tts` - TTS alternativo

### Node.js (`web_avatar/package.json`)

| Dependência | Versão | Uso |
|-------------|--------|-----|
| `react` | ^18.0.0 | UI framework |
| `react-dom` | ^18.0.0 | React rendering |
| `three` | ^0.164.1 | 3D graphics |
| `@pixiv/three-vrm` | ^2.1.0 | VRM model loading |
| `ws` | ^8.19.0 | WebSocket server |
| `lil-gui` | ^0.21.0 | Debug GUI |
| `recharts` | ^3.8.1 | Charting library |
| `simple-peer` | ^9.11.0 | P2P communication |

**DevDependencies:**
- `vite` - Build tool (replaces webpack)
- `vitest` - Test framework (Vite-native)
- `@vitejs/plugin-react` - React support
- `@vitest/ui` - Test UI

---

## 🔄 Fluxo de Comunicação

### Scenario: Usuário faz pergunta via chat

```
1. Web UI (React)
   ↓ (WebSocket: "text_input")
2. Node.js Server (server.js)
   ↓ (relays to)
3. Python Agent (main.py)
   ↓ (receives on WebAvatar.listen_loop)
4. Agent Core → Input Brain
   ↓ (event: TRANSCRIPTION_COMPLETE)
5. Event Bus (broadcasts)
   ├→ Reasoning Brain (LLM inference) 
   ├→ Sentiment Brain (detect emotion)
   └→ Avatar Brain (animate thinking)
   ↓
6. Planning Brain (plan actions)
   ↓ (event: TOOLS_QUEUED)
7. Execution Brain (run tools in parallel)
   ↓ (event: TOOL_RESULT)
8. Output Brain (generate TTS)
   ↓ (WebSocket: "avatar_control")
9. Node.js Server (broadcasts)
   ↓
10. Web UI (React)
    ├ Play TTS audio
    ├ Update avatar emotion
    ├ Play animation
    └ Display response
```

### WebSocket Message Types

**Frontend → Backend:**
```json
{ "type": "text_input", "message": "Olá Mimi!" }
{ "type": "voice_input", "data": "base64_audio" }
{ "type": "control", "action": "happy" }
```

**Backend → Frontend:**
```json
{ "type": "avatar_control", "emotion": "happy", "speak": true, "animation": "wave" }
{ "type": "state", "state": { "mood": "thinking", "speaking": true } }
{ "type": "agent_status", "latency": 245, "tokens": 150 }
{ "type": "browser_command_result", "action": "navigate", "success": true }
```

---

## 📊 Arquitetura de Componentes React

```
App.jsx (main component)
├── AvatarCanvas
│   ├── Three.js scene
│   ├── VRM model loader
│   ├── Camera controller (orbit, zoom, pan)
│   └── Animation playback
│
├── ChatInterface
│   ├── Message history
│   ├── Text input
│   └── Speech input (STT)
│
├── DebugPanel (NEW - Phase 1)
│   ├── ModelStatusCard (emotion, tokens, latency)
│   ├── FilterBar (status + text filters)
│   ├── LatencyChart (history graph)
│   ├── SummaryStats (active, avg latency, tokens)
│   └── Original debug info (action, speaking, animation)
│
├── ExpressionControls
│   ├── Button: happy, sad, angry, surprised, etc.
│   └── WebSocket send
│
├── AnimationControls
│   ├── Play/pause animations
│   └── Speed control
│
├── ModelUpload
│   ├── File input
│   ├── Drag-drop zone
│   └── Model selector dropdown
│
├── WebSocketStatus
│   └── Connection indicator
│
└── BrowserPanel (FUTURE - Phase 4)
    ├── Screenshot display
    ├── Command history
    └── Navigation controls
```

---

## 🚀 Fases de Desenvolvimento

### ✅ Fase 0: MVP Completo (CONCLUÍDA)
- Web avatar com Three.js + VRM
- WebSocket communication
- Chat interface
- OBS integration
- 7-brain architecture em Python

### 🔄 Fase 1: Enhanced Debug Panel (EM PLANEJAMENTO)
**Tasks:** 1-8  
**Status:** Documentação completa em `docs/plans/2026-03-27-browser-control-debug-panel-implementation.md`

- ModelStatusCard component
- FilterBar component
- LatencyChart component
- SummaryStats component
- Integration into DebugPanel
- agent_status message type
- Latency/token tracking

**Expected Output:**
- Real-time metrics display
- Filter by status (active/idle/error)
- Search by text
- Latency history graphs

### 🔮 Fase 2: Browser Control Layer (PLANEJAMENTO)
**Tasks:** 9-13  
**Status:** Specification completo em implementation plan

- Puppeteer integration
- BrowserController class
- Command handlers (navigate, click, type, screenshot, etc.)
- Browser command audit trail
- 30s timeouts

**Tech:** Node.js Puppeteer, Chrome CDP

### 🎨 Fase 3: BrowserBrain LLM Autonomy (PLANEJAMENTO)
**Tasks:** 14-17

- BrowserBrain class (LLM-driven decisions)
- Integration into ActionRouter
- Autonomous browser actions
- Search capability

**Tech:** Python async, LLM prompting

### 📊 Fase 4: Real-Time Dashboard (PLANEJAMENTO)
**Tasks:** 18-20

- BrowserPanel React component
- Live screenshot display
- Command history audit trail
- Real-time visualization

---

## 🧪 Testes

### Python Tests
```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_ollama_connectivity.py -v

# Run with coverage
pytest --cov=agent tests/
```

### React/JS Tests
```bash
# Run tests
cd web_avatar
npm test

# Run with UI
npm run test:ui
```

### Integration Tests
```bash
# Run end-to-end tests
pytest tests/integration/test_full_flow.py -v
```

---

## 🔐 Configuração (.env)

```env
# LLM
OLLAMA_HOST=https://api.ollama.ai
OLLAMA_API_KEY=<provided-by-user>
LLM_MODEL=phi3:mini

# Avatar
AVATAR_TYPE=web
WEBSOCKET_HOST=localhost
WEBSOCKET_PORT=8765

# Database
DB_PATH=data/memory.db
PERSONA_PATH=data/persona.json

# Frontend
VITE_WS_URL=ws://localhost:8765
```

---

## 📈 Performance & Metrics

| Métrica | Target | Current |
|---------|--------|---------|
| **STT Latency** | <500ms | ~300-400ms |
| **LLM Response** | <2s | ~1-3s (streaming) |
| **Avatar FPS** | 60 | 60 |
| **Mirror Stream FPS** | 10 | 10 |
| **Frame Size** | <200KB | ~80-150KB |
| **Total Latency** | <3s | ~2-4s |

---

## 🔧 Development Workflow

### Adding a New Component
1. Create component in `web_avatar/src/components/`
2. Write tests in `__tests__/` subdirectory (TDD)
3. Import in `App.jsx`
4. Test WebSocket integration

### Adding a New Tool
1. Create tool class in `agent/tools/`
2. Register in `ToolRegistry.register()`
3. Add event handlers in ActionRouter
4. Test with `pytest tests/agent/output/`

### Adding a New Brain
1. Create brain class in `agent/brains/`
2. Implement `async run(state, event)` method
3. Subscribe to Event Bus with `@bus.subscribe(EventType.X)`
4. Add to `agent/orchestrator.py`

---

## 📚 Documentação Relacionada

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Detalhes arquitetura 7-brains
- **[MULTI_BRAIN_GUIDE.md](MULTI_BRAIN_GUIDE.md)** - Guia dos 7 brains
- **[plans/2026-03-27-browser-control-debug-panel-implementation.md](plans/2026-03-27-browser-control-debug-panel-implementation.md)** - Plano Phase 1 detalhado

---

## 🔗 Links Rápidos

| Recurso | URL |
|---------|-----|
| **Web Interface** | http://localhost:5173 |
| **OBS Stream** | http://localhost:5173/obs.html |
| **Mirror Stream** | http://localhost:8765/mirror.html |
| **WebSocket** | ws://localhost:8765 |

---

## 📝 Histórico de Mudanças

- **27 Mar 2026** - Estrutura completa catalogada e documentação atualizada
- **26 Mar 2026** - Design do Mirror + LLM Control aprovado
- **25 Mar 2026** - Sistema web avatar completo e testado

---

**Mantido por:** Sistema de Documentação Sisyphus  
**Última Atualização:** 27 de Março de 2026
