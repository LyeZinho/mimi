# Week 3 Plan: Output Brain (TTS) + Remaining Brains Architecture

> **For Claude:** Use `superpowers/subagent-driven-development` to implement this plan task-by-task with code review checkpoints.

**Goal:** Build Text-to-Speech (TTS) output brain using Piper for Portuguese audio synthesis, then design architecture for 5 specialized brains (Sentiment, Control, Memory, Action Executor, System Monitor).

**Tech Stack:** Python 3.10+, piper-tts (offline), pytest, asyncio

---

## Part A: Output Brain (TTS) - 5 Tasks

### Architecture Overview

```
User Input Flow:
Audio (Input Brain) → Text (STT)
                    ↓
Reasoning Brain → Intent + Response
                    ↓
Output Brain (TTS) → Audio Response
                    ↓
Avatar + Speaker Output
```

**Output Brain Design:**
- Async TTS synthesis using Piper (fast, offline)
- Support for streaming text → real-time audio chunks
- Voice configuration (gender, speed, language)
- Audio buffering and playback control
- Integration with avatar animation timing

---

## Task 1: TTS Provider Abstraction (Like LLM Adapter)

**Files:**
- Create: `agent/output/tts_provider.py`
- Create: `agent/output/piper_provider.py`
- Create: `agent/output/config.py`
- Test: `tests/unit/test_tts_provider.py`
- Test: `tests/unit/test_piper_provider.py`

**Step 1: Design (No Code Yet)**

TTS Provider Pattern (same as LLM):
```
TTSProvider (abstract)
├── async synthesize(text: str, stream: bool) → Union[bytes, AsyncIterator[bytes]]
├── set_voice(voice_id: str) → None
├── get_available_voices() → List[VoiceInfo]
└── get_usage_stats() → dict
```

Piper Configuration:
```python
@dataclass
class PiperConfig:
    model_path: str = "~/.cache/piper/pt_PT/pt-pt_blip-medium.onnx"
    speaker_id: int = 0
    speed: float = 1.0
    noise_scale: float = 0.667
```

**Step 2: Implementation**

Files to create:
1. `agent/output/config.py` - TTSConfig, PiperConfig dataclasses
2. `agent/output/tts_provider.py` - Abstract TTSProvider base class
3. `agent/output/piper_provider.py` - PiperProvider implementation (async wrapper)

**Step 3: Tests**

Create 8+ tests:
- Config initialization
- Abstract class cannot be instantiated
- Piper provider inheritance
- Synthesize text → audio bytes
- Stream mode async iteration
- Voice selection
- Usage stats tracking
- Exception handling (model not found, corrupted audio)

**Success Criteria:**
- ✅ All 8+ tests pass
- ✅ Piper model downloads on first use
- ✅ Async/streaming works
- ✅ Portuguese voice (pt_PT) selected
- ✅ Committed with message: `feat(output): add TTS provider abstraction and Piper implementation`

---

## Task 2: Output Brain (Text → Audio Stream)

**Files:**
- Create: `agent/brains/output_brain.py`
- Test: `tests/unit/test_output_brain.py`

**Design:**

```python
class OutputBrain(Brain):
    """Brain 3: Output Brain (TTS)
    
    Responsável por:
    - Receber respostas de texto
    - Sintetizar áudio em tempo real
    - Gerar eventos de áudio
    - Controlar timing de avatar
    """
    
    def __init__(self, tts_provider: TTSProvider):
        self.tts_provider = tts_provider
    
    async def _on_response_ready(self, event):
        """Quando ReasoningBrain gera resposta, converte para áudio."""
        text = event.payload.get("response", "")
        
        # Streaming synthesis
        audio_chunks = []
        async for chunk in self.tts_provider.synthesize(text, stream=True):
            audio_chunks.append(chunk)
            
            # Emit chunk for real-time playback
            await self.publish_event(EventType.AUDIO_CHUNK, {
                "chunk": chunk,
                "index": len(audio_chunks)
            })
        
        # Emit complete audio
        full_audio = b"".join(audio_chunks)
        await self.publish_event(EventType.AUDIO_COMPLETE, {
            "audio": full_audio,
            "duration_ms": calculate_duration(full_audio)
        })
```

**Tests:**
- Output brain initialization with TTS provider
- Responds to RESPONSE_READY event
- Generates AUDIO_CHUNK events
- Generates AUDIO_COMPLETE event
- Tracks synthesis latency
- Handles TTS errors gracefully

**Success Criteria:**
- ✅ All tests pass
- ✅ Event chain: RESPONSE_READY → AUDIO_CHUNK* → AUDIO_COMPLETE
- ✅ Real-time streaming (chunks emitted immediately)
- ✅ Latency tracking
- ✅ Committed: `feat(output): implement Output Brain with TTS integration`

---

## Task 3: Audio Buffering & Playback Control

**Files:**
- Create: `agent/output/audio_buffer.py`
- Test: `tests/unit/test_audio_buffer.py`

**Design:**

```python
class AudioBuffer:
    """Ring buffer for real-time audio playback."""
    
    def __init__(self, sample_rate: int = 22050, channels: int = 1, duration_sec: float = 5.0):
        # Pre-allocate buffer for 5 seconds of audio
        self.buffer = np.zeros(sample_rate * channels * duration_sec, dtype=np.float32)
        self.write_pos = 0
        self.read_pos = 0
        self.buffer_size = len(self.buffer)
    
    async def write(self, audio_chunk: bytes) -> None:
        """Add audio chunk to buffer."""
        # Convert bytes → numpy array
        # Write to buffer with wraparound
        # Emit BUFFER_LEVEL event
    
    async def read(self, num_samples: int) -> np.ndarray:
        """Read samples from buffer (for playback)."""
        # Read from read_pos
        # Update read_pos
        # Return audio frame
    
    def get_fill_level(self) -> float:
        """Get buffer fill percentage (0-1)."""
    
    def is_ready_for_playback(self, threshold: float = 0.1) -> bool:
        """Check if buffer has enough data to start playback."""
```

**Tests:**
- Buffer initialization
- Write chunks without overflow
- Read chunks sequentially
- Wraparound handling (circular buffer)
- Fill level calculation
- Playback readiness
- Underrun/overflow handling

**Success Criteria:**
- ✅ All tests pass
- ✅ Circular buffer works without copying
- ✅ Low latency (<50ms)
- ✅ Thread-safe (if needed for playback thread)
- ✅ Committed: `feat(output): add audio buffer for real-time playback`

---

## Task 4: Audio Playback Engine (sounddevice)

**Files:**
- Create: `agent/output/playback_engine.py`
- Test: `tests/unit/test_playback_engine.py`

**Design:**

```python
class PlaybackEngine:
    """Real-time audio playback using sounddevice."""
    
    def __init__(self, sample_rate: int = 22050, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.is_playing = False
        self.stream = None
    
    async def play_async(self, audio_data: np.ndarray) -> None:
        """Play audio chunk asynchronously."""
        # Create sounddevice stream
        # Play audio data
        # Wait for completion
    
    async def play_streaming(self, audio_buffer: AudioBuffer) -> None:
        """Play from audio buffer in real-time."""
        # Open stream
        # In playback callback, read from buffer
        # Handle buffer underrun
    
    def pause(self) -> None:
        """Pause playback."""
    
    def resume(self) -> None:
        """Resume playback."""
    
    def stop(self) -> None:
        """Stop playback and close stream."""
    
    async def wait_until_done(self) -> None:
        """Block until playback finishes."""
```

**Tests:**
- Initialize playback engine
- Play complete audio (non-streaming)
- Play from buffer (streaming)
- Pause/resume
- Stop
- Latency measurement

**Success Criteria:**
- ✅ All tests pass (mock sounddevice)
- ✅ Sub-50ms latency
- ✅ Streaming works without glitches
- ✅ Graceful cleanup
- ✅ Committed: `feat(output): add audio playback engine with streaming support`

---

## Task 5: Output Brain Integration with Orchestrator

**Files:**
- Modify: `agent/orchestrator.py`
- Test: `tests/integration/test_output_brain_e2e.py`

**Design:**

Orchestrator now manages 3 brains:
```
1. InputBrain (audio capture + STT)
2. ReasoningBrain (LLM inference)
3. OutputBrain (TTS + playback)
```

Event Flow:
```
AUDIO_CAPTURED → TRANSCRIPTION_COMPLETE → INTENT_DETECTED → RESPONSE_READY → AUDIO_CHUNK* → AUDIO_COMPLETE → PLAYBACK_STARTED → PLAYBACK_DONE
```

**Tests:**
- Orchestrator initializes 3 brains
- Event chain flows correctly
- TTS provider injected into OutputBrain
- Full end-to-end: microphone → LLM → speaker
- Measure total latency (audio in → audio out)

**Success Criteria:**
- ✅ All tests pass
- ✅ Full event chain works
- ✅ Latency < 500ms (audio in → TTS out)
- ✅ Committed: `feat(output): integrate Output Brain with orchestrator`

---

## Part B: Remaining Brains - Architecture Design (No Implementation Yet)

### Overview: 7-Brain System

```
Core (2):
├── Input Brain (audio capture + STT)
└── Reasoning Brain (LLM inference)

Output (1):
└── Output Brain (TTS + playback)

Specialized (4):
├── Sentiment Brain (emotion detection)
├── Control Brain (3D model control)
├── Memory Brain (context + persistence)
├── Action Executor Brain (integrations)
└── System Monitor Brain (health + logging)
```

---

## Brain Architecture Documents

### Brain 4: Sentiment Brain

**Purpose:** Analyze emotions from speech transcription and LLM response

**Inputs:**
- Speech transcription (text)
- LLM response (text)
- Audio features (optional: pitch, pace, energy from Input Brain)

**Outputs:**
- Emotion classification: happy, sad, angry, surprised, confused, neutral, thinking
- Confidence score (0-1)
- Emotion event for avatar animation

**Technology:**
- Hugging Face transformers (zero-shot classification)
- Model: `facebook/bart-large-mnli` for zero-shot + custom emotion labels
- Or: `distilbert-base-multilingual-uncased` fine-tuned on emotion

**Design Pattern:**
```python
class SentimentBrain(Brain):
    """Brain 4: Sentiment Analysis"""
    
    async def _on_response_ready(self, event):
        text = event.payload.get("response", "")
        
        # Classify emotion
        emotion = await self.classify_emotion(text)
        
        # Emit emotion event
        await self.publish_event(EventType.EMOTION_DETECTED, {
            "emotion": emotion["label"],
            "confidence": emotion["score"],
            "text_sample": text[:50]
        })
```

**Key Decisions:**
- Emotion detection = post-response (after LLM generates text)
- Could also detect on transcription (user's emotion)
- Lightweight models for low latency
- No cloud API (offline first)

**Integration Points:**
- Subscribes to: RESPONSE_READY, TRANSCRIPTION_COMPLETE
- Publishes to: EMOTION_DETECTED
- Control Brain listens to EMOTION_DETECTED for animation

---

### Brain 5: Control Brain (3D Model)

**Purpose:** Control avatar animations based on intent, emotion, and state

**Inputs:**
- Intent from Reasoning Brain (action type)
- Emotion from Sentiment Brain (happy, sad, etc.)
- User context (greeting, farewell, etc.)
- Speaking state (is TTS playing)

**Outputs:**
- VRM animation commands (blend shape, bone rotations)
- Gesture events (wave, nod, shake head)
- Expression updates (happy face, sad face)
- Speaking animation (jaw movement sync with audio)

**Technology:**
- VRM format (industry standard for avatars)
- Blend shapes (pre-defined expressions: Happy, Sad, Angry, Surprised, Confused, Neutral)
- Gestures (animations for common actions: wave, nod, point, celebrate, think)

**Design Pattern:**
```python
class ControlBrain(Brain):
    """Brain 5: 3D Model Control (Avatar Animation)"""
    
    def __init__(self, avatar_interface):
        self.avatar = avatar_interface  # WebSocket to 3D avatar
    
    async def _on_intent_detected(self, event):
        intent = event.payload.get("intent", "")
        
        # Map intent → gesture
        gesture = self.INTENT_TO_GESTURE.get(intent, "idle")
        await self.avatar.play_gesture(gesture)
    
    async def _on_emotion_detected(self, event):
        emotion = event.payload.get("emotion", "neutral")
        
        # Set face expression
        await self.avatar.set_expression(emotion)
    
    async def _on_audio_chunk(self, event):
        # Sync jaw movement with audio
        # Optional: TTS audio can drive lip-sync
        pass
```

**Animation Mappings:**
```python
INTENT_TO_GESTURE = {
    "greeting": "wave",
    "farewell": "goodbye",
    "query_hours": "think",
    "make_appointment": "celebrate",
    "make_complaint": "sad",
}

EMOTION_TO_EXPRESSION = {
    "happy": "happy",
    "sad": "sad",
    "angry": "angry",
    "surprised": "surprised",
    "confused": "confused",
    "neutral": "neutral",
    "thinking": "thinking",
}
```

**Integration Points:**
- Subscribes to: INTENT_DETECTED, EMOTION_DETECTED, AUDIO_CHUNK
- Publishes to: GESTURE_STARTED, GESTURE_DONE
- WebSocket communication with React avatar component

---

### Brain 6: Memory/Context Brain

**Purpose:** Manage conversation history, user context, and persistent memory

**Inputs:**
- User transcriptions
- LLM responses
- Intents detected
- Emotions expressed

**Outputs:**
- Context snapshot for LLM (previous turns, user preferences)
- Memory persistence (save to DB)
- Context updates

**Technology:**
- SQLite or Postgres for persistence
- Session-based context (in-memory)
- Conversation history (last N turns)

**Design Pattern:**
```python
class MemoryBrain(Brain):
    """Brain 6: Memory & Context Management"""
    
    def __init__(self, db_path: str):
        self.db = ConversationDB(db_path)
        self.session_context = {}
    
    async def initialize(self):
        # Load session context
        session_id = self.shared_state.get("session_id")
        self.session_context = await self.db.load_context(session_id)
    
    async def _on_transcription_complete(self, event):
        text = event.payload.get("transcript", "")
        
        # Add to conversation history
        self.session_context["history"].append({
            "role": "user",
            "text": text,
            "timestamp": time.time()
        })
        
        # Save to DB
        await self.db.save_turn(self.session_context["session_id"], "user", text)
    
    async def get_context_snapshot(self) -> dict:
        """Called by Reasoning Brain before inference."""
        return {
            "user_name": self.session_context.get("user_name"),
            "conversation_history": self.session_context["history"][-5:],  # Last 5 turns
            "user_preferences": self.session_context.get("preferences", {}),
        }
```

**Data Model:**
```sql
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY,
    session_id TEXT,
    user_id TEXT,
    role TEXT,  -- 'user' or 'assistant'
    text TEXT,
    timestamp DATETIME,
    intent TEXT,
    emotion TEXT,
);

CREATE TABLE user_context (
    user_id TEXT PRIMARY KEY,
    name TEXT,
    preferences JSON,
    created_at DATETIME,
    updated_at DATETIME,
);
```

**Integration Points:**
- Subscribes to: TRANSCRIPTION_COMPLETE, INTENT_DETECTED, EMOTION_DETECTED, RESPONSE_READY
- Publishes to: CONTEXT_UPDATED
- Provides context to: Reasoning Brain (injected dependency)

---

### Brain 7: Action Executor Brain

**Purpose:** Execute system commands and external integrations based on intents

**Inputs:**
- Intent from Reasoning Brain (action type + parameters)
- User context

**Outputs:**
- Execution result (success/error)
- External API calls (weather, calendar, smart home, etc.)
- System state changes

**Technology:**
- Plugin/registry pattern for actions
- Async execution
- Error handling and fallback

**Design Pattern:**
```python
class ActionExecutorBrain(Brain):
    """Brain 7: Action Executor"""
    
    def __init__(self):
        self.actions = {}  # action_type → handler function
        self._register_actions()
    
    def _register_actions(self):
        self.actions["query_weather"] = self.get_weather
        self.actions["set_alarm"] = self.set_alarm
        self.actions["send_message"] = self.send_message
        self.actions["control_lights"] = self.control_lights
    
    async def _on_intent_detected(self, event):
        intent = event.payload.get("intent", "")
        parameters = event.payload.get("parameters", {})
        
        if intent in self.actions:
            try:
                result = await self.actions[intent](parameters)
                await self.publish_event(EventType.ACTION_EXECUTED, {
                    "action": intent,
                    "result": result,
                })
            except Exception as e:
                logger.error(f"Action failed: {e}")
                await self.publish_event(EventType.ACTION_FAILED, {
                    "action": intent,
                    "error": str(e),
                })
    
    async def get_weather(self, params: dict) -> dict:
        """Fetch weather from API."""
        city = params.get("location", "Lisbon")
        # Call weather API
        return {"temperature": 20, "condition": "sunny"}
    
    async def set_alarm(self, params: dict) -> dict:
        """Set system alarm."""
        time_str = params.get("time", "10:00")
        # Execute system command
        return {"status": "alarm set"}
```

**Action Registry (Extensible):**
```python
ACTION_REGISTRY = {
    "query_weather": WeatherPlugin(),
    "query_hours": CalendarPlugin(),
    "send_message": MessagingPlugin(),
    "control_lights": SmartHomePlugin(),
}
```

**Integration Points:**
- Subscribes to: INTENT_DETECTED
- Publishes to: ACTION_EXECUTED, ACTION_FAILED
- No audio/avatar integration (system-level actions)

---

### Brain 8: System Monitor Brain

**Purpose:** Monitor system health, performance, logging, and diagnostics

**Inputs:**
- All brain events (for aggregation)
- System metrics (CPU, memory, latency)
- Error events

**Outputs:**
- Health status
- Performance metrics
- Log aggregation
- Alerts for anomalies

**Technology:**
- Prometheus metrics
- Structured logging (JSON)
- Health check HTTP endpoint

**Design Pattern:**
```python
class SystemMonitorBrain(Brain):
    """Brain 8: System Monitoring & Health Checks"""
    
    def __init__(self):
        self.metrics = MetricsCollector()
        self.health_status = {}
    
    async def initialize(self):
        # Start metrics server (Prometheus)
        self.metrics_server = PrometheusServer(port=9090)
        await self.metrics_server.start()
    
    async def _on_all_events(self, event):
        """Subscribe to all events for monitoring."""
        event_type = event.type
        latency = event.payload.get("latency_ms", 0)
        
        # Record metric
        self.metrics.record_event(event_type, latency)
    
    def get_system_health(self) -> dict:
        """Return current system health."""
        return {
            "status": "healthy" if self._all_checks_pass() else "degraded",
            "uptime_sec": self._get_uptime(),
            "avg_latency_ms": self.metrics.avg_latency,
            "error_rate": self.metrics.error_rate,
            "memory_usage_mb": self._get_memory(),
            "active_brains": len(self.orchestrator.brains),
        }
    
    async def check_brain_health(self, brain_id: str) -> dict:
        """Health check for specific brain."""
        # Run diagnostics
        return {"status": "healthy", "last_event": "2s ago"}
```

**Metrics to Track:**
- Latency per brain (ms)
- Error rates (%)
- Event throughput (events/sec)
- Buffer levels (audio, text)
- Memory usage (MB)
- Uptime (sec)

**HTTP Health Endpoint:**
```
GET /health → {"status": "healthy"}
GET /metrics → Prometheus metrics
GET /brains → Brain status
GET /performance → Latency, errors, throughput
```

**Integration Points:**
- Subscribes to: ALL events
- Publishes to: HEALTH_ALERT (if threshold exceeded)
- Provides: Health check HTTP endpoint

---

## Architecture Summary: 7-Brain System

| Brain | Input | Output | Purpose | Technology |
|-------|-------|--------|---------|-----------|
| 1. Input | Microphone | Text | Audio capture + STT | sounddevice, faster-whisper |
| 2. Reasoning | Text | Intent + Response | LLM inference | Ollama, LLM adapter |
| 3. Output | Response | Audio | TTS synthesis | Piper TTS |
| 4. Sentiment | Text | Emotion | Emotion detection | Transformers (BART, DistilBERT) |
| 5. Control | Intent, Emotion | Gestures | Avatar animation | VRM, WebSocket |
| 6. Memory | All events | Context | Conversation persistence | SQLite, JSON |
| 7. Action | Intent | Result | System execution | Plugins, REST APIs |
| 8. Monitor | All events | Metrics | Health + diagnostics | Prometheus, Logging |

---

## Event Bus Architecture

```
AUDIO_CAPTURED
    ↓
TRANSCRIPTION_COMPLETE (Input Brain)
    ↓
INTENT_DETECTED (Reasoning Brain) ← Also triggers Control Brain (gesture)
    ↓
RESPONSE_READY (Reasoning Brain)
    ↓
AUDIO_CHUNK* (Output Brain) → Control Brain (lip-sync)
    ↓
AUDIO_COMPLETE (Output Brain)
    ↓
PLAYBACK_DONE

Parallel:
EMOTION_DETECTED (Sentiment Brain) → Control Brain (expression)
ACTION_EXECUTED (Action Brain) → System integration
CONTEXT_UPDATED (Memory Brain) → For next turn
HEALTH_ALERT (Monitor Brain) → Logging
```

---

## Completion Criteria (Part A + B)

### Part A: Output Brain (Tasks 1-5)
- ✅ TTS Provider abstraction (like LLM adapter pattern)
- ✅ Piper TTS integration (Portuguese, offline)
- ✅ Output Brain implementation
- ✅ Audio buffering for real-time playback
- ✅ Audio playback engine
- ✅ Orchestrator with 3 brains (Input, Reasoning, Output)
- ✅ All tests passing
- ✅ Full latency < 500ms (audio in → audio out)
- ✅ Ready for integration with avatar

### Part B: Remaining Brains (Design)
- ✅ Architecture documented for 5 specialized brains
- ✅ Event bus topology defined
- ✅ Brain responsibilities clarified
- ✅ Technology choices documented
- ✅ Integration points specified
- ✅ Design patterns established (for future implementation)

---

## Implementation Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| **Week 3A** | 6 hours | Tasks 1-5 (Output Brain complete) |
| **Week 3B** | 2 hours | Architecture documentation (this file) |
| **Week 4** | 8 hours | Sentiment + Control Brain (Brains 4-5) |
| **Week 5** | 6 hours | Memory + Action + Monitor Brains (6-8) |
| **Week 6** | 4 hours | E2E integration + testing all 8 brains |

---

## Next Steps (Immediate)

1. ✅ Understand Week 3A scope (5 TTS tasks)
2. ✅ Review architecture for Brains 4-8
3. 🔄 **START Week 3A Task 1:** TTS Provider Abstraction
4. Then proceed through Tasks 2-5 sequentially

**Ready to begin Week 3A Task 1?** (y/n)
