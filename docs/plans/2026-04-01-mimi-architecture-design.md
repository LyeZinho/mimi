# Mimi — Architecture Design
**Date:** 2026-04-01  
**Status:** Approved

---

## Context

Redesign from scratch. The previous implementation grew too complex too fast:
- 7 brains including Avatar/3D control (premature)
- Distributed-leaning architecture
- Docker wrapping the agent itself
- Too much abstraction before validated fundamentals

**Guiding principles for this version:**
1. Docker = infrastructure only (Redis). Agent runs directly in Python.
2. Focus on core brains: input / output / reasoning / sentiment / action / interaction. No 3D.
3. Modular monolithic > distributed. Clear steps, well-organized, but not fully monolithic.
4. Web panel = raw information display only. Zero control.
5. Robust non-LLM logic. LLMs only for text generation. Max 2 LLM-using brains.

---

## 1. Architecture Overview

### Core: FSM + Brain Registry

The agent has a central `AgentFSM` with 5 deterministic states. Transitions are rule-based (zero LLM). For each state, the `BrainRegistry` defines which brains execute in sequence via a configurable pipeline.

```
idle ──────────────► listening ──────────► processing ──────────► speaking
  ▲                      │                     │                      │
  │                      │ (vad off)            │ (error)              │
  └──────────────────────┴─────────────────────► error ◄──────────────┘
                                                         └──► idle (recover)
```

### States

| State | Trigger | Active Brains |
|-------|---------|--------------|
| `idle` | startup / after speaking | none |
| `listening` | VAD speech start | InputBrain |
| `processing` | VAD speech end + transcript ready | SentimentBrain → InteractionBrain(read) → ReasoningBrain → ActionBrain → InteractionBrain(write) |
| `speaking` | ResponsePlan ready | OutputBrain |
| `error` | any brain exception | recovery logic → idle |

---

## 2. Brains

**Only 2 brains call the LLM:**

| Brain | Responsibility | LLM? | Notes |
|-------|---------------|------|-------|
| `InputBrain` | VAD + STT (faster-whisper) | ❌ | sounddevice + webrtcvad |
| `SentimentBrain` | User tone/emotion analysis | ✅ Small call | Punctual, small model prompt |
| `ReasoningBrain` | Generate response text | ✅ Main call | Full Ollama inference |
| `ActionBrain` | Intent routing + tool dispatch | ❌ | Rule-based only |
| `InteractionBrain` | Memory read/write | ❌ | Redis + SQLite client |
| `OutputBrain` | TTS synthesis | ❌ | Piper TTS |

### Pipeline Configuration (pipeline.yaml)

```yaml
states:
  idle:
    pipeline: []
  listening:
    pipeline: [input]
  processing:
    pipeline: [sentiment, interaction_read, reasoning, action, interaction_write]
  speaking:
    pipeline: [output]
  error:
    pipeline: []
```

---

## 3. Data Flow

### Full Turn Flow

```
MIC ──► [InputBrain] ──► TranscriptEvent
                               │
                       [SentimentBrain] ──► SentimentResult (LLM #1)
                               │
                       [InteractionBrain.read] ──► MemoryContext (Redis + SQLite)
                               │
                       [ReasoningBrain] ──► ResponsePlan (LLM #2, main)
                               │
                       [ActionBrain] ──► ActionPlan (rule-based)
                               │
                       [InteractionBrain.write] ──► saves to Redis + SQLite
                               │
                       [OutputBrain] ──► TTS audio ──► SPEAKERS
```

### Core Schemas (Pydantic v2)

```python
class TranscriptEvent(BaseModel):
    text: str
    confidence: float
    timestamp: datetime

class SentimentResult(BaseModel):
    emotion: Literal["neutral", "happy", "sad", "angry", "surprised", "curious"]
    intensity: float  # 0.0–1.0

class AgentContext(BaseModel):
    transcript: TranscriptEvent
    sentiment: SentimentResult
    memory: list[MemoryEntry]
    session_id: str

class ResponsePlan(BaseModel):
    text: str
    action: Literal["speak", "speak+tool", "silence"]
    tool_calls: list[ToolCall] = []

class AgentState(BaseModel):  # emitted to dashboard
    fsm_state: str
    active_brain: str
    last_emotion: str
    last_transcript: str
    latency_ms: int
```

---

## 4. Memory

- **Short-term (Redis):** Current session context (last N turns), active state. Ephemeral by design.
- **Long-term (SQLite):** Persistent conversation history, persona data. Local file (no container needed for the DB itself).
- **Docker:** Used only to run Redis reliably. SQLite is a plain file.

---

## 5. Dashboard (Monitoring Only)

FastAPI + WebSocket server. Emits `AgentState` on every FSM transition.  
**No control surface.** Read-only view of:
- Current FSM state
- Active brain
- Last transcript
- Last detected emotion
- Per-brain latency (ms)
- Error log

Frontend: minimal HTML or lightweight React. No framework overkill.

---

## 6. Project Structure

```
mimi/
├── agent/
│   ├── fsm/
│   │   ├── states.py              # State enum + valid transitions
│   │   └── agent_fsm.py           # FSM core (asyncio)
│   ├── brains/
│   │   ├── base.py                # BrainBase + BrainRegistry
│   │   ├── input_brain.py         # VAD + STT (faster-whisper)
│   │   ├── sentiment_brain.py     # LLM sentiment (small call)
│   │   ├── reasoning_brain.py     # LLM response generation
│   │   ├── action_brain.py        # Rule-based intent routing
│   │   ├── interaction_brain.py   # Memory read/write (Redis + SQLite)
│   │   └── output_brain.py        # TTS (Piper)
│   ├── memory/
│   │   ├── short_term.py          # Redis async client
│   │   └── long_term.py           # SQLite async client (aiosqlite)
│   ├── llm/
│   │   └── ollama_client.py       # Ollama remote async wrapper
│   ├── config.py                  # Pydantic Settings
│   └── main.py                    # Entrypoint (asyncio.run)
├── dashboard/
│   ├── server.py                  # FastAPI + WebSocket
│   └── static/                    # Minimal frontend (HTML/JS)
├── docker/
│   └── docker-compose.yml         # Redis only
├── config/
│   └── pipeline.yaml              # Brain pipeline per FSM state
├── tests/
│   ├── unit/
│   └── integration/
├── docs/
│   └── plans/
├── pyproject.toml
└── .env.example
```

---

## 7. Tech Stack

| Layer | Choice | Reason |
|-------|--------|--------|
| Runtime | Python 3.11 + asyncio | Async-native, well-supported |
| STT | faster-whisper | Local, fast, accurate |
| VAD | webrtcvad | Lightweight, battle-tested |
| Audio I/O | sounddevice | Cross-platform |
| LLM | Ollama (remote) | Flexible model swap |
| TTS | Piper TTS | Local, fast, lightweight |
| Short-term memory | Redis (Docker) | Fast, ephemeral by design |
| Long-term memory | SQLite + aiosqlite | Zero infra, persistent |
| Schema validation | Pydantic v2 | Type-safe, fast |
| Dashboard | FastAPI + WebSocket | Lightweight, async |
| Config | YAML + pydantic-settings | Declarative + validated |
| Testing | pytest + pytest-asyncio | Standard |

---

## 8. Implementation Phases

### Phase 1 — Core Pipeline (text only, no audio)
- `pyproject.toml` + project structure
- `AgentFSM` + `BrainRegistry` + `BrainBase`
- `OllamaClient` (async wrapper)
- `ReasoningBrain` + Pydantic schemas
- `InteractionBrain` + Redis client
- End-to-end text pipeline testable in terminal

**Done when:** `python -m agent` accepts text input, reasons via Ollama, stores to Redis, returns response.

### Phase 2 — Voice In/Out
- `InputBrain` (sounddevice + webrtcvad + faster-whisper)
- `OutputBrain` (Piper TTS)
- `SentimentBrain` (small LLM call)
- Full voice pipeline: mic → whisper → LLM → TTS → speakers

**Done when:** Agent hears a question via microphone and responds with voice.

### Phase 3 — Memory + Dashboard
- SQLite long-term memory (aiosqlite)
- Docker Compose for Redis
- FastAPI dashboard (WebSocket, monitoring-only)
- `ActionBrain` (rule-based intent routing)

**Done when:** Dashboard shows live state; conversation persists across sessions.

### Phase 4 — Polish
- `pipeline.yaml` configuration
- Integration tests
- Observability: per-brain latency, health checks
- `.env.example` + docs

---

## Non-Goals (this version)

- 3D avatar / VRM control
- Multiple simultaneous users
- Distributed processes (separate process per brain)
- Cloud-hosted inference (LLM stays on remote Ollama)
- Fine-tuned models
- Voice cloning

These are explicitly deferred. The architecture does not need to support them now.

---

## Success Criteria

- [ ] Voice in → voice out < 500ms latency target
- [ ] FSM state visible in dashboard (real-time)
- [ ] Conversation history persists across restarts (SQLite)
- [ ] Adding a new brain requires editing only `pipeline.yaml` + a new brain class
- [ ] Zero `as any` / type suppressions / broad exception catches
