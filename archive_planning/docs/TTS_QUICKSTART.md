# TTS Voice Synthesis Quick Start

## Manual Testing

### 1. Test PiperProvider directly

```python
import asyncio
from agent.output.piper_provider import PiperProvider
from agent.output.config import PiperConfig

async def test_piper():
    config = PiperConfig(provider="piper", model="pt_PT")
    provider = PiperProvider(config)
    
    text = "Olá, como você está hoje?"
    async for chunk in provider.synthesize(text, stream=True):
        print(f"Received chunk: {len(chunk)} bytes")

asyncio.run(test_piper())
```

Expected output:
```
Received chunk: 1024 bytes
Received chunk: 1024 bytes
Received chunk: 512 bytes
```

### 2. Run Unit Tests

```bash
cd /home/pedro/repo/mimi
source .venv/bin/activate

pytest tests/output/test_piper_provider.py -v
pytest tests/brains/test_output_brain_streaming_fix.py -v
```

Expected: All 6 tests passing ✅

### 3. Test End-to-End in Agent

1. Start agent: `python agent/main.py`
2. Open web interface: `http://localhost:5173`
3. Send message to Mimi
4. Observe:
   - Avatar mouth starts moving (speak_start triggered)
   - Audio plays through browser speakers
   - Avatar mouth stops (speak_end triggered)

## Debugging TTS Issues

### Check if Piper is installed

```bash
python -c "import piper; print(piper.__file__)"
```

If not installed:
```bash
pip install piper-tts
```

### Enable TTS debug logging

Edit `agent/main.py` to add:
```python
logging.getLogger('agent.brains.output_brain').setLevel(logging.DEBUG)
logging.getLogger('agent.output.piper_provider').setLevel(logging.DEBUG)
```

Then check logs for:
- `TTS initialized and subscribed to RESPONSE_READY`
- `Synthesized N chunks in Xms`
- Any synthesis errors

### Verify EventBus connections

```python
from agent.core.messaging import EventBus, EventType

event_bus = EventBus()
event_bus.subscribe(EventType.TTS_STARTED)(
    lambda e: print(f"TTS Started: {e}")
)
event_bus.subscribe(EventType.AUDIO_COMPLETE)(
    lambda e: print(f"Audio Complete: {e}")
)
```

### Check avatar speaker methods

```python
mock_avatar.speak_start.assert_called()
mock_avatar.speak_end.assert_called()
```

## Common Issues & Solutions

### "object AsyncGenerator can't be used in 'await' expression"

**Problem**: Code incorrectly awaits AsyncIterator

**Solution**: See TTS_IMPLEMENTATION.md - The Fix section

**Quick Fix**:
```python
# REMOVE this pattern:
async for chunk in await provider.synthesize(text, stream=True):

# USE this pattern:
async for chunk in provider.synthesize(text, stream=True):
```

### No audio in browser

**Checklist**:
- [ ] Piper installed: `pip install piper-tts`
- [ ] Agent running: `python agent/main.py`
- [ ] Bridge subscribed to TTS events: Check bridge.py
- [ ] WebAvatar connected: Check browser WebSocket status
- [ ] No errors in agent logs: Search for "error" or "Error"

### Slow synthesis

Typical first chunk latency: 200-500ms

**If consistently slower**:
1. Check CPU usage - TTS is CPU-bound
2. Try GPU if available: `PiperConfig(use_cuda=True)`
3. Check agent logs for delays between TTS_STARTED and first AUDIO_CHUNK

### Events not publishing

**Check**:
1. OutputBrain initialized? Check startup health check
2. RESPONSE_READY triggered? Test with manual LLM response
3. EventBus connected? Verify bridge subscriptions

## Configuration Reference

### Environment Variables

None specific to TTS - uses existing Ollama/agent config

### PiperConfig Options

```python
from agent.output.config import PiperConfig

config = PiperConfig(
    provider="piper",           # Required: "piper"
    model="pt_PT",              # Language: pt_PT, en_US, es_ES, etc.
    speaker_id=0,               # Voice ID (0 = default)
    speed=1.0,                  # Speech speed (0.5-2.0)
    noise_scale=0.667,          # Voice variance (0.0-1.0)
    use_cuda=False,             # GPU acceleration if available
)
```

### OutputBrain Dependency Injection

In `agent/main.py`:
```python
def create_tts_provider():
    try:
        config = PiperConfig(provider="piper", model="pt_PT")
        provider = PiperProvider(config)
        return provider
    except Exception as e:
        logger.warning(f"TTS not available ({e})")
        return None

# In orchestrator initialization:
tts_provider = create_tts_provider()
output_brain = OutputBrain(..., tts_provider=tts_provider)
```

## Performance Tuning

### Chunk Size

In `PiperProvider._synthesize_streaming()`:
```python
chunk_size = 1024  # Bytes per chunk
```

Trade-offs:
- **Smaller chunks** (512): More events, lower latency per event, more overhead
- **Larger chunks** (4096): Fewer events, higher latency per event, less overhead
- **Current (1024)**: Good balance

### Event Publishing Latency

Each `await self.publish_event(...)` in OutputBrain triggers EventBus subscribers.

If slow, profile EventBus performance with logging:
```python
import time
start = time.time()
await self.publish_event(EventType.AUDIO_CHUNK, {...})
elapsed = (time.time() - start) * 1000
logger.debug(f"Event publish took {elapsed:.1f}ms")
```

## Architecture Decisions

### Why Streaming Instead of Complete Audio?

- **Streaming**: Low latency (chunks available as generated), enables real-time avatar sync
- **Complete**: Simple but 500+ ms delay before any audio available

### Why AsyncIterator Over Coroutine?

- `stream=True` returns `AsyncIterator[bytes]` directly
- Allows `async for` without intermediate awaits
- Matches Piper's native streaming API

### Why EventBus for Audio?

- **Decoupling**: OutputBrain doesn't know about Bridge or WebAvatar
- **Extensibility**: New subscribers can attach to AUDIO_CHUNK easily
- **Testability**: Easy to mock event flow
- **Debugging**: Central point to monitor all audio events

## Integration Checklist

- [x] OutputBrain fixed (AsyncIterator handling)
- [x] PiperProvider tests (streaming & non-streaming)
- [x] OutputBrain fix tests (exact pattern verified)
- [x] Documentation (this guide + implementation details)
- [ ] Voice selection UI (future enhancement)
- [ ] Audio playback (future enhancement)
- [ ] Emotion modulation (future enhancement)

## Version History

- **2025-03-28**: Initial implementation
  - Fixed critical bug in OutputBrain streaming
  - Added comprehensive unit tests
  - Documented architecture and troubleshooting
