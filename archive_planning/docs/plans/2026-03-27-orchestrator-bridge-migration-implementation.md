# Orchestrator Bridge Migration — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Activate the 7-brain AgentOrchestrator as the primary system by creating a Bridge between WebAvatar (WebSocket) and EventBus, wiring OllamaProvider for LLM, PiperProvider for TTS, and enabling audio capture.

**Architecture:** A new `OrchestratorBridge` class translates between WebSocket messages (via WebAvatar) and EventBus events. WebAvatar stays as the WS client, Orchestrator manages brains, and the Bridge connects both. Audio capture runs in parallel via InputBrain.

**Tech Stack:** Python 3.10+, asyncio, websockets, aiohttp, piper-tts, sounddevice, faster-whisper, EventBus (custom pub/sub)

**Design Doc:** `docs/plans/2026-03-27-orchestrator-bridge-migration-design.md`

---

### Task 1: Fix `avatar_control` WebSocket routing in server.js

**Files:**
- Modify: `web_avatar/server.js:472` (add case before `default:`)

**Step 1: Add `avatar_control` case to switch statement**

In `web_avatar/server.js`, find the `default:` case in the message switch (line 472) and add a new case before it:

```javascript
      case 'avatar_control':
        // Forward emotion/gesture/speaking commands from Python agent to frontend
        console.log('[AVATAR] Control message:', msg.emotion || msg.gesture || 'unknown');
        wss.clients.forEach(client => {
          if (client.readyState === WebSocket.OPEN && client !== ws) {
            client.send(JSON.stringify(msg));
          }
        });
        break;
```

**Step 2: Verify manually (no automated test needed for this)**

This is a one-line routing fix. Verify by checking the switch statement reads correctly.

**Step 3: Commit**

```bash
git add web_avatar/server.js
git commit -m "fix: add avatar_control handler to WebSocket server"
```

---

### Task 2: Create `OrchestratorBridge` class

**Files:**
- Create: `agent/bridge.py`
- Test: `tests/unit/test_bridge.py`

**Step 1: Write failing tests for the Bridge**

Create `tests/unit/test_bridge.py`:

```python
"""Unit tests for OrchestratorBridge."""
import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from agent.core.messaging import EventBus, EventType, AgentEvent, SharedAgentState


class MockWebAvatar:
    """Mock WebAvatar for testing."""
    def __init__(self):
        self.commands_sent = []
        self.connected = True
        self.message_callback = None
    
    async def send_command(self, data: dict):
        self.commands_sent.append(data)
    
    async def set_expression(self, name: str):
        self.commands_sent.append({"type": "set_expression", "expression": name})
    
    async def speak_start(self):
        self.commands_sent.append({"type": "set_speaking", "speaking": True})
    
    async def speak_end(self):
        self.commands_sent.append({"type": "set_speaking", "speaking": False})
    
    def set_message_callback(self, callback):
        self.message_callback = callback


@pytest.fixture
async def event_bus():
    bus = EventBus()
    await bus.start()
    yield bus
    await bus.stop()


@pytest.fixture
async def shared_state():
    return SharedAgentState()


@pytest.fixture
def mock_avatar():
    return MockWebAvatar()


@pytest.fixture
async def bridge(event_bus, mock_avatar):
    from agent.bridge import OrchestratorBridge
    b = OrchestratorBridge(avatar=mock_avatar, event_bus=event_bus)
    yield b


class TestBridgeInit:
    def test_bridge_creates(self, bridge):
        assert bridge is not None
    
    def test_bridge_has_avatar(self, bridge, mock_avatar):
        assert bridge.avatar is mock_avatar
    
    def test_bridge_has_event_bus(self, bridge, event_bus):
        assert bridge.event_bus is event_bus


class TestBridgeInbound:
    """Test WS message → EventBus event translation."""
    
    @pytest.mark.asyncio
    async def test_text_input_publishes_transcription_complete(self, bridge, event_bus):
        """When bridge receives text input, it publishes TRANSCRIPTION_COMPLETE."""
        await bridge.start()
        
        captured = []
        
        async def capture(event):
            captured.append(event)
        
        event_bus.subscribe(EventType.TRANSCRIPTION_COMPLETE)(capture)
        
        await bridge.handle_text_input("Olá Mimi")
        await asyncio.sleep(0.2)
        
        assert len(captured) == 1
        assert captured[0].payload["transcript"] == "Olá Mimi"
        assert captured[0].payload["confidence"] == 1.0
        assert captured[0].source_brain == "bridge"


class TestBridgeOutbound:
    """Test EventBus event → WS message translation."""
    
    @pytest.mark.asyncio
    async def test_response_ready_sends_agent_response(self, bridge, event_bus, mock_avatar):
        """When RESPONSE_READY fires, bridge sends agent_response via WebAvatar."""
        await bridge.start()
        
        event = AgentEvent(
            type=EventType.RESPONSE_READY,
            source_brain="reasoning_brain",
            payload={"response": "Olá! Como posso ajudar?"}
        )
        await event_bus.publish(event)
        await asyncio.sleep(0.2)
        
        response_cmds = [c for c in mock_avatar.commands_sent if c.get("type") == "agent_response"]
        assert len(response_cmds) == 1
        assert response_cmds[0]["text"] == "Olá! Como posso ajudar?"
    
    @pytest.mark.asyncio
    async def test_animation_queued_sends_avatar_control(self, bridge, event_bus, mock_avatar):
        """When ANIMATION_QUEUED fires, bridge sends avatar_control via WebAvatar."""
        await bridge.start()
        
        event = AgentEvent(
            type=EventType.ANIMATION_QUEUED,
            source_brain="avatar_brain",
            payload={"animation": "smile", "sentiment": "happy"}
        )
        await event_bus.publish(event)
        await asyncio.sleep(0.2)
        
        ctrl_cmds = [c for c in mock_avatar.commands_sent if c.get("type") == "avatar_control"]
        assert len(ctrl_cmds) == 1
        assert ctrl_cmds[0]["emotion"] == "happy"
    
    @pytest.mark.asyncio
    async def test_tts_started_calls_speak_start(self, bridge, event_bus, mock_avatar):
        """When TTS_STARTED fires, bridge calls speak_start."""
        await bridge.start()
        
        event = AgentEvent(
            type=EventType.TTS_STARTED,
            source_brain="output_brain",
            payload={"text": "Hello"}
        )
        await event_bus.publish(event)
        await asyncio.sleep(0.2)
        
        speak_cmds = [c for c in mock_avatar.commands_sent if c.get("type") == "set_speaking" and c.get("speaking")]
        assert len(speak_cmds) == 1
    
    @pytest.mark.asyncio
    async def test_audio_complete_calls_speak_end(self, bridge, event_bus, mock_avatar):
        """When AUDIO_COMPLETE fires, bridge calls speak_end."""
        await bridge.start()
        
        event = AgentEvent(
            type=EventType.AUDIO_COMPLETE,
            source_brain="output_brain",
            payload={"audio": b"", "duration_ms": 100}
        )
        await event_bus.publish(event)
        await asyncio.sleep(0.2)
        
        speak_cmds = [c for c in mock_avatar.commands_sent if c.get("type") == "set_speaking" and not c.get("speaking")]
        assert len(speak_cmds) == 1
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_bridge.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent.bridge'`

**Step 3: Implement OrchestratorBridge**

Create `agent/bridge.py`:

```python
"""
OrchestratorBridge: translates between WebAvatar (WebSocket) and EventBus.

Inbound: WS messages → EventBus events
Outbound: EventBus events → WS messages via WebAvatar
"""

import asyncio
import logging
from typing import Any

from agent.core.messaging import EventBus, EventType, AgentEvent

logger = logging.getLogger(__name__)


class OrchestratorBridge:
    """Connects WebAvatar (WS client) to the EventBus (brain communication)."""
    
    def __init__(self, avatar: Any, event_bus: EventBus):
        self.avatar = avatar
        self.event_bus = event_bus
        self._running = False
    
    async def start(self) -> None:
        """Subscribe to EventBus events for outbound translation."""
        self._running = True
        
        # Outbound: EventBus → WebAvatar
        self.event_bus.subscribe(EventType.RESPONSE_READY)(self._on_response_ready)
        self.event_bus.subscribe(EventType.ANIMATION_QUEUED)(self._on_animation_queued)
        self.event_bus.subscribe(EventType.GESTURE_QUEUED)(self._on_gesture_queued)
        self.event_bus.subscribe(EventType.TTS_STARTED)(self._on_tts_started)
        self.event_bus.subscribe(EventType.AUDIO_COMPLETE)(self._on_audio_complete)
        self.event_bus.subscribe(EventType.EMOTION_DETECTED)(self._on_emotion_detected)
        
        logger.info("OrchestratorBridge started — subscribed to EventBus")
    
    async def stop(self) -> None:
        """Stop the bridge."""
        self._running = False
        logger.info("OrchestratorBridge stopped")
    
    # ===== INBOUND: WS → EventBus =====
    
    async def handle_text_input(self, text: str, source: str = "web") -> None:
        """Called when text arrives via WebSocket. Publishes TRANSCRIPTION_COMPLETE."""
        event = AgentEvent(
            type=EventType.TRANSCRIPTION_COMPLETE,
            source_brain="bridge",
            payload={
                "transcript": text,
                "confidence": 1.0,
                "source": source,
            }
        )
        await self.event_bus.publish(event)
        logger.info(f"Bridge published TRANSCRIPTION_COMPLETE: {text[:50]}...")
    
    # ===== OUTBOUND: EventBus → WS =====
    
    async def _on_response_ready(self, event: AgentEvent) -> None:
        """Send agent response back through WebSocket."""
        response = event.payload.get("response", "")
        if response:
            await self.avatar.send_command({
                "type": "agent_response",
                "text": response,
            })
            logger.info(f"Bridge sent agent_response: {response[:50]}...")
    
    async def _on_animation_queued(self, event: AgentEvent) -> None:
        """Send avatar emotion/animation control."""
        sentiment = event.payload.get("sentiment", "neutral")
        animation = event.payload.get("animation", "neutral")
        await self.avatar.send_command({
            "type": "avatar_control",
            "emotion": sentiment,
            "gesture": animation,
        })
    
    async def _on_gesture_queued(self, event: AgentEvent) -> None:
        """Send avatar gesture control."""
        gesture = event.payload.get("gesture", "idle")
        intensity = event.payload.get("intensity", 0.0)
        await self.avatar.send_command({
            "type": "avatar_control",
            "gesture": gesture,
            "intensity": intensity,
        })
    
    async def _on_tts_started(self, event: AgentEvent) -> None:
        """Notify avatar that speech has started."""
        await self.avatar.speak_start()
    
    async def _on_audio_complete(self, event: AgentEvent) -> None:
        """Notify avatar that speech has ended."""
        await self.avatar.speak_end()
    
    async def _on_emotion_detected(self, event: AgentEvent) -> None:
        """Set avatar expression based on detected emotion."""
        sentiment = event.payload.get("sentiment", "neutral")
        await self.avatar.set_expression(sentiment)
```

**Step 4: Run tests**

Run: `pytest tests/unit/test_bridge.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add agent/bridge.py tests/unit/test_bridge.py
git commit -m "feat: add OrchestratorBridge for WS-EventBus translation"
```

---

### Task 3: Modify WebAvatar to support Bridge message interception

**Files:**
- Modify: `agent/avatar/interface.py`
- Test: `tests/unit/test_bridge.py` (add integration tests)

**Step 1: Add message callback to WebAvatar**

In `agent/avatar/interface.py`, add to the `WebAvatar.__init__`:

```python
self.message_callback = None  # Bridge callback for incoming messages
```

Add a setter method:

```python
def set_message_callback(self, callback):
    """Set callback for incoming WebSocket messages. Used by Bridge."""
    self.message_callback = callback
```

**Step 2: Modify `_listen_loop` to call Bridge callback**

Replace the agent_input/chat handling in `_listen_loop` with a callback that the Bridge can intercept. The Bridge will handle the message instead of WebAvatar calling `agent.handle_input()` directly.

In `_listen_loop`, after parsing the message, add:

```python
# If bridge callback is set, delegate to it
if self.message_callback:
    await self.message_callback(data)
    continue
```

This goes BEFORE the existing `msg_type == "chat"` and `msg_type == "agent_input"` checks. When the Bridge is connected, it handles all incoming messages. When no bridge is set (backwards compat), the old AgentCore path still works.

**Step 3: Run existing tests**

Run: `pytest tests/ -v --ignore=tests/web_avatar -x -q`
Expected: Existing tests still pass

**Step 4: Commit**

```bash
git add agent/avatar/interface.py
git commit -m "feat: add message callback to WebAvatar for Bridge interception"
```

---

### Task 4: Modify Orchestrator to accept LLM provider for ReasoningBrain

**Files:**
- Modify: `agent/orchestrator.py`
- Test: `tests/integration/test_orchestrator_with_llm.py` (already exists, verify it passes)

**Step 1: Add `llm_provider` parameter to AgentOrchestrator.__init__**

In `agent/orchestrator.py`, add `llm_provider` to the constructor:

```python
def __init__(self,
             user_id: str = "user_1",
             session_id: Optional[str] = None,
             tts_provider: Optional[TTSProvider] = None,
             llm_provider: Optional['LLMProvider'] = None):
```

And inject it into ReasoningBrain:

```python
self.reasoning_brain = ReasoningBrain(
    brain_id="reasoning_brain",
    event_bus=self.event_bus,
    shared_state=self.shared_state,
    llm_provider=llm_provider,
)
```

**Step 2: Run existing integration test**

Run: `pytest tests/integration/test_orchestrator_with_llm.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add agent/orchestrator.py
git commit -m "feat: inject LLM provider into Orchestrator for ReasoningBrain"
```

---

### Task 5: Wire InputBrain audio capture (sounddevice + VAD + STT)

**Files:**
- Modify: `agent/brains/input_brain.py`

**Step 1: Implement `process()` with audio capture loop**

Replace the placeholder `process()` in InputBrain with a real audio capture loop using sounddevice:

```python
async def process(self) -> None:
    """Main loop: capture audio from mic and process with VAD + STT."""
    try:
        import sounddevice as sd
    except ImportError:
        logger.warning(f"[{self.brain_id}] sounddevice not available, audio capture disabled")
        while self._running:
            await asyncio.sleep(1.0)
        return
    
    logger.info(f"[{self.brain_id}] Starting audio capture loop")
    sample_rate = 16000
    frame_size = int(sample_rate * 0.02)  # 20ms frames
    
    try:
        stream = sd.InputStream(
            samplerate=sample_rate,
            channels=1,
            dtype='int16',
            blocksize=frame_size,
        )
        stream.start()
        
        while self._running:
            data, overflowed = stream.read(frame_size)
            if overflowed:
                logger.warning("Audio buffer overflow")
            
            audio_bytes = data.tobytes()
            await self.handle_audio_frame(audio_bytes)
        
        stream.stop()
        stream.close()
    except Exception as e:
        logger.error(f"[{self.brain_id}] Audio capture error: {e}")
        # Fall back to idle loop — text input still works via Bridge
        while self._running:
            await asyncio.sleep(1.0)
```

Note: This gracefully falls back if sounddevice is not installed. Text input via Bridge still works.

**Step 2: Run existing tests**

Run: `pytest tests/unit/ -v -x -q`
Expected: Existing tests still pass

**Step 3: Commit**

```bash
git add agent/brains/input_brain.py
git commit -m "feat: wire InputBrain audio capture with sounddevice fallback"
```

---

### Task 6: Rewrite `main.py` to use Orchestrator + Bridge

**Files:**
- Modify: `agent/main.py`

**Step 1: Rewrite main.py**

Replace the entire content of `agent/main.py`:

```python
"""Entry point do agente Mimi — Orchestrator mode."""

from __future__ import annotations

import asyncio
import logging
import sys

from agent.avatar.interface import DummyAvatar, WebAvatar
from agent.bridge import OrchestratorBridge
from agent.orchestrator import AgentOrchestrator
from agent.llm.config import OllamaConfig
from agent.llm.ollama_provider import OllamaProvider
from agent.config import (
    AVATAR_TYPE, LLM_MODEL, WEBSOCKET_HOST, WEBSOCKET_PORT,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# Read Ollama config from environment
import os
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "https://api.ollama.ai")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")


def create_avatar() -> DummyAvatar | WebAvatar:
    """Create avatar instance based on config."""
    if AVATAR_TYPE == "web":
        return WebAvatar(host=WEBSOCKET_HOST, port=WEBSOCKET_PORT)
    else:
        return DummyAvatar()


def create_tts_provider():
    """Create TTS provider with graceful fallback."""
    try:
        from agent.output.piper_provider import PiperProvider
        from agent.output.config import PiperConfig
        config = PiperConfig(provider="piper", model="pt_PT")
        provider = PiperProvider(config)
        logger.info("PiperTTS provider initialized")
        return provider
    except Exception as e:
        logger.warning(f"PiperTTS not available ({e}), OutputBrain will have no TTS")
        return None


def create_llm_provider():
    """Create Ollama LLM provider."""
    try:
        # Build the Ollama API URL with key if present
        host = OLLAMA_HOST
        config = OllamaConfig(
            provider="ollama",
            model=LLM_MODEL,
            host=host,
            temperature=0.7,
        )
        provider = OllamaProvider(config)
        logger.info(f"OllamaProvider initialized (model={LLM_MODEL}, host={host})")
        return provider
    except Exception as e:
        logger.warning(f"OllamaProvider not available ({e}), ReasoningBrain will use fallback")
        return None


async def main() -> None:
    """Initialize and run the Mimi agent with full Orchestrator."""
    print("=" * 50)
    print("  Mimi – Agente de IA (Orchestrator Mode)")
    print("=" * 50)
    logger.info("Starting agent in Orchestrator mode...")

    # Components
    avatar = create_avatar()
    tts_provider = create_tts_provider()
    llm_provider = create_llm_provider()

    # Create Orchestrator with all dependencies
    orchestrator = AgentOrchestrator(
        tts_provider=tts_provider,
        llm_provider=llm_provider,
    )

    # Create Bridge (WS ↔ EventBus)
    bridge = OrchestratorBridge(
        avatar=avatar,
        event_bus=orchestrator.event_bus,
    )

    # Set Bridge as message handler on WebAvatar
    if isinstance(avatar, WebAvatar):
        async def on_ws_message(data: dict):
            """Bridge callback for incoming WebSocket messages."""
            msg_type = data.get("type")
            if msg_type in ("agent_input", "chat"):
                text = data.get("text") or data.get("message", "")
                if text:
                    await bridge.handle_text_input(text, source="web")
            elif msg_type == "state":
                pass  # State updates handled by WebAvatar natively
            else:
                logger.debug(f"Unhandled WS message type in bridge: {msg_type}")
        
        avatar.set_message_callback(on_ws_message)

    try:
        # Connect WebSocket
        await avatar.connect()
        logger.info("Avatar connected")

        # Load default model
        if isinstance(avatar, WebAvatar):
            await avatar.load_model_from_path("vroid_model/Mimi.vrm")
            logger.info("Default model Mimi.vrm loaded")

        # Initialize and start Orchestrator (all 7 brains)
        await orchestrator.initialize()
        await orchestrator.start()
        logger.info("Orchestrator started with all brains")

        # Start Bridge
        await bridge.start()
        logger.info("Bridge connected: WebSocket ↔ EventBus")

        logger.info("System ready. Waiting for input...")

        # Keep alive
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Interrupt received")
    except Exception as e:
        logger.error(f"Daemon error: {e}", exc_info=True)
    finally:
        await bridge.stop()
        await orchestrator.stop()
        await avatar.disconnect()
        if llm_provider and hasattr(llm_provider, 'close'):
            await llm_provider.close()
        logger.info("Daemon stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
```

**Step 2: Run tests**

Run: `pytest tests/ -v --ignore=tests/web_avatar -x -q`
Expected: All existing tests still pass

**Step 3: Commit**

```bash
git add agent/main.py
git commit -m "feat: rewrite main.py to use Orchestrator + Bridge"
```

---

### Task 7: Integration test — full pipeline end-to-end

**Files:**
- Create: `tests/integration/test_orchestrator_bridge_e2e.py`

**Step 1: Write E2E test**

```python
"""
End-to-end test: text input → Bridge → EventBus → Brains → response.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock
from agent.orchestrator import AgentOrchestrator
from agent.bridge import OrchestratorBridge
from agent.core.messaging import EventBus, EventType, AgentEvent


class FakeAvatar:
    """Minimal fake avatar for E2E testing."""
    def __init__(self):
        self.commands_sent = []
        self.connected = True
        self.message_callback = None
    
    async def send_command(self, data):
        self.commands_sent.append(data)
    
    async def set_expression(self, name):
        self.commands_sent.append({"type": "set_expression", "expression": name})
    
    async def speak_start(self):
        self.commands_sent.append({"type": "set_speaking", "speaking": True})
    
    async def speak_end(self):
        self.commands_sent.append({"type": "set_speaking", "speaking": False})
    
    def set_message_callback(self, callback):
        self.message_callback = callback


@pytest.mark.asyncio
async def test_text_input_produces_response():
    """Full pipeline: text → Bridge → Orchestrator → response back through Bridge."""
    avatar = FakeAvatar()
    
    # No LLM provider — ReasoningBrain will use fallback "Echo: ..."
    orchestrator = AgentOrchestrator(
        user_id="test", session_id="test_e2e",
        tts_provider=None,  # No TTS — OutputBrain will handle gracefully
        llm_provider=None,  # Fallback echo mode
    )
    
    bridge = OrchestratorBridge(
        avatar=avatar,
        event_bus=orchestrator.event_bus,
    )
    
    await orchestrator.initialize()
    await orchestrator.start()
    await bridge.start()
    
    # Send text input through bridge
    await bridge.handle_text_input("Olá Mimi")
    
    # Wait for event chain to complete
    await asyncio.sleep(1.0)
    
    # Verify response was sent back through avatar
    response_cmds = [c for c in avatar.commands_sent if c.get("type") == "agent_response"]
    assert len(response_cmds) >= 1, f"Expected agent_response, got: {avatar.commands_sent}"
    assert "Echo:" in response_cmds[0].get("text", "") or len(response_cmds[0].get("text", "")) > 0
    
    await orchestrator.stop()


@pytest.mark.asyncio
async def test_emotion_reaches_avatar():
    """Full pipeline: text → sentiment analysis → emotion → avatar control."""
    avatar = FakeAvatar()
    
    orchestrator = AgentOrchestrator(
        user_id="test", session_id="test_emotion",
        tts_provider=None,
        llm_provider=None,
    )
    
    bridge = OrchestratorBridge(
        avatar=avatar,
        event_bus=orchestrator.event_bus,
    )
    
    await orchestrator.initialize()
    await orchestrator.start()
    await bridge.start()
    
    await bridge.handle_text_input("Olá Mimi")
    await asyncio.sleep(1.0)
    
    # Check that avatar received some control commands (expression or avatar_control)
    control_cmds = [c for c in avatar.commands_sent 
                    if c.get("type") in ("avatar_control", "set_expression")]
    assert len(control_cmds) >= 1, f"Expected avatar control, got: {avatar.commands_sent}"
    
    await orchestrator.stop()
```

**Step 2: Run E2E test**

Run: `pytest tests/integration/test_orchestrator_bridge_e2e.py -v`
Expected: PASS (with echo mode — no LLM needed)

**Step 3: Commit**

```bash
git add tests/integration/test_orchestrator_bridge_e2e.py
git commit -m "test: add E2E test for orchestrator bridge pipeline"
```

---

### Task 8: Run full test suite and verify

**Step 1: Run all tests**

Run: `pytest tests/ -v --ignore=tests/web_avatar -x`
Expected: All tests PASS (or pre-existing failures noted)

**Step 2: Run linting**

Run: `ruff check agent/ --fix && ruff format agent/`
Expected: Clean or auto-fixed

**Step 3: Final commit if any lint fixes**

```bash
git add -A
git commit -m "chore: lint and format fixes"
```

---

## Execution Order Summary

1. **Task 1** — Fix server.js `avatar_control` routing (quick, independent)
2. **Task 2** — Create OrchestratorBridge (new file + tests)
3. **Task 3** — Modify WebAvatar for Bridge callback
4. **Task 4** — Modify Orchestrator to accept LLM provider
5. **Task 5** — Wire InputBrain audio capture
6. **Task 6** — Rewrite main.py
7. **Task 7** — E2E integration test
8. **Task 8** — Full test suite + lint
