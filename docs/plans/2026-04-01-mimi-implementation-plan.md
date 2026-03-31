# Mimi v2 — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a voice AI agent (STT → LLM → TTS) with FSM-based brain orchestration, Redis/SQLite memory, and a monitoring-only web dashboard.

**Architecture:** `AgentFSM` drives state transitions (idle → listening → processing → speaking → error). Each state runs a pipeline of brains defined in `config/pipeline.yaml`. Only 2 brains call the LLM (SentimentBrain + ReasoningBrain). Docker runs Redis only; agent runs directly in Python.

**Tech Stack:** Python 3.11, asyncio, pydantic v2, faster-whisper, webrtcvad, sounddevice, Ollama (remote), Piper TTS, Redis (aioredis), SQLite (aiosqlite), FastAPI + WebSocket.

---

## Phase 1 — Core Pipeline (text only, no audio)

### Task 1: Project Setup

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `agent/__init__.py`
- Create: `agent/config.py`
- Create: `agent/fsm/__init__.py`
- Create: `agent/brains/__init__.py`
- Create: `agent/memory/__init__.py`
- Create: `agent/llm/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/unit/__init__.py`
- Create: `tests/integration/__init__.py`
- Create: `config/pipeline.yaml`

**Step 1: Create pyproject.toml**

```toml
[project]
name = "mimi"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "httpx>=0.27",
    "aioredis>=2.0",
    "aiosqlite>=0.20",
    "fastapi>=0.111",
    "uvicorn[standard]>=0.30",
    "python-dotenv>=1.0",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
voice = [
    "sounddevice>=0.4",
    "faster-whisper>=1.0",
    "webrtcvad>=2.0",
    "piper-tts>=1.2",
]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-mock>=3.12",
    "ruff>=0.4",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py311"
```

**Step 2: Create .env.example**

```env
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=mistral:7b-instruct
OLLAMA_SENTIMENT_MODEL=qwen2.5:0.5b
REDIS_URL=redis://localhost:6379
SQLITE_PATH=data/memory.db
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=8080
LOG_LEVEL=INFO
```

**Step 3: Create agent/config.py**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "mistral:7b-instruct"
    ollama_sentiment_model: str = "qwen2.5:0.5b"
    redis_url: str = "redis://localhost:6379"
    sqlite_path: str = "data/memory.db"
    dashboard_host: str = "0.0.0.0"
    dashboard_port: int = 8080
    log_level: str = "INFO"

settings = Settings()
```

**Step 4: Create config/pipeline.yaml**

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

**Step 5: Install dependencies**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Expected: no errors, `pytest --collect-only` runs.

**Step 6: Commit**

```bash
git add pyproject.toml .env.example agent/ config/ tests/
git commit -m "chore: project scaffolding and config"
```

---

### Task 2: Pydantic Schemas

**Files:**
- Create: `agent/schemas.py`
- Create: `tests/unit/test_schemas.py`

**Step 1: Write failing tests**

```python
# tests/unit/test_schemas.py
from datetime import datetime
from agent.schemas import (
    TranscriptEvent, SentimentResult, AgentContext,
    ResponsePlan, AgentStateSnapshot, MemoryEntry, ToolCall
)

def test_transcript_event_defaults():
    t = TranscriptEvent(text="hello", confidence=0.95)
    assert t.text == "hello"
    assert isinstance(t.timestamp, datetime)

def test_sentiment_result_valid_emotions():
    s = SentimentResult(emotion="happy", intensity=0.8)
    assert s.emotion == "happy"

def test_sentiment_result_invalid_emotion():
    with pytest.raises(Exception):
        SentimentResult(emotion="bored", intensity=0.5)

def test_response_plan_default_no_tools():
    r = ResponsePlan(text="hi", action="speak")
    assert r.tool_calls == []

def test_agent_state_snapshot():
    snap = AgentStateSnapshot(
        fsm_state="idle", active_brain="none",
        last_emotion="neutral", last_transcript="",
        latency_ms=0
    )
    assert snap.fsm_state == "idle"
```

**Step 2: Run to confirm failure**

```bash
pytest tests/unit/test_schemas.py -v
```
Expected: `ImportError` (schemas.py doesn't exist yet).

**Step 3: Write agent/schemas.py**

```python
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class TranscriptEvent(BaseModel):
    text: str
    confidence: float = 1.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SentimentResult(BaseModel):
    emotion: Literal["neutral", "happy", "sad", "angry", "surprised", "curious"]
    intensity: float = Field(ge=0.0, le=1.0)


class MemoryEntry(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ToolCall(BaseModel):
    name: str
    args: dict = Field(default_factory=dict)


class AgentContext(BaseModel):
    transcript: TranscriptEvent
    sentiment: SentimentResult | None = None
    memory: list[MemoryEntry] = Field(default_factory=list)
    session_id: str


class ResponsePlan(BaseModel):
    text: str
    action: Literal["speak", "speak+tool", "silence"] = "speak"
    tool_calls: list[ToolCall] = Field(default_factory=list)


class AgentStateSnapshot(BaseModel):
    fsm_state: str
    active_brain: str
    last_emotion: str
    last_transcript: str
    latency_ms: int
```

**Step 4: Run tests**

```bash
pytest tests/unit/test_schemas.py -v
```
Expected: all pass.

**Step 5: Commit**

```bash
git add agent/schemas.py tests/unit/test_schemas.py
git commit -m "feat: add core Pydantic schemas"
```

---

### Task 3: FSM — States & Transitions

**Files:**
- Create: `agent/fsm/states.py`
- Create: `agent/fsm/agent_fsm.py`
- Create: `tests/unit/test_fsm.py`

**Step 1: Write failing tests**

```python
# tests/unit/test_fsm.py
import pytest
from agent.fsm.states import AgentStateEnum, VALID_TRANSITIONS
from agent.fsm.agent_fsm import AgentFSM

def test_valid_transitions_defined():
    assert AgentStateEnum.IDLE in VALID_TRANSITIONS
    assert AgentStateEnum.LISTENING in VALID_TRANSITIONS[AgentStateEnum.IDLE]

@pytest.mark.asyncio
async def test_fsm_starts_idle():
    fsm = AgentFSM()
    assert fsm.state == AgentStateEnum.IDLE

@pytest.mark.asyncio
async def test_fsm_valid_transition():
    fsm = AgentFSM()
    await fsm.transition(AgentStateEnum.LISTENING)
    assert fsm.state == AgentStateEnum.LISTENING

@pytest.mark.asyncio
async def test_fsm_invalid_transition_raises():
    fsm = AgentFSM()
    with pytest.raises(ValueError, match="Invalid transition"):
        await fsm.transition(AgentStateEnum.SPEAKING)

@pytest.mark.asyncio
async def test_fsm_error_recovery():
    fsm = AgentFSM()
    await fsm.transition(AgentStateEnum.LISTENING)
    await fsm.transition(AgentStateEnum.ERROR)
    await fsm.transition(AgentStateEnum.IDLE)
    assert fsm.state == AgentStateEnum.IDLE
```

**Step 2: Run to confirm failure**

```bash
pytest tests/unit/test_fsm.py -v
```

**Step 3: Write agent/fsm/states.py**

```python
from enum import Enum

class AgentStateEnum(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    ERROR = "error"

VALID_TRANSITIONS: dict[AgentStateEnum, set[AgentStateEnum]] = {
    AgentStateEnum.IDLE:       {AgentStateEnum.LISTENING},
    AgentStateEnum.LISTENING:  {AgentStateEnum.PROCESSING, AgentStateEnum.IDLE, AgentStateEnum.ERROR},
    AgentStateEnum.PROCESSING: {AgentStateEnum.SPEAKING, AgentStateEnum.IDLE, AgentStateEnum.ERROR},
    AgentStateEnum.SPEAKING:   {AgentStateEnum.IDLE, AgentStateEnum.ERROR},
    AgentStateEnum.ERROR:      {AgentStateEnum.IDLE},
}
```

**Step 4: Write agent/fsm/agent_fsm.py**

```python
import asyncio
import logging
from collections.abc import Callable, Awaitable
from agent.fsm.states import AgentStateEnum, VALID_TRANSITIONS
from agent.schemas import AgentStateSnapshot

log = logging.getLogger(__name__)

StateCallback = Callable[[AgentStateEnum, AgentStateEnum], Awaitable[None]]


class AgentFSM:
    def __init__(self) -> None:
        self._state = AgentStateEnum.IDLE
        self._lock = asyncio.Lock()
        self._callbacks: list[StateCallback] = []

    @property
    def state(self) -> AgentStateEnum:
        return self._state

    def on_transition(self, cb: StateCallback) -> None:
        self._callbacks.append(cb)

    async def transition(self, new_state: AgentStateEnum) -> None:
        async with self._lock:
            allowed = VALID_TRANSITIONS.get(self._state, set())
            if new_state not in allowed:
                raise ValueError(
                    f"Invalid transition: {self._state} → {new_state}. Allowed: {allowed}"
                )
            old = self._state
            self._state = new_state
            log.debug("FSM: %s → %s", old, new_state)

        for cb in self._callbacks:
            try:
                await cb(old, new_state)
            except Exception:
                log.exception("FSM callback error")
```

**Step 5: Run tests**

```bash
pytest tests/unit/test_fsm.py -v
```
Expected: all pass.

**Step 6: Commit**

```bash
git add agent/fsm/ tests/unit/test_fsm.py
git commit -m "feat: FSM states and transitions"
```

---

### Task 4: BrainBase & BrainRegistry

**Files:**
- Create: `agent/brains/base.py`
- Create: `tests/unit/test_brain_base.py`

**Step 1: Write failing tests**

```python
# tests/unit/test_brain_base.py
import pytest
from agent.brains.base import BrainBase, BrainRegistry

class EchoBrain(BrainBase):
    name = "echo"
    async def run(self, context: dict) -> dict:
        return {**context, "echo": True}

@pytest.mark.asyncio
async def test_brain_run():
    brain = EchoBrain()
    result = await brain.run({"input": "hello"})
    assert result["echo"] is True
    assert result["input"] == "hello"

def test_registry_register_and_get():
    registry = BrainRegistry()
    brain = EchoBrain()
    registry.register(brain)
    assert registry.get("echo") is brain

def test_registry_get_unknown_raises():
    registry = BrainRegistry()
    with pytest.raises(KeyError):
        registry.get("unknown")

@pytest.mark.asyncio
async def test_registry_run_pipeline():
    registry = BrainRegistry()
    registry.register(EchoBrain())
    ctx = {"value": 1}
    result = await registry.run_pipeline(["echo"], ctx)
    assert result["echo"] is True
```

**Step 2: Run to confirm failure**

```bash
pytest tests/unit/test_brain_base.py -v
```

**Step 3: Write agent/brains/base.py**

```python
import abc
import logging
from typing import Any

log = logging.getLogger(__name__)


class BrainBase(abc.ABC):
    name: str = "base"

    @abc.abstractmethod
    async def run(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute brain logic. Receives context dict, returns updated context."""

    async def setup(self) -> None:
        """Optional async initialization."""

    async def teardown(self) -> None:
        """Optional async cleanup."""


class BrainRegistry:
    def __init__(self) -> None:
        self._brains: dict[str, BrainBase] = {}

    def register(self, brain: BrainBase) -> None:
        self._brains[brain.name] = brain
        log.debug("Registered brain: %s", brain.name)

    def get(self, name: str) -> BrainBase:
        if name not in self._brains:
            raise KeyError(f"Brain '{name}' not registered. Available: {list(self._brains)}")
        return self._brains[name]

    async def run_pipeline(
        self, pipeline: list[str], context: dict[str, Any]
    ) -> dict[str, Any]:
        for name in pipeline:
            brain = self.get(name)
            log.debug("Running brain: %s", name)
            try:
                context = await brain.run(context)
            except Exception:
                log.exception("Brain '%s' failed", name)
                raise
        return context

    async def setup_all(self) -> None:
        for brain in self._brains.values():
            await brain.setup()

    async def teardown_all(self) -> None:
        for brain in self._brains.values():
            await brain.teardown()
```

**Step 4: Run tests**

```bash
pytest tests/unit/test_brain_base.py -v
```
Expected: all pass.

**Step 5: Commit**

```bash
git add agent/brains/base.py tests/unit/test_brain_base.py
git commit -m "feat: BrainBase and BrainRegistry"
```

---

### Task 5: Ollama Client

**Files:**
- Create: `agent/llm/ollama_client.py`
- Create: `tests/unit/test_ollama_client.py`

**Step 1: Write failing tests**

```python
# tests/unit/test_ollama_client.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from agent.llm.ollama_client import OllamaClient

@pytest.mark.asyncio
async def test_generate_returns_text():
    client = OllamaClient(host="http://fake:11434", model="test")
    mock_response = MagicMock()
    mock_response.json = AsyncMock(return_value={
        "message": {"content": "Hello there"}
    })
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
        result = await client.generate(messages=[{"role": "user", "content": "hi"}])
    
    assert result == "Hello there"
    mock_post.assert_called_once()

@pytest.mark.asyncio
async def test_generate_includes_system_prompt():
    client = OllamaClient(host="http://fake:11434", model="test", system_prompt="You are Mimi.")
    mock_response = MagicMock()
    mock_response.json = AsyncMock(return_value={"message": {"content": "Hi!"}})
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
        await client.generate(messages=[{"role": "user", "content": "hello"}])

    call_args = mock_post.call_args
    body = call_args.kwargs.get("json", call_args.args[1] if len(call_args.args) > 1 else {})
    messages = body["messages"]
    assert messages[0]["role"] == "system"
    assert "Mimi" in messages[0]["content"]
```

**Step 2: Run to confirm failure**

```bash
pytest tests/unit/test_ollama_client.py -v
```

**Step 3: Write agent/llm/ollama_client.py**

```python
import logging
import httpx
from typing import Any

log = logging.getLogger(__name__)

Message = dict[str, str]  # {"role": "user"|"assistant"|"system", "content": str}


class OllamaClient:
    def __init__(
        self,
        host: str,
        model: str,
        system_prompt: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._host = host.rstrip("/")
        self._model = model
        self._system_prompt = system_prompt
        self._timeout = timeout

    async def generate(self, messages: list[Message]) -> str:
        all_messages: list[Message] = []
        if self._system_prompt:
            all_messages.append({"role": "system", "content": self._system_prompt})
        all_messages.extend(messages)

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": all_messages,
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(f"{self._host}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()

        text: str = data["message"]["content"]
        log.debug("Ollama [%s]: %d chars", self._model, len(text))
        return text
```

**Step 4: Run tests**

```bash
pytest tests/unit/test_ollama_client.py -v
```
Expected: all pass.

**Step 5: Commit**

```bash
git add agent/llm/ollama_client.py tests/unit/test_ollama_client.py
git commit -m "feat: async Ollama client"
```

---

### Task 6: Short-Term Memory (Redis)

**Files:**
- Create: `agent/memory/short_term.py`
- Create: `tests/unit/test_short_term.py`

**Step 1: Write failing tests**

```python
# tests/unit/test_short_term.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from agent.memory.short_term import ShortTermMemory
from agent.schemas import MemoryEntry

@pytest.fixture
def mock_redis(mocker):
    redis = AsyncMock()
    mocker.patch("aioredis.from_url", return_value=redis)
    return redis

@pytest.mark.asyncio
async def test_add_and_get_history(mock_redis):
    mock_redis.rpush = AsyncMock()
    mock_redis.lrange = AsyncMock(return_value=[
        b'{"role": "user", "content": "hello", "timestamp": "2026-01-01T00:00:00"}'
    ])
    
    mem = ShortTermMemory(redis_url="redis://fake")
    await mem.connect()
    await mem.add("session1", MemoryEntry(role="user", content="hello"))
    entries = await mem.get_history("session1", limit=10)
    
    assert len(entries) == 1
    assert entries[0].content == "hello"

@pytest.mark.asyncio
async def test_clear_session(mock_redis):
    mock_redis.delete = AsyncMock()
    mem = ShortTermMemory(redis_url="redis://fake")
    await mem.connect()
    await mem.clear("session1")
    mock_redis.delete.assert_called_once()
```

**Step 2: Run to confirm failure**

```bash
pytest tests/unit/test_short_term.py -v
```

**Step 3: Write agent/memory/short_term.py**

```python
import json
import logging
import aioredis
from agent.schemas import MemoryEntry

log = logging.getLogger(__name__)
_KEY_PREFIX = "mimi:session:"
_MAX_HISTORY = 50


class ShortTermMemory:
    def __init__(self, redis_url: str) -> None:
        self._url = redis_url
        self._redis: aioredis.Redis | None = None

    async def connect(self) -> None:
        self._redis = await aioredis.from_url(self._url, decode_responses=False)
        log.info("Redis connected: %s", self._url)

    async def disconnect(self) -> None:
        if self._redis:
            await self._redis.close()

    def _key(self, session_id: str) -> str:
        return f"{_KEY_PREFIX}{session_id}"

    async def add(self, session_id: str, entry: MemoryEntry) -> None:
        assert self._redis, "Not connected"
        key = self._key(session_id)
        await self._redis.rpush(key, entry.model_dump_json())
        await self._redis.ltrim(key, -_MAX_HISTORY, -1)

    async def get_history(self, session_id: str, limit: int = 20) -> list[MemoryEntry]:
        assert self._redis, "Not connected"
        raw: list[bytes] = await self._redis.lrange(self._key(session_id), -limit, -1)
        return [MemoryEntry.model_validate_json(r) for r in raw]

    async def clear(self, session_id: str) -> None:
        assert self._redis, "Not connected"
        await self._redis.delete(self._key(session_id))
```

**Step 4: Run tests**

```bash
pytest tests/unit/test_short_term.py -v
```
Expected: all pass.

**Step 5: Commit**

```bash
git add agent/memory/short_term.py tests/unit/test_short_term.py
git commit -m "feat: Redis short-term memory"
```

---

### Task 7: Long-Term Memory (SQLite)

**Files:**
- Create: `agent/memory/long_term.py`
- Create: `tests/unit/test_long_term.py`

**Step 1: Write failing tests**

```python
# tests/unit/test_long_term.py
import pytest
from agent.memory.long_term import LongTermMemory
from agent.schemas import MemoryEntry

@pytest.fixture
async def mem(tmp_path):
    db_path = str(tmp_path / "test.db")
    m = LongTermMemory(db_path=db_path)
    await m.connect()
    yield m
    await m.disconnect()

@pytest.mark.asyncio
async def test_save_and_load(mem):
    entry = MemoryEntry(role="user", content="remember this")
    await mem.save("session1", entry)
    results = await mem.load("session1", limit=10)
    assert len(results) == 1
    assert results[0].content == "remember this"

@pytest.mark.asyncio
async def test_load_empty_session(mem):
    results = await mem.load("nonexistent", limit=10)
    assert results == []

@pytest.mark.asyncio
async def test_load_respects_limit(mem):
    for i in range(5):
        await mem.save("s", MemoryEntry(role="user", content=f"msg {i}"))
    results = await mem.load("s", limit=3)
    assert len(results) == 3
```

**Step 2: Run to confirm failure**

```bash
pytest tests/unit/test_long_term.py -v
```

**Step 3: Write agent/memory/long_term.py**

```python
import logging
import aiosqlite
from agent.schemas import MemoryEntry

log = logging.getLogger(__name__)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL
)
"""


class LongTermMemory:
    def __init__(self, db_path: str) -> None:
        self._path = db_path
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self._db = await aiosqlite.connect(self._path)
        await self._db.execute(_CREATE_TABLE)
        await self._db.commit()
        log.info("SQLite connected: %s", self._path)

    async def disconnect(self) -> None:
        if self._db:
            await self._db.close()

    async def save(self, session_id: str, entry: MemoryEntry) -> None:
        assert self._db
        await self._db.execute(
            "INSERT INTO memory (session_id, role, content, timestamp) VALUES (?,?,?,?)",
            (session_id, entry.role, entry.content, entry.timestamp.isoformat()),
        )
        await self._db.commit()

    async def load(self, session_id: str, limit: int = 20) -> list[MemoryEntry]:
        assert self._db
        async with self._db.execute(
            "SELECT role, content, timestamp FROM memory WHERE session_id=? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()
        return [MemoryEntry(role=r[0], content=r[1], timestamp=r[2]) for r in reversed(rows)]
```

**Step 4: Run tests**

```bash
pytest tests/unit/test_long_term.py -v
```
Expected: all pass.

**Step 5: Commit**

```bash
git add agent/memory/long_term.py tests/unit/test_long_term.py
git commit -m "feat: SQLite long-term memory"
```

---

### Task 8: ReasoningBrain

**Files:**
- Create: `agent/brains/reasoning_brain.py`
- Create: `tests/unit/test_reasoning_brain.py`

**Step 1: Write failing tests**

```python
# tests/unit/test_reasoning_brain.py
import pytest
from unittest.mock import AsyncMock
from agent.brains.reasoning_brain import ReasoningBrain
from agent.schemas import TranscriptEvent, SentimentResult, AgentContext, ResponsePlan

def make_context(text: str = "hello") -> dict:
    ctx: dict = {
        "context": AgentContext(
            transcript=TranscriptEvent(text=text),
            sentiment=SentimentResult(emotion="neutral", intensity=0.5),
            memory=[],
            session_id="test",
        )
    }
    return ctx

@pytest.mark.asyncio
async def test_reasoning_brain_produces_response_plan(mocker):
    brain = ReasoningBrain.__new__(ReasoningBrain)
    brain._client = AsyncMock()
    brain._client.generate = AsyncMock(return_value="Hello! How can I help?")
    brain.name = "reasoning"

    ctx = make_context("hi mimi")
    result = await brain.run(ctx)

    assert "response_plan" in result
    plan = result["response_plan"]
    assert isinstance(plan, ResponsePlan)
    assert plan.text == "Hello! How can I help?"
    assert plan.action == "speak"

@pytest.mark.asyncio
async def test_reasoning_brain_passes_history_to_llm(mocker):
    from agent.schemas import MemoryEntry
    brain = ReasoningBrain.__new__(ReasoningBrain)
    brain._client = AsyncMock()
    brain._client.generate = AsyncMock(return_value="Sure!")
    brain.name = "reasoning"

    ctx = make_context("what did I say?")
    ctx["context"].memory = [MemoryEntry(role="user", content="I said hello")]
    
    result = await brain.run(ctx)
    call_args = brain._client.generate.call_args
    messages = call_args.kwargs["messages"] if call_args.kwargs else call_args.args[0]
    assert any("I said hello" in m["content"] for m in messages)
```

**Step 2: Run to confirm failure**

```bash
pytest tests/unit/test_reasoning_brain.py -v
```

**Step 3: Write agent/brains/reasoning_brain.py**

```python
import logging
from agent.brains.base import BrainBase
from agent.llm.ollama_client import OllamaClient
from agent.schemas import AgentContext, ResponsePlan
from agent.config import settings

log = logging.getLogger(__name__)

_SYSTEM = """You are Mimi, a helpful AI companion.
You speak naturally and concisely.
Respond only with your spoken reply — no stage directions, no markdown."""


class ReasoningBrain(BrainBase):
    name = "reasoning"

    def __init__(self) -> None:
        self._client = OllamaClient(
            host=settings.ollama_host,
            model=settings.ollama_model,
            system_prompt=_SYSTEM,
        )

    async def run(self, context: dict) -> dict:
        ctx: AgentContext = context["context"]
        messages = [
            {"role": e.role, "content": e.content}
            for e in ctx.memory
        ]
        messages.append({"role": "user", "content": ctx.transcript.text})

        text = await self._client.generate(messages=messages)
        context["response_plan"] = ResponsePlan(text=text, action="speak")
        log.debug("ReasoningBrain: %d chars", len(text))
        return context
```

**Step 4: Run tests**

```bash
pytest tests/unit/test_reasoning_brain.py -v
```
Expected: all pass.

**Step 5: Commit**

```bash
git add agent/brains/reasoning_brain.py tests/unit/test_reasoning_brain.py
git commit -m "feat: ReasoningBrain (LLM text generation)"
```

---

### Task 9: SentimentBrain

**Files:**
- Create: `agent/brains/sentiment_brain.py`
- Create: `tests/unit/test_sentiment_brain.py`

**Step 1: Write failing tests**

```python
# tests/unit/test_sentiment_brain.py
import pytest
from unittest.mock import AsyncMock
from agent.brains.sentiment_brain import SentimentBrain
from agent.schemas import TranscriptEvent, AgentContext, SentimentResult

def make_context(text: str) -> dict:
    return {
        "context": AgentContext(
            transcript=TranscriptEvent(text=text),
            memory=[],
            session_id="test",
        )
    }

@pytest.mark.asyncio
async def test_sentiment_brain_sets_sentiment(mocker):
    brain = SentimentBrain.__new__(SentimentBrain)
    brain._client = AsyncMock()
    brain._client.generate = AsyncMock(return_value='{"emotion": "happy", "intensity": 0.9}')
    brain.name = "sentiment"

    ctx = make_context("This is great!")
    result = await brain.run(ctx)

    assert result["context"].sentiment is not None
    assert result["context"].sentiment.emotion == "happy"

@pytest.mark.asyncio
async def test_sentiment_brain_falls_back_on_invalid_json(mocker):
    brain = SentimentBrain.__new__(SentimentBrain)
    brain._client = AsyncMock()
    brain._client.generate = AsyncMock(return_value="oops not json")
    brain.name = "sentiment"

    ctx = make_context("something")
    result = await brain.run(ctx)
    # Fallback: neutral sentiment, never crashes
    assert result["context"].sentiment.emotion == "neutral"
```

**Step 2: Run to confirm failure**

```bash
pytest tests/unit/test_sentiment_brain.py -v
```

**Step 3: Write agent/brains/sentiment_brain.py**

```python
import json
import logging
from agent.brains.base import BrainBase
from agent.llm.ollama_client import OllamaClient
from agent.schemas import AgentContext, SentimentResult
from agent.config import settings

log = logging.getLogger(__name__)

_SYSTEM = """Analyze the emotion in the user's message.
Respond ONLY with valid JSON: {"emotion": "<one of: neutral,happy,sad,angry,surprised,curious>", "intensity": <0.0-1.0>}
No other text."""


class SentimentBrain(BrainBase):
    name = "sentiment"

    def __init__(self) -> None:
        self._client = OllamaClient(
            host=settings.ollama_host,
            model=settings.ollama_sentiment_model,
            system_prompt=_SYSTEM,
        )

    async def run(self, context: dict) -> dict:
        ctx: AgentContext = context["context"]
        try:
            raw = await self._client.generate(
                messages=[{"role": "user", "content": ctx.transcript.text}]
            )
            data = json.loads(raw.strip())
            ctx.sentiment = SentimentResult(**data)
        except Exception:
            log.warning("SentimentBrain fallback to neutral")
            ctx.sentiment = SentimentResult(emotion="neutral", intensity=0.0)
        return context
```

**Step 4: Run tests**

```bash
pytest tests/unit/test_sentiment_brain.py -v
```
Expected: all pass.

**Step 5: Commit**

```bash
git add agent/brains/sentiment_brain.py tests/unit/test_sentiment_brain.py
git commit -m "feat: SentimentBrain with LLM fallback"
```

---

### Task 10: InteractionBrain

**Files:**
- Create: `agent/brains/interaction_brain.py`
- Create: `tests/unit/test_interaction_brain.py`

**Step 1: Write failing tests**

```python
# tests/unit/test_interaction_brain.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from agent.brains.interaction_brain import InteractionBrain
from agent.schemas import TranscriptEvent, AgentContext, ResponsePlan, MemoryEntry

def make_context(text: str = "hello") -> dict:
    return {
        "context": AgentContext(
            transcript=TranscriptEvent(text=text),
            memory=[],
            session_id="sess1",
        )
    }

@pytest.mark.asyncio
async def test_read_loads_history(mocker):
    brain = InteractionBrain.__new__(InteractionBrain)
    brain._short = AsyncMock()
    brain._long = AsyncMock()
    brain._short.get_history = AsyncMock(return_value=[MemoryEntry(role="user", content="prev")])
    brain._long.load = AsyncMock(return_value=[])
    brain.name = "interaction_read"

    ctx = make_context()
    result = await brain.run_read(ctx)
    assert len(result["context"].memory) == 1

@pytest.mark.asyncio
async def test_write_saves_turn(mocker):
    brain = InteractionBrain.__new__(InteractionBrain)
    brain._short = AsyncMock()
    brain._long = AsyncMock()
    brain._short.add = AsyncMock()
    brain._long.save = AsyncMock()

    ctx = make_context("hi")
    ctx["response_plan"] = ResponsePlan(text="hello back", action="speak")
    await brain.run_write(ctx)

    assert brain._short.add.call_count == 2  # user + assistant
    assert brain._long.save.call_count == 2
```

**Step 2: Run to confirm failure**

```bash
pytest tests/unit/test_interaction_brain.py -v
```

**Step 3: Write agent/brains/interaction_brain.py**

```python
import logging
from agent.brains.base import BrainBase
from agent.memory.short_term import ShortTermMemory
from agent.memory.long_term import LongTermMemory
from agent.schemas import AgentContext, MemoryEntry, ResponsePlan

log = logging.getLogger(__name__)


class InteractionBrain(BrainBase):
    name = "interaction_read"  # primary name (read phase)

    def __init__(self, short: ShortTermMemory, long: LongTermMemory) -> None:
        self._short = short
        self._long = long

    async def run(self, context: dict) -> dict:
        """Default: read phase."""
        return await self.run_read(context)

    async def run_read(self, context: dict) -> dict:
        ctx: AgentContext = context["context"]
        recent = await self._short.get_history(ctx.session_id, limit=10)
        if not recent:
            recent = await self._long.load(ctx.session_id, limit=5)
        ctx.memory = recent
        log.debug("InteractionBrain: loaded %d memory entries", len(recent))
        return context

    async def run_write(self, context: dict) -> None:
        ctx: AgentContext = context["context"]
        plan: ResponsePlan | None = context.get("response_plan")
        if plan is None:
            return

        user_entry = MemoryEntry(role="user", content=ctx.transcript.text)
        assistant_entry = MemoryEntry(role="assistant", content=plan.text)

        for entry in (user_entry, assistant_entry):
            await self._short.add(ctx.session_id, entry)
            await self._long.save(ctx.session_id, entry)


class InteractionWriteBrain(BrainBase):
    """Separate brain instance for the write phase in the pipeline."""
    name = "interaction_write"

    def __init__(self, interaction: "InteractionBrain") -> None:
        self._interaction = interaction

    async def run(self, context: dict) -> dict:
        await self._interaction.run_write(context)
        return context
```

**Step 4: Run tests**

```bash
pytest tests/unit/test_interaction_brain.py -v
```
Expected: all pass.

**Step 5: Commit**

```bash
git add agent/brains/interaction_brain.py tests/unit/test_interaction_brain.py
git commit -m "feat: InteractionBrain (memory read/write)"
```

---

### Task 11: ActionBrain (Rule-Based)

**Files:**
- Create: `agent/brains/action_brain.py`
- Create: `tests/unit/test_action_brain.py`

**Step 1: Write failing tests**

```python
# tests/unit/test_action_brain.py
import pytest
from agent.brains.action_brain import ActionBrain
from agent.schemas import AgentContext, TranscriptEvent, ResponsePlan

def make_context(text: str, response: str = "ok") -> dict:
    return {
        "context": AgentContext(
            transcript=TranscriptEvent(text=text),
            memory=[],
            session_id="test",
        ),
        "response_plan": ResponsePlan(text=response, action="speak"),
    }

@pytest.mark.asyncio
async def test_action_brain_passes_through_default():
    brain = ActionBrain()
    ctx = make_context("hello")
    result = await brain.run(ctx)
    assert result["response_plan"].action == "speak"

@pytest.mark.asyncio
async def test_action_brain_detects_silence():
    brain = ActionBrain()
    ctx = make_context("ok")
    ctx["response_plan"] = ResponsePlan(text="", action="speak")
    result = await brain.run(ctx)
    assert result["response_plan"].action == "silence"
```

**Step 2: Run to confirm failure**

```bash
pytest tests/unit/test_action_brain.py -v
```

**Step 3: Write agent/brains/action_brain.py**

```python
import logging
from agent.brains.base import BrainBase
from agent.schemas import ResponsePlan

log = logging.getLogger(__name__)


class ActionBrain(BrainBase):
    """Rule-based intent routing. Zero LLM calls."""
    name = "action"

    async def run(self, context: dict) -> dict:
        plan: ResponsePlan = context.get("response_plan")
        if plan is None:
            return context

        # Rule: empty response → silence
        if not plan.text.strip():
            plan.action = "silence"
            log.debug("ActionBrain: empty response → silence")

        context["response_plan"] = plan
        return context
```

**Step 4: Run tests**

```bash
pytest tests/unit/test_action_brain.py -v
```
Expected: all pass.

**Step 5: Commit**

```bash
git add agent/brains/action_brain.py tests/unit/test_action_brain.py
git commit -m "feat: ActionBrain rule-based routing"
```

---

### Task 12: Orchestrator + Text Pipeline

**Files:**
- Create: `agent/orchestrator.py`
- Create: `agent/main.py`
- Create: `tests/integration/test_text_pipeline.py`

**Step 1: Write failing integration test**

```python
# tests/integration/test_text_pipeline.py
import pytest
from unittest.mock import AsyncMock, patch
from agent.orchestrator import Orchestrator

@pytest.mark.asyncio
async def test_text_turn_end_to_end(mocker):
    """Test a single text turn: input → reasoning → output text"""
    # Mock Ollama calls
    mocker.patch(
        "agent.llm.ollama_client.OllamaClient.generate",
        side_effect=[
            '{"emotion": "neutral", "intensity": 0.5}',  # sentiment
            "Hi there! Nice to meet you.",                # reasoning
        ],
    )
    # Mock Redis (not running in unit tests)
    mocker.patch("aioredis.from_url", return_value=AsyncMock(
        rpush=AsyncMock(), lrange=AsyncMock(return_value=[]),
        ltrim=AsyncMock(), delete=AsyncMock(), close=AsyncMock()
    ))

    orchestrator = Orchestrator()
    await orchestrator.setup()

    response = await orchestrator.process_text("Hello Mimi!")
    assert response is not None
    assert "Hi there" in response or len(response) > 0

    await orchestrator.teardown()
```

**Step 2: Run to confirm failure**

```bash
pytest tests/integration/test_text_pipeline.py -v
```

**Step 3: Write agent/orchestrator.py**

```python
import asyncio
import logging
import uuid
import yaml
from pathlib import Path
from agent.fsm.agent_fsm import AgentFSM
from agent.fsm.states import AgentStateEnum
from agent.brains.base import BrainRegistry
from agent.brains.reasoning_brain import ReasoningBrain
from agent.brains.sentiment_brain import SentimentBrain
from agent.brains.action_brain import ActionBrain
from agent.brains.interaction_brain import InteractionBrain, InteractionWriteBrain
from agent.memory.short_term import ShortTermMemory
from agent.memory.long_term import LongTermMemory
from agent.schemas import TranscriptEvent, AgentContext, AgentStateSnapshot
from agent.config import settings

log = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self) -> None:
        self._fsm = AgentFSM()
        self._registry = BrainRegistry()
        self._short_mem = ShortTermMemory(settings.redis_url)
        self._long_mem = LongTermMemory(settings.sqlite_path)
        self._state_snapshot = AgentStateSnapshot(
            fsm_state="idle", active_brain="none",
            last_emotion="neutral", last_transcript="",
            latency_ms=0,
        )
        self._pipeline_config: dict = {}

    async def setup(self) -> None:
        # Load pipeline config
        config_path = Path("config/pipeline.yaml")
        if config_path.exists():
            with open(config_path) as f:
                self._pipeline_config = yaml.safe_load(f)

        # Connect memory
        await self._short_mem.connect()
        await self._long_mem.connect()

        # Register brains
        interaction = InteractionBrain(self._short_mem, self._long_mem)
        self._registry.register(interaction)
        self._registry.register(InteractionWriteBrain(interaction))
        self._registry.register(ReasoningBrain())
        self._registry.register(SentimentBrain())
        self._registry.register(ActionBrain())

        log.info("Orchestrator ready")

    async def teardown(self) -> None:
        await self._short_mem.disconnect()
        await self._long_mem.disconnect()

    def _get_pipeline(self, state: AgentStateEnum) -> list[str]:
        states = self._pipeline_config.get("states", {})
        return states.get(state.value, {}).get("pipeline", [])

    async def process_text(self, text: str, session_id: str | None = None) -> str:
        """Process a single text turn. Returns response text."""
        if session_id is None:
            session_id = str(uuid.uuid4())

        await self._fsm.transition(AgentStateEnum.LISTENING)
        await self._fsm.transition(AgentStateEnum.PROCESSING)

        context: dict = {
            "context": AgentContext(
                transcript=TranscriptEvent(text=text),
                memory=[],
                session_id=session_id,
            )
        }

        pipeline = self._get_pipeline(AgentStateEnum.PROCESSING)
        context = await self._registry.run_pipeline(pipeline, context)

        response_plan = context.get("response_plan")
        response_text = response_plan.text if response_plan else ""

        await self._fsm.transition(AgentStateEnum.SPEAKING)
        await self._fsm.transition(AgentStateEnum.IDLE)

        return response_text
```

**Step 4: Write agent/main.py (text REPL)**

```python
import asyncio
import logging
from agent.orchestrator import Orchestrator
from agent.config import settings

logging.basicConfig(level=settings.log_level)

async def main() -> None:
    orchestrator = Orchestrator()
    await orchestrator.setup()
    print("Mimi ready. Type to chat (Ctrl+C to exit).")
    session_id = "terminal"
    try:
        while True:
            text = input("\nYou: ").strip()
            if not text:
                continue
            response = await orchestrator.process_text(text, session_id=session_id)
            print(f"Mimi: {response}")
    except (KeyboardInterrupt, EOFError):
        print("\nBye!")
    finally:
        await orchestrator.teardown()

if __name__ == "__main__":
    asyncio.run(main())
```

**Step 5: Run integration test**

```bash
pytest tests/integration/test_text_pipeline.py -v
```
Expected: pass.

**Step 6: Run full test suite**

```bash
pytest tests/ -v
```
Expected: all pass.

**Step 7: Commit**

```bash
git add agent/orchestrator.py agent/main.py tests/integration/test_text_pipeline.py
git commit -m "feat: Orchestrator + text pipeline end-to-end"
```

**Phase 1 complete.** Run `python -m agent.main` to test interactively (requires Redis + Ollama).

---

## Phase 2 — Voice In/Out

### Task 13: InputBrain (VAD + STT)

**Files:**
- Create: `agent/brains/input_brain.py`
- Create: `tests/unit/test_input_brain.py`

**Prerequisites:** Install voice deps: `pip install -e ".[voice]"`

**Step 1: Write failing tests**

```python
# tests/unit/test_input_brain.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from agent.brains.input_brain import InputBrain

@pytest.mark.asyncio
async def test_input_brain_transcribes_audio(mocker):
    brain = InputBrain.__new__(InputBrain)
    brain.name = "input"

    mock_segment = MagicMock()
    mock_segment.text = " Hello Mimi "

    mocker.patch(
        "faster_whisper.WhisperModel.transcribe",
        return_value=([mock_segment], MagicMock(language="pt"))
    )

    # Pass raw PCM bytes
    ctx = {"raw_audio": b"\x00" * 16000 * 2}  # 1s 16kHz 16-bit
    result = await brain.transcribe(ctx)

    assert result["transcript"].text.strip() == "Hello Mimi"
    assert result["transcript"].confidence > 0
```

**Step 2: Run to confirm failure**

```bash
pytest tests/unit/test_input_brain.py -v
```

**Step 3: Write agent/brains/input_brain.py**

```python
import asyncio
import io
import logging
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from agent.brains.base import BrainBase
from agent.schemas import TranscriptEvent

log = logging.getLogger(__name__)
_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="whisper")


class InputBrain(BrainBase):
    name = "input"
    _MODEL_SIZE = "base"
    _SAMPLE_RATE = 16000

    def __init__(self) -> None:
        from faster_whisper import WhisperModel
        self._model = WhisperModel(self._MODEL_SIZE, device="cpu", compute_type="int8")
        log.info("InputBrain: whisper '%s' loaded", self._MODEL_SIZE)

    async def run(self, context: dict) -> dict:
        return await self.transcribe(context)

    async def transcribe(self, context: dict) -> dict:
        raw: bytes = context.get("raw_audio", b"")
        if not raw:
            context["transcript"] = TranscriptEvent(text="", confidence=0.0)
            return context

        loop = asyncio.get_running_loop()
        transcript = await loop.run_in_executor(_EXECUTOR, self._transcribe_sync, raw)
        context["transcript"] = transcript
        return context

    def _transcribe_sync(self, raw_audio: bytes) -> TranscriptEvent:
        audio = np.frombuffer(raw_audio, dtype=np.int16).astype(np.float32) / 32768.0
        segments, info = self._model.transcribe(audio, beam_size=5, language="pt")
        text = " ".join(seg.text for seg in segments).strip()
        # faster-whisper doesn't expose per-word confidence; use language prob as proxy
        confidence = float(info.language_probability)
        log.debug("STT: '%s' (%.2f)", text[:60], confidence)
        return TranscriptEvent(text=text, confidence=confidence)
```

**Step 4: Run tests**

```bash
pytest tests/unit/test_input_brain.py -v
```
Expected: all pass.

**Step 5: Commit**

```bash
git add agent/brains/input_brain.py tests/unit/test_input_brain.py
git commit -m "feat: InputBrain (VAD + Whisper STT)"
```

---

### Task 14: OutputBrain (TTS)

**Files:**
- Create: `agent/brains/output_brain.py`
- Create: `tests/unit/test_output_brain.py`

**Step 1: Write failing tests**

```python
# tests/unit/test_output_brain.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from agent.brains.output_brain import OutputBrain
from agent.schemas import ResponsePlan

@pytest.mark.asyncio
async def test_output_brain_skips_empty_response():
    brain = OutputBrain.__new__(OutputBrain)
    brain.name = "output"
    ctx = {"response_plan": ResponsePlan(text="", action="silence")}
    result = await brain.run(ctx)
    assert result.get("tts_played") is None

@pytest.mark.asyncio
async def test_output_brain_calls_synthesize(mocker):
    brain = OutputBrain.__new__(OutputBrain)
    brain.name = "output"
    brain._synthesize_and_play = AsyncMock()

    ctx = {"response_plan": ResponsePlan(text="Hello!", action="speak")}
    await brain.run(ctx)
    brain._synthesize_and_play.assert_called_once_with("Hello!")
```

**Step 2: Run to confirm failure**

```bash
pytest tests/unit/test_output_brain.py -v
```

**Step 3: Write agent/brains/output_brain.py**

```python
import asyncio
import logging
import io
import wave
import struct
from concurrent.futures import ThreadPoolExecutor
from agent.brains.base import BrainBase
from agent.schemas import ResponsePlan

log = logging.getLogger(__name__)
_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="tts")


class OutputBrain(BrainBase):
    name = "output"

    def __init__(self, voice: str = "en_US-lessac-medium") -> None:
        from piper import PiperVoice
        self._voice = PiperVoice.load(voice)
        log.info("OutputBrain: Piper voice loaded")

    async def run(self, context: dict) -> dict:
        plan: ResponsePlan | None = context.get("response_plan")
        if plan is None or plan.action == "silence" or not plan.text.strip():
            return context

        await self._synthesize_and_play(plan.text)
        context["tts_played"] = True
        return context

    async def _synthesize_and_play(self, text: str) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(_EXECUTOR, self._play_sync, text)

    def _play_sync(self, text: str) -> None:
        import sounddevice as sd
        import numpy as np

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(22050)
            self._voice.synthesize(text, wf)

        buf.seek(44)  # skip WAV header
        pcm = np.frombuffer(buf.read(), dtype=np.int16)
        sd.play(pcm.astype(np.float32) / 32768.0, samplerate=22050, blocking=True)
        log.debug("OutputBrain: played %d samples", len(pcm))
```

**Step 4: Run tests**

```bash
pytest tests/unit/test_output_brain.py -v
```
Expected: all pass (no actual audio played in test).

**Step 5: Commit**

```bash
git add agent/brains/output_brain.py tests/unit/test_output_brain.py
git commit -m "feat: OutputBrain (Piper TTS)"
```

---

### Task 15: Voice Loop Integration

**Files:**
- Modify: `agent/orchestrator.py`
- Create: `agent/audio/vad_loop.py`
- Create: `tests/integration/test_voice_pipeline.py`

**Step 1: Write failing integration test**

```python
# tests/integration/test_voice_pipeline.py
import pytest
import numpy as np
from unittest.mock import AsyncMock, patch, MagicMock
from agent.orchestrator import Orchestrator

@pytest.mark.asyncio
async def test_voice_turn_end_to_end(mocker):
    """Test voice turn: raw audio → STT → reasoning → TTS (mocked)"""
    mocker.patch(
        "agent.brains.input_brain.InputBrain._transcribe_sync",
        return_value=__import__("agent.schemas", fromlist=["TranscriptEvent"]).TranscriptEvent(
            text="what time is it", confidence=0.95
        )
    )
    mocker.patch(
        "agent.llm.ollama_client.OllamaClient.generate",
        side_effect=[
            '{"emotion": "curious", "intensity": 0.7}',
            "I don't have access to the current time.",
        ],
    )
    mocker.patch("aioredis.from_url", return_value=AsyncMock(
        rpush=AsyncMock(), lrange=AsyncMock(return_value=[]),
        ltrim=AsyncMock(), delete=AsyncMock(), close=AsyncMock()
    ))
    mocker.patch("agent.brains.output_brain.OutputBrain._synthesize_and_play", AsyncMock())

    orchestrator = Orchestrator(voice_enabled=True)
    await orchestrator.setup()

    raw_audio = np.zeros(16000, dtype=np.int16).tobytes()
    response = await orchestrator.process_audio(raw_audio)
    assert response is not None

    await orchestrator.teardown()
```

**Step 2: Run to confirm failure**

```bash
pytest tests/integration/test_voice_pipeline.py -v
```

**Step 3: Create agent/audio/vad_loop.py**

```python
import asyncio
import logging
import numpy as np
import sounddevice as sd
import webrtcvad

log = logging.getLogger(__name__)
_SAMPLE_RATE = 16000
_FRAME_MS = 30
_FRAME_SAMPLES = int(_SAMPLE_RATE * _FRAME_MS / 1000)  # 480 samples


class VADLoop:
    """Captures audio via sounddevice, uses WebRTC VAD to detect speech segments."""

    def __init__(self, aggressiveness: int = 2) -> None:
        self._vad = webrtcvad.Vad(aggressiveness)
        self._queue: asyncio.Queue[bytes] = asyncio.Queue()

    def _audio_callback(self, indata: np.ndarray, frames: int, time, status) -> None:
        if status:
            log.warning("VAD audio status: %s", status)
        pcm = (indata[:, 0] * 32768).astype(np.int16).tobytes()
        self._queue.put_nowait(pcm)

    async def capture_utterance(self, silence_frames: int = 20) -> bytes:
        """Block until a complete utterance is captured. Returns raw PCM bytes."""
        buffer: list[bytes] = []
        in_speech = False
        silence_count = 0

        with sd.InputStream(
            samplerate=_SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=_FRAME_SAMPLES,
            callback=self._audio_callback,
        ):
            log.debug("VAD: listening...")
            while True:
                frame = await asyncio.wait_for(self._queue.get(), timeout=10.0)
                is_speech = self._vad.is_speech(frame, _SAMPLE_RATE)

                if is_speech:
                    in_speech = True
                    silence_count = 0
                    buffer.append(frame)
                elif in_speech:
                    buffer.append(frame)
                    silence_count += 1
                    if silence_count >= silence_frames:
                        log.debug("VAD: end of speech (%d frames)", len(buffer))
                        break

        return b"".join(buffer)
```

**Step 4: Update agent/orchestrator.py to add voice support**

Add `voice_enabled` flag and `process_audio` method. Add `input_brain` and `output_brain` registration when voice is enabled.

Key additions to `Orchestrator`:
```python
# In __init__:
self._voice_enabled = False

# In setup(voice_enabled=False):
self._voice_enabled = voice_enabled
if voice_enabled:
    from agent.brains.input_brain import InputBrain
    from agent.brains.output_brain import OutputBrain
    self._registry.register(InputBrain())
    self._registry.register(OutputBrain())

# New method:
async def process_audio(self, raw_audio: bytes, session_id: str | None = None) -> str:
    if session_id is None:
        session_id = str(uuid.uuid4())
    await self._fsm.transition(AgentStateEnum.LISTENING)
    
    # STT via InputBrain
    ctx = {"raw_audio": raw_audio}
    ctx = await self._registry.get("input").transcribe(ctx)
    transcript = ctx["transcript"]
    
    await self._fsm.transition(AgentStateEnum.PROCESSING)
    context: dict = {
        "context": AgentContext(
            transcript=transcript,
            memory=[],
            session_id=session_id,
        )
    }
    pipeline = self._get_pipeline(AgentStateEnum.PROCESSING)
    context = await self._registry.run_pipeline(pipeline, context)
    
    await self._fsm.transition(AgentStateEnum.SPEAKING)
    output_pipeline = self._get_pipeline(AgentStateEnum.SPEAKING)
    context = await self._registry.run_pipeline(output_pipeline, context)
    
    await self._fsm.transition(AgentStateEnum.IDLE)
    
    plan = context.get("response_plan")
    return plan.text if plan else ""
```

**Step 5: Run tests**

```bash
pytest tests/ -v
```
Expected: all pass.

**Step 6: Commit**

```bash
git add agent/audio/vad_loop.py agent/orchestrator.py tests/integration/test_voice_pipeline.py
git commit -m "feat: voice pipeline (VAD + STT + TTS integration)"
```

---

## Phase 3 — Docker + Dashboard

### Task 16: Docker Compose (Redis)

**Files:**
- Create: `docker/docker-compose.yml`
- Create: `docker/.env.docker`

**Step 1: Write docker/docker-compose.yml**

```yaml
version: "3.9"

services:
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --save 60 1 --loglevel warning

volumes:
  redis_data:
```

**Step 2: Start Redis**

```bash
docker compose -f docker/docker-compose.yml up -d redis
```
Expected: Redis running on port 6379.

**Step 3: Test Redis connection**

```bash
python -c "import asyncio, aioredis; asyncio.run(aioredis.from_url('redis://localhost:6379').ping())" && echo "OK"
```
Expected: `OK`.

**Step 4: Commit**

```bash
git add docker/
git commit -m "infra: Docker Compose for Redis"
```

---

### Task 17: Dashboard (Monitoring-Only)

**Files:**
- Create: `dashboard/server.py`
- Create: `dashboard/static/index.html`
- Create: `tests/unit/test_dashboard.py`

**Step 1: Write failing tests**

```python
# tests/unit/test_dashboard.py
import pytest
from httpx import AsyncClient, ASGITransport
from dashboard.server import create_app
from agent.schemas import AgentStateSnapshot

@pytest.mark.asyncio
async def test_dashboard_health():
    app = create_app(state_getter=lambda: AgentStateSnapshot(
        fsm_state="idle", active_brain="none",
        last_emotion="neutral", last_transcript="",
        latency_ms=0
    ))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200

@pytest.mark.asyncio
async def test_dashboard_state_endpoint():
    snapshot = AgentStateSnapshot(
        fsm_state="processing", active_brain="reasoning",
        last_emotion="curious", last_transcript="test",
        latency_ms=120
    )
    app = create_app(state_getter=lambda: snapshot)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/state")
    assert resp.status_code == 200
    assert resp.json()["fsm_state"] == "processing"
```

**Step 2: Run to confirm failure**

```bash
pytest tests/unit/test_dashboard.py -v
```

**Step 3: Write dashboard/server.py**

```python
import asyncio
import json
import logging
from collections.abc import Callable
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from agent.schemas import AgentStateSnapshot

log = logging.getLogger(__name__)


def create_app(state_getter: Callable[[], AgentStateSnapshot]) -> FastAPI:
    app = FastAPI(title="Mimi Dashboard", docs_url=None)
    connections: list[WebSocket] = []

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/state")
    async def get_state():
        return state_getter().model_dump()

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket):
        await ws.accept()
        connections.append(ws)
        log.info("Dashboard client connected (%d total)", len(connections))
        try:
            while True:
                await ws.receive_text()  # keep alive; client can ping
        except WebSocketDisconnect:
            connections.remove(ws)
            log.info("Dashboard client disconnected")

    async def broadcast_state(state: AgentStateSnapshot) -> None:
        if not connections:
            return
        data = state.model_dump_json()
        dead = []
        for ws in connections:
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            connections.remove(ws)

    app.state.broadcast = broadcast_state
    app.mount("/", StaticFiles(directory="dashboard/static", html=True), name="static")
    return app
```

**Step 4: Write dashboard/static/index.html** (minimal monitoring UI)

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Mimi Dashboard</title>
  <style>
    body { font-family: monospace; background: #0d0d0d; color: #e0e0e0; padding: 2rem; }
    h1 { color: #7ec8e3; }
    .card { background: #1a1a1a; border: 1px solid #333; padding: 1rem; margin: 0.5rem 0; border-radius: 4px; }
    .state { font-size: 2rem; font-weight: bold; }
    .idle { color: #888; }
    .listening { color: #6fbe6f; }
    .processing { color: #f0a500; }
    .speaking { color: #7ec8e3; }
    .error { color: #e05c5c; }
    .label { color: #888; font-size: 0.8rem; text-transform: uppercase; margin-bottom: 0.3rem; }
  </style>
</head>
<body>
  <h1>Mimi — Monitor</h1>
  <div class="card">
    <div class="label">State</div>
    <div class="state" id="state">connecting...</div>
  </div>
  <div class="card">
    <div class="label">Active Brain</div>
    <div id="brain">—</div>
  </div>
  <div class="card">
    <div class="label">Last Transcript</div>
    <div id="transcript">—</div>
  </div>
  <div class="card">
    <div class="label">Emotion</div>
    <div id="emotion">—</div>
  </div>
  <div class="card">
    <div class="label">Latency</div>
    <div id="latency">—</div>
  </div>
  <script>
    const el = id => document.getElementById(id);
    const ws = new WebSocket(`ws://${location.host}/ws`);
    ws.onmessage = e => {
      const d = JSON.parse(e.data);
      el("state").textContent = d.fsm_state;
      el("state").className = `state ${d.fsm_state}`;
      el("brain").textContent = d.active_brain;
      el("transcript").textContent = d.last_transcript || "—";
      el("emotion").textContent = `${d.last_emotion}`;
      el("latency").textContent = `${d.latency_ms}ms`;
    };
    ws.onclose = () => el("state").textContent = "disconnected";
  </script>
</body>
</html>
```

**Step 5: Run tests**

```bash
pytest tests/unit/test_dashboard.py -v
```
Expected: all pass.

**Step 6: Commit**

```bash
git add dashboard/ tests/unit/test_dashboard.py
git commit -m "feat: monitoring-only dashboard (FastAPI + WebSocket)"
```

---

## Phase 4 — Polish & Observability

### Task 18: Per-Brain Latency Tracking

**Files:**
- Modify: `agent/brains/base.py`
- Modify: `agent/orchestrator.py`
- Modify: `agent/schemas.py`

Add timing to `BrainRegistry.run_pipeline`: wrap each brain call with `time.perf_counter()`. Store results in `context["_timings"]`. Orchestrator updates `AgentStateSnapshot.latency_ms` with total time and broadcasts to dashboard.

**Step 1: Update BrainRegistry.run_pipeline**

```python
import time

async def run_pipeline(self, pipeline: list[str], context: dict) -> dict:
    timings: dict[str, int] = {}
    for name in pipeline:
        brain = self.get(name)
        t0 = time.perf_counter()
        context = await brain.run(context)
        timings[name] = int((time.perf_counter() - t0) * 1000)
    context["_timings"] = timings
    return context
```

**Step 2: Run all tests**

```bash
pytest tests/ -v
```
Expected: all pass.

**Step 3: Commit**

```bash
git add agent/brains/base.py agent/orchestrator.py
git commit -m "feat: per-brain latency tracking"
```

---

### Task 19: Health Checks & Startup Verification

**Files:**
- Create: `agent/health.py`
- Modify: `agent/main.py`
- Create: `tests/unit/test_health.py`

**Step 1: Write agent/health.py**

```python
import asyncio
import logging
from dataclasses import dataclass
from agent.config import settings

log = logging.getLogger(__name__)

@dataclass
class BrainHealth:
    name: str
    ok: bool
    message: str


async def check_redis(redis_url: str) -> BrainHealth:
    try:
        import aioredis
        r = await aioredis.from_url(redis_url)
        await r.ping()
        await r.close()
        return BrainHealth("redis", True, "pong")
    except Exception as e:
        return BrainHealth("redis", False, str(e))


async def check_ollama(host: str, model: str) -> BrainHealth:
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as c:
            resp = await c.get(f"{host}/api/tags")
            resp.raise_for_status()
        return BrainHealth("ollama", True, f"model={model}")
    except Exception as e:
        return BrainHealth("ollama", False, str(e))


async def run_health_checks() -> list[BrainHealth]:
    results = await asyncio.gather(
        check_redis(settings.redis_url),
        check_ollama(settings.ollama_host, settings.ollama_model),
        return_exceptions=False,
    )
    for r in results:
        icon = "✓" if r.ok else "✗"
        log.info("%s %-20s %s", icon, r.name, r.message)
    return list(results)
```

**Step 2: Add health check to main.py startup**

```python
from agent.health import run_health_checks

async def main():
    print("Running health checks...")
    checks = await run_health_checks()
    failed = [c for c in checks if not c.ok]
    if failed:
        print(f"⚠ {len(failed)} check(s) failed: {[c.name for c in failed]}")
    else:
        print("✅ All systems go")
    # ... rest of main
```

**Step 3: Run all tests**

```bash
pytest tests/ -v
```
Expected: all pass.

**Step 4: Final full test run**

```bash
pytest tests/ -v --tb=short
```

**Step 5: Commit**

```bash
git add agent/health.py agent/main.py tests/
git commit -m "feat: startup health checks (Redis + Ollama)"
```

---

## Final Verification

```bash
# All tests pass
pytest tests/ -v

# Linting clean
ruff check agent/ dashboard/ tests/

# Start Redis
docker compose -f docker/docker-compose.yml up -d

# Run agent (text mode)
python -m agent.main

# Run dashboard (separate terminal)
uvicorn dashboard.server:app --host 0.0.0.0 --port 8080
# Open http://localhost:8080
```

---

## Out of Scope (deferred)

- Avatar / 3D VRM control
- Multiple simultaneous sessions
- Distributed brain processes
- Cloud fallback LLM
- Voice cloning / custom voices
- Fine-tuned models
