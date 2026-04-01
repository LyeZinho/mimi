"""
Architecture Documentation: 7-Brain Multi-Agent System with Audio Streaming

## Overview

Mimi is a multi-brain agent system designed for real-time audio I/O with minimal latency.
The architecture separates concerns into 7 autonomous brains that communicate via event bus
and shared state.

## The 7 Brains

### 1. Input Brain (VAD + STT)
- Captures audio from microphone in real-time
- Ring buffer: maintains 3-second history for VAD context
- Voice Activity Detection: detects speech start/end
- Speech-to-Text: converts audio chunks to text
- Events: AUDIO_CHUNK, VAD_START, VAD_END, TRANSCRIPTION_COMPLETE

**Efficiency**: Uses local models (faster-whisper, webrtcvad) — no cloud, low latency

---

### 2. Reasoning Brain (LLM Inference)
- Consumes transcribed text from Input Brain
- Builds context from conversation history
- Invokes LLM (Ollama, Mistral) for intent inference
- Streaming response: doesn't wait for full completion
- Events: INTENT_DETECTED, INTENT_STREAMING

**Optimization**: Streaming begins mid-inference, allowing parallel processing

---

### 3. Planning Brain (Action Schema)
- Validates inferred intent
- Selects actions to execute
- **No LLM**: uses efficient rule-based logic
- Handles edge cases, constraints, ambiguity resolution
- Events: TOOLS_QUEUED, PLAN_CREATED

**Token Economy**: 100% rule-based, zero LLM overhead

---

### 4. Execution Brain (Tool Dispatcher)
- Executes actions in parallel (thread pool)
- Aggregates results from multiple tools
- Handles synchronous operations safely
- **No LLM**: pure dispatcher
- Events: TOOL_STARTED, TOOL_RESULT, TOOL_ERROR

**Performance**: Parallelizes independent operations for speed

---

### 5. Sentiment Brain (Emotion Detection)
- Analyzes emotional tone of user input
- Analyzes emotional tone of agent response
- **No LLM**: uses efficient lexical analysis
- Updates avatar emotion state
- Events: SENTIMENT_UPDATED, EMOTION_DETECTED

**Efficiency**: Lexical rules with minimal overhead — perfect for real-time

---

### 6. Avatar Brain (3D Model Control)
- Controls 3D model animations and expressions
- Maps emotions to facial expressions
- Synchronizes with TTS (lip-sync)
- Manages gesture queuing
- **No LLM**: pure animation controller
- Events: ANIMATION_QUEUED, GESTURE_QUEUED, AVATAR_STATE_CHANGED

**Design**: Decoupled from LLM — avatar responds to events, not to prompts

---

### 7. Output Brain (TTS + Streaming)
- Converts response text to speech
- Streams audio in chunks (100ms typical)
- Doesn't wait for full TTS completion (parallel with avatar)
- Synchronizes with avatar gestures
- Events: TTS_STARTED, TTS_CHUNK, TTS_COMPLETE

**Optimization**: Streaming TTS reduces perceived latency

---

## Communication Architecture

```
┌─────────────────────────────────────────┐
│     EVENT BUS (pub/sub, async)          │
│  - Non-blocking publish                 │
│  - Parallel handler dispatch            │
│  - Event history + metrics              │
└──────────────────┬──────────────────────┘
         ▲         │
         │         ▼
    publish      subscribe
         │         │
    ┌────┴─────────┴────┐
    │  SHARED STATE     │
    │  (asyncio.Lock)   │
    │                   │
    │ - User context    │
    │ - Conversation    │
    │ - Task status     │
    │ - Brain health    │
    └─────────────────┬─┘
          ▲           │
          └───────────┘
        (update via delta)
```

### Event Bus

- **Async pub/sub** with decorator pattern
- **Non-blocking**: publish() returns immediately
- **Concurrent** handler execution
- **Event history** for debugging and replay
- **Type-safe**: EventType enum for all event types

```python
bus = EventBus()

@bus.subscribe(EventType.TEXT_CHUNK)
async def on_text(event):
    print(event.payload)

await bus.publish(AgentEvent(
    type=EventType.TEXT_CHUNK,
    source_brain="input_brain",
    payload={"text": "hello"}
))
```

### Shared State

- **Lock-free reads**: snapshots don't block
- **Serialized writes**: asyncio.Lock for consistency
- **Versioning**: context version increments on update
- **Health tracking**: brain heartbeats, event counts, latencies
- **Task management**: persistent task status tracking

```python
state = SharedAgentState()
await state.initialize("user_1", "session_1")

snapshot = await state.get_context_snapshot()  # Lock-free read

await state.update_context("brain_id", {"state": "listening"})  # Locked write
```

---

## Buffer Architecture (Hybrid)

### Ring Buffer (Audio Input)
- **Fixed capacity**: 3 seconds of history
- **Circular**: auto-recycles oldest data
- **Snapshots**: non-destructive reads for VAD
- Used by: Input Brain (VAD monitoring)

```python
buffer = RingBuffer(capacity_bytes=96000, sample_rate=16000)

await buffer.write(microphone_data)
snapshot = await buffer.peek(48000)  # Last 1.5 seconds
```

### Chunk Queue (Processing)
- **FIFO**: first-in-first-out
- **TTL**: automatic expiration (5s default)
- **Max size**: prevents memory bloat
- Used by: STT consumer threads

```python
queue = ChunkQueue(max_queue_size=100, ttl_ms=5000)

await queue.put(AudioChunk(data=b'...'))
chunk = await queue.get()
```

### BufferManager
- Coordinates RingBuffer + ChunkQueue
- Simulates microphone → VAD → STT flow

```python
manager = BufferManager(ring_buffer_duration_sec=3.0)

await manager.write_audio(mic_frame)
ring_snapshot = await manager.get_ring_snapshot()

await manager.enqueue_chunk(chunk)
chunk = await manager.dequeue_chunk()
```

---

## Data Flow: Example Conversation

```
TIME  │ FLOW                                           │ LATENCY
──────┼────────────────────────────────────────────────┼─────────
  0ms │ Microphone captures audio                      │
      │ Input Brain: writes to RingBuffer              │
      │              publishes AUDIO_CHUNK event       │
      │                                                │
 50ms │ Input Brain: VAD detects speech start          │
      │              publishes VAD_START               │
      │              publishes AUDIO_CHUNK → Input     │
      │                                                │
100ms │ Input Brain: STT in progress (streaming)       │
      │ Reasoning Brain: receives transcript chunks    │
      │ Planning Brain: speculates on actions          │
      │ Avatar Brain: prepares animations             │
      │                                                │
150ms │ Input Brain: STT complete                      │
      │              publishes TRANSCRIPTION_COMPLETE  │
      │                                                │
160ms │ Reasoning Brain: calls LLM                     │
      │ Sentiment Brain: analyzes user emotion        │
      │ Avatar Brain: queues facial expression        │
      │                                                │
200ms │ Reasoning Brain: LLM returns intent            │
      │                 publishes INTENT_DETECTED      │
      │                                                │
210ms │ Planning Brain: validates + selects actions    │
      │ Sentiment Brain: analyzes response emotion    │
      │ Avatar Brain: queues new gesture              │
      │                                                │
215ms │ Planning Brain: publishes TOOLS_QUEUED        │
      │                                                │
220ms │ Execution Brain: executes actions (parallel)   │
      │ Output Brain: starts TTS (streaming)           │
      │ Avatar Brain: begins speaking animation       │
      │                                                │
250ms │ Output Brain: first TTS chunk ready            │
      │               publishes TTS_CHUNK              │
      │               avatar starts lip-sync          │
      │                                                │
300ms │ Full response synthesized + avatar speaking    │ ~300ms total
      │ Input Brain: VAD detects speech end           │
```

---

## Key Design Principles

### 1. No Single Point of Failure
- Each brain is independent
- Event bus is fire-and-forget (no replies)
- Brains can pause/resume independently
- Health monitoring detects unhealthy brains

### 2. Token Economy
- **Planning Brain**: rule-based (0 tokens)
- **Sentiment Brain**: lexical analysis (0 tokens)
- **Avatar Brain**: deterministic mapping (0 tokens)
- **Only Reasoning Brain**: uses LLM (saving on other brains)

### 3. Real-Time Performance
- Ring buffer: efficient sliding window
- Chunk queue: bounded memory
- Async/await: non-blocking everywhere
- Streaming TTS: parallel with avatar

### 4. Observable
- Event bus: full history
- Shared state: health metrics per brain
- Metrics API: latency, throughput, errors
- Debug tools: event replay, state snapshots

---

## API Usage

```python
from agent.orchestrator import AgentOrchestrator

async def main():
    orchestrator = AgentOrchestrator(
        user_id="user_1",
        session_id="session_1"
    )
    
    await orchestrator.initialize()
    await orchestrator.start()
    
    await orchestrator.process_text_input("Olá Mimi!")
    
    await asyncio.sleep(2.0)
    
    metrics = await orchestrator.get_metrics()
    print(metrics)
    
    history = await orchestrator.get_event_history("TRANSCRIPTION_COMPLETE")
    print(history)
    
    await orchestrator.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Configuration

```python
# agent/config.py

AUDIO_CONFIG = {
    "sample_rate": 16000,
    "channels": 1,
    "bits_per_sample": 16,
}

BUFFER_CONFIG = {
    "ring_buffer_duration_sec": 3.0,
    "chunk_queue_max_size": 100,
    "chunk_ttl_ms": 5000,
}

EVENT_BUS_CONFIG = {
    "max_queue_size": 1000,
}

BRAIN_CONFIG = {
    "heartbeat_interval": 1.0,
}
```

---

## Testing

### Unit Tests
```python
# tests/test_buffers.py
# tests/test_event_bus.py
# tests/test_brains.py
```

### Integration Tests
```python
# tests/test_orchestrator.py
# tests/test_audio_pipeline.py
```

### Metrics & Observability
```python
metrics = await orchestrator.get_metrics()
print(f"Input Brain latency: {metrics['brains']['input_brain']['avg_latency_ms']:.1f}ms")
print(f"Events published: {metrics['event_bus']['events_published']}")
```

---

## Future Enhancements

1. **Distributed Brains**: Run each brain in separate process/machine
2. **Tool Registry**: Extensible tool system for Planning Brain
3. **Memory System**: Long-term conversational memory
4. **Multimodal Input**: Vision integration (camera, webcam)
5. **Custom LLM Integration**: Support for local fine-tuned models
6. **A/B Testing**: Route intents to different LLMs experimentally
7. **Failure Recovery**: Auto-restart unhealthy brains
8. **Voice Clone**: Custom voice synthesis

---
