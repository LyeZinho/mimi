# Audio Response Integration Design

**Date**: March 28, 2026  
**Status**: Design Phase (pending approval)  
**Approach**: Hybrid Pull + Push Buffer Architecture with Phoneme Sync

## 1. Architecture Overview

### Data Flow
```
User Input (text)
  ↓
LLM Generation
  ↓
RESPONSE_READY event
  ↓
OutputBrain: synthesize(text, stream=True)
  ↓
PiperProvider: yields AudioChunk(audio_int16_bytes, phonemes, sample_rate)
  ↓
OutputBrain: publishes AUDIO_CHUNK + PHONEME_DATA events
  ↓
ResponseBuffer: accumulates chunks with metadata
  ↓
Bridge (outbound): 
  ├→ Push: sends chunks via WebSocket periodically
  └→ Poll: responds to buffer_status requests
  ↓
WebSocket → Frontend
  ↓
AudioPlayer: 
  ├→ pulls chunks from buffer
  └→ feeds to Web Audio API for playback
  ↓
AvatarSync: 
  ├→ receives phoneme timestamps
  └→ triggers lip-sync + gestures
  ↓
Avatar speaks in sync with audio
```

## 2. Component Design

### 2.1 ResponseBuffer (Python Backend)
**File**: `agent/output/response_buffer.py`

Ring buffer for current response's audio chunks:
- Stores chunks as they arrive from TTS
- Keeps track of:
  - Audio bytes (16-bit PCM)
  - Phoneme data (phonemes + sample positions)
  - Timestamps for each chunk
  - Fill level (for underrun detection)
- Methods:
  - `add_chunk(audio_bytes, phonemes)` - accumulate
  - `get_chunks(start_pos)` - retrieve available chunks
  - `mark_playback_pos(pos)` - track frontend playback
  - `is_complete()` - check if TTS finished
  - `clear()` - reset for next response

**Size**: ~5-10 seconds of audio (150-300 KB at 22050 Hz, 16-bit)

### 2.2 OutputBrain Changes
**File**: `agent/brains/output_brain.py`

When synthesizing with stream=True:
1. Create new ResponseBuffer for this response
2. For each chunk from PiperProvider:
   - Add to ResponseBuffer
   - Extract phoneme data from AudioChunk
   - Publish AUDIO_CHUNK event (with phonemes)
   - Publish PHONEME_DATA event (for avatar sync)
3. On completion:
   - Publish AUDIO_COMPLETE event
   - Mark buffer as complete

**New Events**:
- `PHONEME_DATA`: {phonemes: List[str], sample_positions: List[int], timestamp: float}

### 2.3 Bridge Outbound Handler
**File**: `agent/bridge.py`

Add two handlers:

**Handler 1: Push AUDIO_CHUNK events**
```python
async def _on_audio_chunk(self, event: AgentEvent):
    """Send TTS audio chunks to frontend."""
    chunk_data = event.payload.get("data")  # bytes
    phonemes = event.payload.get("phonemes", [])
    
    await self.avatar.send_command({
        "type": "audio_chunk",
        "audio_data": chunk_data.hex(),  # encode bytes as hex string
        "phonemes": phonemes,
        "timestamp": event.payload.get("timestamp"),
    })
```

**Handler 2: Respond to buffer_status poll**
```python
async def handle_buffer_status_request(self):
    """Frontend polls: 'give me next 10 chunks'"""
    # Get chunks from current ResponseBuffer
    chunks = await response_buffer.get_chunks(start_pos=last_requested_pos)
    return {
        "type": "buffer_status",
        "chunks": [...],
        "is_complete": response_buffer.is_complete(),
        "buffer_size_ms": response_buffer.duration_ms(),
    }
```

### 2.4 Frontend AudioPlayer (React)
**File**: `web_avatar/src/components/AudioPlayer.jsx` (new)

Uses Web Audio API for real-time playback:
```javascript
// Receive chunks via WebSocket
onMessage({type: "audio_chunk", audio_data, phonemes}) {
  // Decode hex → bytes
  // Add to playback queue
  // Start playback if not running
}

// Poll for more chunks
setInterval(async () => {
  const status = await pollBufferStatus()
  updatePlaybackBuffer(status.chunks)
}, 100) // every 100ms

// Web Audio playback loop
playbackLoop() {
  if (playback_queue.length > 0 && playback_time < duration) {
    // Decode PCM → AudioBuffer
    // Play via AudioContext
    // Emit phoneme_sync events
  }
}
```

### 2.5 Avatar Synchronization
**File**: `web_avatar/src/components/AvatarSync.jsx` (new)

Receives PHONEME_DATA events and triggers animations:
```javascript
onPhonemeData({phonemes, sample_positions, timestamp}) {
  // Map phonemes to VRM mouth shapes
  // Schedule animations based on timing
  // Interpolate between phonemes for smooth lip-sync
}
```

## 3. Event Flow

### Complete Pipeline
```
1. User sends: "Olá, como vai?"
2. Bridge.handle_text_input("Olá, como vai?")
   → publishes TRANSCRIPTION_COMPLETE

3. ReasoningBrain processes
   → publishes RESPONSE_READY: {response: "Tudo bem!"}

4. OutputBrain receives RESPONSE_READY
   → creates new ResponseBuffer
   → calls synthesize("Tudo bem!", stream=True)

5. PiperProvider yields chunks:
   AudioChunk(audio_int16_bytes=b'...', phonemes=['t','u','d','u'], sample_rate=22050)

6. OutputBrain for each chunk:
   → buffer.add_chunk(chunk.audio_int16_bytes, chunk.phonemes)
   → publishes AUDIO_CHUNK: {data: b'...', phonemes: ['t','u','d','u']}
   → publishes PHONEME_DATA: {phonemes: [...], sample_positions: [...]}

7. Bridge receives AUDIO_CHUNK
   → sends via WebSocket: {type: "audio_chunk", audio_data: "...", phonemes: [...]}

8. Frontend AudioPlayer receives chunk
   → decodes PCM
   → adds to playback queue

9. AvatarSync receives PHONEME_DATA
   → schedules lip-sync animations

10. AudioPlayer playback loop
    → feeds audio to Web Audio API
    → syncs with avatar animations

11. User hears audio + sees avatar talking
```

## 4. Data Structures

### ResponseBuffer Chunk Entry
```python
@dataclass
class BufferChunk:
    audio_bytes: bytes          # 16-bit PCM
    phonemes: List[str]         # ["t", "u", "d", "u"]
    sample_positions: List[int] # [0, 400, 800, 1200]
    timestamp: float            # when chunk arrived
    sample_rate: int            # 22050 Hz
```

### WebSocket Messages

**Push (Agent → Frontend)**:
```json
{
  "type": "audio_chunk",
  "audio_data": "0401000401...",  // hex-encoded PCM bytes
  "phonemes": ["t", "u", "d", "u"],
  "sample_positions": [0, 400, 800, 1200],
  "timestamp": 1711606800.123,
  "chunk_index": 0
}
```

**Pull Request (Frontend → Agent)**:
```json
{
  "type": "buffer_status_request",
  "last_received_chunk": 5
}
```

**Pull Response (Agent → Frontend)**:
```json
{
  "type": "buffer_status",
  "chunks": [
    {"audio_data": "...", "phonemes": [...], "sample_positions": [...]},
    ...
  ],
  "is_complete": false,
  "buffer_size_seconds": 3.5
}
```

## 5. Error Handling

### Scenarios

| Scenario | Handling |
|----------|----------|
| **Underrun** (frontend runs out of audio) | Buffer.get_chunks() returns what's available; frontend buffers silently |
| **Overflow** (chunks arrive faster than playback) | Ring buffer recycles old data; frontend skips old chunks |
| **Network latency** | Frontend requests buffer_status more frequently if underrun detected |
| **TTS fails** | OutputBrain catches exception, publishes AUDIO_COMPLETE with error |
| **Frontend disconnects** | Buffer cleared, next message starts fresh |

## 6. Testing Strategy

### Unit Tests
1. **ResponseBuffer**: add/retrieve chunks, overflow handling
2. **Bridge outbound handlers**: event → WebSocket message conversion
3. **AudioPlayer**: chunk decoding, queue management, timing

### Integration Tests
1. **End-to-end**: user text → response audio plays
2. **Streaming**: verify chunks arrive progressively (not all at once)
3. **Sync**: phoneme events align with audio timing
4. **Underrun recovery**: buffer handles slow frontend

### Manual Testing
1. Start agent, send message in browser
2. Hear audio response
3. See avatar mouth sync with audio
4. Check console for chunk timing

## 7. Files to Create/Modify

### Create
- `agent/output/response_buffer.py` (ResponseBuffer class)
- `web_avatar/src/components/AudioPlayer.jsx` (Web Audio playback)
- `web_avatar/src/components/AvatarSync.jsx` (Phoneme sync)
- `tests/output/test_response_buffer.py` (unit tests)
- `tests/integration/test_audio_response_pipeline.py` (integration tests)

### Modify
- `agent/brains/output_brain.py` (emit PHONEME_DATA events)
- `agent/bridge.py` (add audio chunk + buffer_status handlers)
- `web_avatar/src/App.jsx` (mount AudioPlayer + AvatarSync)
- `agent/core/messaging/event_bus.py` (add PHONEME_DATA event type)

## 8. Success Criteria

✅ **Functional**:
- User sends message, hears audio response
- Audio plays progressively (not all at once)
- Avatar mouth syncs with speech
- No crashes on errors

✅ **Quality**:
- All tests pass (unit + integration)
- No console errors
- Buffer doesn't overflow
- Clean separation of concerns (buffer / bridge / frontend)

✅ **Performance**:
- Audio latency < 500ms (start hearing within 500ms of LLM response)
- No underruns (smooth playback)
- Memory stable (buffer resets per response)

---

## Questions for Approval

Does this design look correct? Specifically:

1. **Buffer location** (Python backend ring buffer) - OK?
2. **Push + Pull hybrid** (WebSocket push + periodic poll) - makes sense?
3. **Phoneme synchronization** (PHONEME_DATA events for avatar) - worth it?
4. **Test coverage** (unit + integration + manual) - sufficient?
5. **No changes needed to existing TTS code** (OutputBrain just publishes events) - good?

Please confirm if this looks right, or let me know what to adjust before implementation.
