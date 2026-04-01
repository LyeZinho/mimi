# Mimi v2 — Global TODO

> Voice AI agent: mic → VAD → Whisper STT → Ollama LLM → Piper TTS → speakers  
> Architecture: FSM-driven brain pipeline · Redis (short-term) + SQLite (long-term) · Monitoring-only dashboard  
> Rule: Docker = infra only (Redis). Agent runs directly in Python. Max 2 LLM-calling brains.

---

## Phase 1 — Core Pipeline (text only, no audio)

- [x] **Task 1** — Project setup (`pyproject.toml`, `config.py`, scaffolding, `pipeline.yaml`) — `5aeefb01`
- [x] **Task 2** — Pydantic schemas (7 schemas: `TranscriptEvent`, `SentimentResult`, `MemoryEntry`, `ToolCall`, `AgentContext`, `ResponsePlan`, `AgentStateSnapshot`) — `2a250fb2` + `1e914fe8`
- [x] **Task 3** — FSM states & transitions (`AgentStateEnum`, `VALID_TRANSITIONS`, `AgentFSM`) — `3d59ab37`
- [x] **Task 4** — `BrainBase` ABC + `BrainRegistry` — `cc4155f4`
- [x] **Task 5** — Ollama client (async httpx) — `6aa322f0`
- [x] **Task 6** — Short-term memory (`ShortTermMemory` via `redis[asyncio]`) — `14593c98`
- [x] **Task 7** — Long-term memory (`LongTermMemory` via `aiosqlite`) — `3f69ba08`
- [x] **Task 8** — `ReasoningBrain` (LLM text generation) — `d534ed9e`
- [x] **Task 9** — `SentimentBrain` (LLM + rule-based fallback) — `01a7488f`
- [x] **Task 10** — `InteractionBrain` (memory read/write) — `2142dd58`
- [x] **Task 11** — `ActionBrain` (rule-based routing, zero LLM) — `6651fe0e`
- [x] **Task 12** — Orchestrator + text pipeline end-to-end (`agent/orchestrator.py`, `agent/main.py`) — `83f093db` + `64118de5`

**Phase 1 milestone:** `python -m agent.main` works (requires Redis + Ollama). 32 tests passing.

---

## Phase 2 — Voice In/Out

- [ ] **Task 13** — `InputBrain` (VAD + Whisper STT, runs in `ThreadPoolExecutor`)
  - Files: `agent/brains/input_brain.py`, `tests/unit/test_input_brain.py`
  - Prereq: `pip install -e ".[voice]"`
  - Commit message: `feat: InputBrain (VAD + Whisper STT)`

- [ ] **Task 14** — `OutputBrain` (Piper TTS, runs in `ThreadPoolExecutor`)
  - Files: `agent/brains/output_brain.py`, `tests/unit/test_output_brain.py`
  - Commit message: `feat: OutputBrain (Piper TTS)`

- [ ] **Task 15** — Voice loop integration
  - Files: `agent/audio/vad_loop.py`, modify `agent/orchestrator.py` (add `voice_enabled` + `process_audio`), `tests/integration/test_voice_pipeline.py`
  - Commit message: `feat: voice pipeline (VAD + STT + TTS integration)`

**Phase 2 milestone:** Full mic → response cycle works end-to-end.

---

## Phase 3 — Docker + Dashboard

- [ ] **Task 16** — Docker Compose for Redis
  - Files: `docker/docker-compose.yml`, `docker/.env.docker`
  - Commit message: `infra: Docker Compose for Redis`

- [ ] **Task 17** — Monitoring-only dashboard (FastAPI + WebSocket)
  - Files: `dashboard/server.py`, `dashboard/static/index.html`, `tests/unit/test_dashboard.py`
  - Endpoints: `GET /health`, `GET /state`, `WS /ws` (broadcasts `AgentStateSnapshot`)
  - Read-only — zero control buttons
  - Commit message: `feat: monitoring-only dashboard (FastAPI + WebSocket)`

---

## Phase 4 — Polish & Observability

- [ ] **Task 18** — Per-brain latency tracking
  - Modify: `agent/brains/base.py` (`BrainRegistry.run_pipeline` wraps each call with `time.perf_counter`)
  - Stores `context["_timings"]` dict; orchestrator updates `AgentStateSnapshot.latency_ms`
  - Commit message: `feat: per-brain latency tracking`

- [ ] **Task 19** — Startup health checks
  - Files: `agent/health.py`, modify `agent/main.py`
  - Checks: Redis ping, Ollama `/api/tags` reachable
  - Commit message: `feat: startup health checks (Redis + Ollama)`

---

## Final Verification (after Task 19)

```bash
.venv/bin/pytest tests/ -v          # all tests pass
.venv/bin/ruff check agent/ dashboard/ tests/   # lint clean
docker compose -f docker/docker-compose.yml up -d
python -m agent.main                # text REPL
uvicorn dashboard.server:app --host 0.0.0.0 --port 8080  # dashboard at :8080
```

---

## Out of Scope (this version)

- Avatar / 3D VRM control
- Multiple simultaneous sessions
- Distributed brain processes
- Cloud fallback LLM
- Voice cloning / custom voices
- Fine-tuned models
