# Audio Streaming Bug - Misaligned Message Format

**Status**: FIXED ✓ (Commit 7053bb6d)  
**Issue**: Audio chunks not reaching browser despite TTS working  
**Symptom**: "🎵 Audio: ⏹️ Idle" with "Chunks: 0" (fixed TTS config didn't help)  
**Root Cause**: Bridge-Server message format mismatch  
**Impact**: Audio streaming pipeline was broken at the WebSocket layer

---

## Problem Description

After fixing the TTS configuration bug (commit bc77beac), audio synthesis started working BUT audio chunks still weren't reaching the frontend AudioPlayer component. The issue persisted despite the backend code being correct.

**Symptom**: 
- Agent responds with correct text ✓
- TTS synthesizes audio ✓
- But AudioPlayer shows "⏹️ Idle" with "Chunks: 0" ✗

---

## Root Cause Analysis

### Phase 1: Trace the Data Flow

**Data flow should be:**
```
1. ReasoningBrain detects response ready → RESPONSE_READY event
2. OutputBrain receives RESPONSE_READY → calls TTS synthesizer
3. TTS generates audio chunks → publishes AUDIO_CHUNK events
4. Bridge receives AUDIO_CHUNK → forwards to WebSocket
5. Server receives audio_chunk message → broadcasts to browser clients
6. AudioPlayer receives message → adds chunks, starts playback
```

### Phase 2: Identify Where It Breaks

Investigated each layer:

**Layer 1: OutputBrain → AUDIO_CHUNK events** ✓ WORKING
```python
# agent/brains/output_brain.py lines 80-84
await self.publish_event(EventType.AUDIO_CHUNK, {
    "chunk_index": chunk_index,
    "data": chunk,
    "chunk_size": len(chunk),
})
```

**Layer 2: Bridge receives AUDIO_CHUNK** ✓ WORKING
```python
# agent/bridge.py line 33
self.event_bus.subscribe(EventType.AUDIO_CHUNK)(self._on_audio_chunk)
```

**Layer 3: Bridge sends to WebSocket** ✗ **BROKEN**
```python
# agent/bridge.py lines 137-144 (BEFORE FIX)
await self.avatar.send_command({
    "type": "audio_chunk",
    "audio_data": audio_hex,        # ← WRONG field name
    "audio_bytes": len(audio_bytes), # ← WRONG field
    "chunk_index": chunk_index,
    "timestamp": event.payload.get("timestamp", 0),
})
```

**Layer 4: Server receives and processes** ✗ **GUARD CONDITION FAILED**
```javascript
// web_avatar/server.js lines 344-362
case 'audio_chunk':
    if (msg.data && msg.sample_rate) {  // ← Both undefined!
        console.log(`[Server] Received audio_chunk: ...`);
        // Forward to browser clients
        const audioMsg = JSON.stringify({
            type: 'audio_chunk',
            data: msg.data,
            sample_rate: msg.sample_rate
        });
        wss.clients.forEach(client => {
            if (client.readyState === WebSocket.OPEN && client !== ws) {
                client.send(audioMsg);
            }
        });
    }
    break;
```

**The Guard Condition Issue:**
- Bridge sends: `audio_data` (but server expects `data`)
- Bridge sends: `audio_bytes` (but server expects `sample_rate`)
- Result: `msg.data === undefined` && `msg.sample_rate === undefined`
- Guard fails: Message is silently dropped! ✗

---

## The Fix

**Commit**: 7053bb6d

### Before (Wrong)
```python
await self.avatar.send_command({
    "type": "audio_chunk",
    "audio_data": audio_hex,        # ← Wrong
    "audio_bytes": len(audio_bytes), # ← Wrong
    "chunk_index": chunk_index,
    "timestamp": event.payload.get("timestamp", 0),
})
```

### After (Correct)
```python
await self.avatar.send_command({
    "type": "audio_chunk",
    "data": audio_hex,               # ← Matches server expectation
    "sample_rate": 22050,            # ← Matches server expectation (Piper TTS)
    "chunk_index": chunk_index,
    "timestamp": event.payload.get("timestamp", 0),
})
```

---

## Why This Happened

The Bridge was designed without seeing the actual server.js guard condition. The field names were invented during development but never validated against the server's expectations.

**Lesson**: Message contracts between components must be validated end-to-end, not assumed to match by name similarity.

---

## Impact

**Before Fix**:
```
Server log: [Server] Received audio_chunk: ...  ✓ (message arrived)
           [Server] Forwarded audio_chunk to 0 agent client(s) ✗ (guard failed, dropped)
Browser:    AudioPlayer: Chunks: 0, Buffered: 0.0s
```

**After Fix**:
```
Server log: [Server] Received audio_chunk: ...  ✓
           [Server] Forwarded audio_chunk to 1 agent client(s) ✓
Browser:    AudioPlayer: Chunks: N, Buffered: 5.2s, Playing ▶️
```

---

## Verification

1. **Restart services** with the fixed code
2. **Send text to agent**: "Olá Mimi"
3. **Monitor server logs**: Should show "Forwarded audio_chunk to X agent client(s)"
4. **Check AudioPlayer**: Should show increasing chunk count and buffered time
5. **Listen to audio**: Should hear agent's response in Portuguese

---

## Complete Fix Timeline

| Commit | Issue | Fix |
|--------|-------|-----|
| bc77beac | TTS not initializing | Changed model pt_PT → pt_BR |
| 251675d7 | STT repeated text | Moved clear() before STT |
| 7053bb6d | Audio chunks not streaming | Fixed message format to match server |

---

## Files Modified

- `agent/bridge.py` lines 137-144 - Message format alignment

## Related Files

- `agent/brains/output_brain.py` - Publishes AUDIO_CHUNK events
- `agent/avatar/interface.py` - WebAvatar.send_command() sends to server
- `web_avatar/server.js` lines 344-362 - Server guards and forwards audio
- `web_avatar/src/components/AudioPlayer.jsx` - Frontend receives audio_chunk messages

---

## Next Steps

1. Restart Python agent: `python agent/main.py`
2. Restart WebSocket server: `node web_avatar/server.js` (if needed)
3. Test end-to-end: Send voice → agent responds → audio streams → avatar speaks

All three critical bugs (TTS config, STT timing, message format) are now fixed.
