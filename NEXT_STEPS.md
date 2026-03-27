# 🚀 Next Steps: From Architecture to Integration

## Phase 1: Input Brain Integration (Week 1-2)

### 1.1 Audio Capture with sounddevice
```python
# agent/input/audio_capture.py (NEW)
import sounddevice as sd

async def capture_audio_stream(sample_rate=16000, block_size=512):
    """Capture audio from microphone and feed to InputBrain"""
    # Will connect to InputBrain.handle_audio_frame()
```

**Files to create**:
- `agent/input/audio_capture.py` — microphone interface
- `agent/input/vad_processor.py` — webrtcvad wrapper

**Status**: TODO

---

### 1.2 Speech-to-Text with faster-whisper
```python
# agent/input/speech_to_text.py (NEW)
import faster_whisper

class STTProcessor:
    async def transcribe_chunk(self, audio_data: bytes) -> str:
        """STT inference with streaming support"""
        # Will integrate with InputBrain
```

**Files to create**:
- `agent/input/speech_to_text.py` — faster-whisper wrapper
- Tests for STT latency

**Status**: TODO

---

### 1.3 Connect Input Brain
```python
# agent/brains/input_brain.py (MODIFY)
# Replace placeholder _run_vad() and _run_stt() with real implementations
```

**Integration checklist**:
- [ ] Connect sounddevice to RingBuffer
- [ ] Connect webrtcvad for VAD
- [ ] Connect faster-whisper for STT
- [ ] Measure end-to-end latency (target: 100ms)
- [ ] Test with 10+ different utterances

**Status**: TODO

---

## Phase 2: Reasoning Brain Integration (Week 2-3)

### 2.1 LLM Client for Ollama
```python
# agent/llm/ollama_client.py (NEW)
import aiohttp

class OllamaClient:
    async def generate_streaming(self, prompt: str, model: str = "phi3:mini"):
        """Stream LLM inference with event publishing"""
        # Will publish INTENT_DETECTED with streaming chunks
```

**Files to create**:
- `agent/llm/ollama_client.py` — Ollama async wrapper
- `agent/llm/prompt_templates.py` — intent extraction prompts
- Tests for prompt quality

**Status**: TODO

---

### 2.2 Connect Reasoning Brain
```python
# agent/brains/reasoning_brain.py (MODIFY)
# Replace placeholder _infer_intent() with real LLM calls
```

**Integration checklist**:
- [ ] Connect to Ollama API
- [ ] Implement streaming inference
- [ ] Parse intent JSON from LLM
- [ ] Validate intent structure
- [ ] Measure latency (target: 100-150ms)
- [ ] Test with 20+ different queries

**Status**: TODO

---

## Phase 3: Output Brain Integration (Week 3)

### 3.1 Text-to-Speech with Piper
```python
# agent/output/piper_tts.py (NEW)
import subprocess

class PiperTTS:
    async def synthesize_streaming(self, text: str, voice: str = "pt_PT-mimi"):
        """TTS with chunk streaming"""
        # Will publish TTS_CHUNK events without waiting for completion
```

**Files to create**:
- `agent/output/piper_tts.py` — Piper wrapper (subprocess-based)
- `agent/output/audio_player.py` — audio playback (optional)
- Tests for audio quality

**Status**: TODO

---

### 3.2 Connect Output Brain
```python
# agent/brains/output_brain.py (MODIFY)
# Replace placeholder _synthesize_and_stream() with real TTS
```

**Integration checklist**:
- [ ] Connect to Piper or Coqui
- [ ] Stream audio chunks (100ms each)
- [ ] Don't wait for full TTS completion
- [ ] Measure latency (target: 50-100ms first chunk)
- [ ] Test with various response lengths

**Status**: TODO

---

## Phase 4: Avatar Brain Integration (Week 3-4)

### 4.1 WebSocket Avatar Controller
```python
# agent/avatar/websocket_controller.py (NEW)
import websockets

class AvatarController:
    async def send_animation(self, animation_type: str, intensity: float):
        """Send animation command to web_avatar"""
        # Will communicate with web_avatar/server.js
```

**Files to create**:
- `agent/avatar/websocket_controller.py` — WebSocket client
- Connect to existing web_avatar/server.js
- Tests for animation timing

**Status**: TODO

---

### 4.2 Connect Avatar Brain
```python
# agent/brains/avatar_brain.py (MODIFY)
# Replace placeholder with real WebSocket calls
```

**Integration checklist**:
- [ ] Connect to web_avatar WebSocket
- [ ] Test emotion-to-animation mapping
- [ ] Test lip-sync with TTS chunks
- [ ] Verify animation timing
- [ ] Test with 30+ avatar states

**Status**: TODO

---

## Phase 5: End-to-End Testing (Week 4)

### 5.1 Create comprehensive test suite
```python
# tests/test_orchestrator_e2e.py (NEW)
# Full conversation: "Qual é a temperatura em Lisboa?"
# Measure: latency per brain, total latency, memory usage
```

**Test cases**:
- [ ] Simple greeting: "Olá"
- [ ] Question: "Qual é a temperatura em Lisboa?"
- [ ] Complex request: "Mostra-me a previsão do tempo para os próximos 3 dias"
- [ ] Error handling: Invalid input, timeout, LLM failure
- [ ] Stress test: 100 requests in succession
- [ ] Memory profiling: Long session (1000 turns)

**Status**: TODO

---

### 5.2 Performance benchmarking
```
Target: < 300ms total latency

Breakdown (ideal):
- Input Brain: 80-100ms (STT)
- Reasoning Brain: 100-150ms (LLM)
- Planning Brain: < 1ms (rules)
- Execution Brain: < 1ms (dispatcher)
- Sentiment Brain: < 1ms (lexical)
- Avatar Brain: < 1ms (mapping)
- Output Brain: 50-100ms (TTS first chunk)

Total: ~250ms
```

**Benchmark suite**:
- [ ] Latency per brain
- [ ] Throughput (events/sec)
- [ ] Memory usage (baseline + growth)
- [ ] CPU usage
- [ ] Event queue depth
- [ ] Buffer efficiency

**Status**: TODO

---

## Phase 6: Refactor main.py (Week 4)

### 6.1 Update main.py to use AgentOrchestrator
```python
# agent/main.py (MODIFY)
from agent.orchestrator import AgentOrchestrator

async def main():
    orchestrator = AgentOrchestrator(user_id="mimi_user")
    await orchestrator.initialize()
    await orchestrator.start()
    
    # Handle WebSocket connections from web_avatar
    # Forward text input to orchestrator
    # Stream metrics back to frontend
```

**Files to update**:
- `agent/main.py` — use new orchestrator
- `web_avatar/server.js` — adapt to new event types
- Tests for backward compatibility

**Status**: TODO

---

### 6.2 WebSocket integration
```python
# Test that web_avatar still works with new architecture
# Events should flow: orchestrator → metrics endpoint → frontend
```

**Integration checklist**:
- [ ] WebSocket connection works
- [ ] Metrics stream to frontend
- [ ] Avatar responds to emotions
- [ ] Text input is processed
- [ ] Test with OBS Studio integration

**Status**: TODO

---

## Concrete Action Items

### Week 1
- [ ] Setup: Install sounddevice, faster-whisper, webrtcvad
- [ ] Implement `audio_capture.py`
- [ ] Implement STT processor
- [ ] Test Input Brain end-to-end
- [ ] Measure STT latency
- **Target**: "Olá" → transcribed in < 100ms

### Week 2
- [ ] Setup: Install/run Ollama with phi3:mini model
- [ ] Implement Ollama client
- [ ] Create intent extraction prompts
- [ ] Test Reasoning Brain streaming
- [ ] Measure inference latency
- **Target**: Intent detected in < 150ms

### Week 3
- [ ] Setup: Install/download Piper TTS
- [ ] Implement TTS processor
- [ ] Implement Avatar WebSocket controller
- [ ] Test Output Brain streaming
- [ ] Test Avatar animations
- **Target**: Audio synthesized in < 100ms, avatar animates

### Week 4
- [ ] End-to-end conversation flow
- [ ] Performance benchmarking
- [ ] Refactor main.py
- [ ] Full integration testing
- [ ] Performance tuning
- **Target**: Complete conversation in < 300ms

---

## Performance Targets

| Component | Latency Target | Status |
|-----------|----------------|--------|
| Input Brain (STT) | 80-100ms | TODO |
| Reasoning Brain (LLM) | 100-150ms | TODO |
| Planning Brain | < 1ms | ✅ Ready |
| Execution Brain | < 1ms | ✅ Ready |
| Sentiment Brain | < 1ms | ✅ Ready |
| Avatar Brain | < 1ms | ✅ Ready |
| Output Brain (TTS) | 50-100ms | TODO |
| **Total** | **< 300ms** | TODO |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| STT latency too high | Slow response | Profile with real audio, optimize model quantization |
| LLM inference slow | Bottleneck | Use streaming, implement fallback to simpler model |
| TTS latency high | User waits long | Stream chunks early, use faster TTS engine |
| Memory leaks in buffers | Crash on long sessions | Profile memory, add buffer cleanup |
| Event bus queue overflow | Dropped events | Monitor queue size, increase buffer or optimize throughput |
| Avatar WebSocket connection fails | Silent failure | Implement reconnect with exponential backoff |

---

## Testing Strategy

### Unit Tests
```
tests/
├── test_event_bus.py           — EventBus pub/sub
├── test_shared_state.py        — State management
├── test_buffers.py             — Ring buffer, chunk queue
├── test_brains.py              — Each brain independently
└── test_orchestrator.py        — Orchestrator lifecycle
```

### Integration Tests
```
tests/
├── test_orchestrator_e2e.py    — Full conversation flow
├── test_latency_profile.py     — Per-brain latencies
└── test_stress.py              — High throughput scenarios
```

### Performance Tests
```
scripts/
├── benchmark_latency.py        — Latency per component
├── benchmark_throughput.py     — Events/sec
└── profile_memory.py           — Memory usage over time
```

---

## Success Criteria

- ✅ All brains integrated with real implementations
- ✅ End-to-end latency < 300ms (with 70% confidence)
- ✅ Zero crashes on 1000+ conversation turns
- ✅ Memory stable (no leaks)
- ✅ All unit + integration tests passing
- ✅ Performance benchmarks documented
- ✅ Deployment guide written

---

## Questions for Implementation

1. **STT Model Size**: Use tiny, base, or small faster-whisper model? (speed vs accuracy)
2. **LLM Model**: Phi3:mini or Mistral 7B? (speed vs quality)
3. **TTS Engine**: Piper or Coqui? (speed vs quality)
4. **Audio Output**: Play via speakers or just return bytes? (depends on deployment)
5. **Persistence**: Save conversation history to DB? (depends on memory constraints)
6. **Monitoring**: Export metrics to Prometheus/Grafana? (for production)

---

## Next Meeting Agenda

1. Review this implementation complete ✅
2. Prioritize Phase 1 tasks (Input Brain)
3. Discuss STT model selection
4. Setup development environment
5. Assign first tasks

---

**Status**: Infrastructure complete, ready for implementation phase
**Timeline**: 4 weeks to production-ready system
**Team**: Ready to integrate!
