# Orchestrator Bridge Migration Design

**Date:** 2026-03-27
**Status:** Approved
**Approach:** Bridge Layer (Approach B)

## Problem

The project has two parallel systems that are not connected:

1. **AgentCore** (active in `main.py`): Simple pipeline — text input → Memory → LLM → ActionRouter → Response
2. **AgentOrchestrator** (dormant): Full 7-brain event-driven architecture with EventBus, SharedAgentState, and real implementations for all brains

The Orchestrator and all 7 brains are fully implemented but never instantiated. The goal is to activate the Orchestrator as the primary system while maintaining stable WebSocket communication.

## Decisions

- **Input:** Both WebSocket text chat AND microphone audio (sounddevice + VAD + STT)
- **TTS:** PiperProvider (with fallback to DummyTTS if piper not installed)
- **LLM:** OllamaProvider (existing implementation, already implements LLMProvider interface)
- **Migration Strategy:** Bridge Layer — create a translation layer between WebAvatar (WS) and EventBus

## Architecture

```
main.py
  ├── WebAvatar (WS client to server.js)
  ├── AgentOrchestrator (7 brains + EventBus)
  └── OrchestratorBridge (WebAvatar ↔ EventBus)
```

### OrchestratorBridge (NEW: `agent/bridge.py`)

The bridge is the key new component. It translates between WebSocket messages and EventBus events:

**Inbound (WS → EventBus):**
- `agent_input` message → publishes `TRANSCRIPTION_COMPLETE` event
- `chat` message → publishes `TRANSCRIPTION_COMPLETE` event

**Outbound (EventBus → WS):**
- `RESPONSE_READY` event → sends `{type:"agent_response", text:"..."}` via WebAvatar
- `ANIMATION_QUEUED` event → sends `{type:"avatar_control", ...}` via WebAvatar
- `GESTURE_QUEUED` event → sends `{type:"avatar_control", ...}` via WebAvatar
- `TTS_STARTED` event → calls `WebAvatar.speak_start()`
- `AUDIO_COMPLETE` event → calls `WebAvatar.speak_end()`

### Event Flow (Text Chat)

```
React → {chat} → server.js → {agent_input} → WebAvatar
  → Bridge → TRANSCRIPTION_COMPLETE
    → ReasoningBrain (OllamaProvider → LLM)
      → INTENT_DETECTED + RESPONSE_READY
    → SentimentBrain → SENTIMENT_UPDATED
      → (after INTENT_DETECTED) → EMOTION_DETECTED
        → AvatarBrain → ANIMATION_QUEUED
          → Bridge → avatar_control → server.js → React
    → PlanningBrain → TOOLS_QUEUED
      → ExecutionBrain → TOOL_RESULT
  → OutputBrain (PiperTTS) → TTS_STARTED → AUDIO_COMPLETE
    → Bridge → speak_start/speak_end → server.js → React
  → Bridge → agent_response → server.js → React
```

### Event Flow (Audio)

```
Microphone (sounddevice) → InputBrain.handle_audio_frame()
  → VAD → speech detected → VAD_START
  → silence → VAD_END → STT (faster-whisper)
  → TRANSCRIPTION_COMPLETE
  → Same downstream flow as text
```

## Components to Create/Modify

| Component | Action | Description |
|-----------|--------|-------------|
| `agent/bridge.py` | **NEW** | OrchestratorBridge — WS ↔ EventBus translation layer |
| `agent/main.py` | **REWRITE** | Use Orchestrator + Bridge instead of AgentCore |
| `web_avatar/server.js` | **FIX** | Add `avatar_control` handler to switch statement |
| `agent/brains/input_brain.py` | **MODIFY** | Wire `process()` to AudioCapture + sounddevice |
| `agent/orchestrator.py` | **MODIFY** | Accept OllamaProvider + WebAvatar via constructor |
| `agent/avatar/interface.py` | **MODIFY** | Expose message callback for Bridge to intercept |

**Unchanged:** ReasoningBrain, PlanningBrain, ExecutionBrain, SentimentBrain, AvatarBrain, OutputBrain, EventBus, SharedAgentState — they already communicate via events.

## server.js Fix (Critical Bug)

Add `avatar_control` handler — currently Python sends these messages but server.js drops them in `default:`:

```javascript
case 'avatar_control':
  wss.clients.forEach(client => {
    if (client.readyState === WebSocket.OPEN && client !== ws) {
      client.send(JSON.stringify(msg));
    }
  });
  break;
```

## Dependency Fallbacks

| Dependency | Used By | Fallback |
|------------|---------|----------|
| `piper-tts` | OutputBrain | DummyTTS (print-only) |
| `sounddevice` | InputBrain audio | Audio disabled, text-only |
| `faster-whisper` | InputBrain STT | Audio disabled, text-only |
| `aiohttp` | OllamaProvider | Already in requirements.txt |

## main.py Rewrite (High-Level)

```python
async def main():
    # Create WebAvatar (WS client)
    avatar = WebAvatar(host=WEBSOCKET_HOST, port=WEBSOCKET_PORT)
    
    # Create OllamaProvider (LLM)
    ollama_config = OllamaConfig(
        provider="ollama", model=LLM_MODEL,
        host=OLLAMA_HOST, temperature=0.7
    )
    llm_provider = OllamaProvider(ollama_config)
    
    # Create TTS provider (with fallback)
    tts_provider = create_tts_provider()
    
    # Create Orchestrator with dependencies
    orchestrator = AgentOrchestrator(
        tts_provider=tts_provider,
        # Need to inject llm_provider into ReasoningBrain
    )
    
    # Create Bridge
    bridge = OrchestratorBridge(
        avatar=avatar,
        event_bus=orchestrator.event_bus,
    )
    
    # Initialize and start
    await avatar.connect()
    await orchestrator.initialize()
    await orchestrator.start()
    await bridge.start()
    
    # Keep alive
    while True:
        await asyncio.sleep(1)
```

## Success Criteria

1. Text chat via WebSocket works end-to-end through the 7-brain pipeline
2. LLM (Ollama) generates real responses via ReasoningBrain
3. Avatar emotions/gestures reach the React frontend (avatar_control messages routed)
4. TTS synthesis works via PiperProvider (or graceful fallback)
5. Audio capture starts (even if STT quality needs tuning later)
6. All 7 brains report healthy in orchestrator health checks
7. System remains stable as a long-running daemon
