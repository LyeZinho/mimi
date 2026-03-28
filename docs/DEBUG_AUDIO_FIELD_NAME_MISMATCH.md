# Bug #5: Audio Chunk Field Name Mismatch in AudioPlayer

**Status**: ✅ FIXED (Commit e49e491b)
**Severity**: CRITICAL - Blocks all audio playback
**Root Cause**: Field name contract mismatch between sender (bridge.py) and receiver (AudioPlayer.jsx)
**Date Fixed**: 2026-03-28 09:52 UTC

## Problem

Audio chunks were being **received by the browser** (as shown in logs: `[Server] Forwarded audio_chunk to 1 agent client(s)`) but **silently dropped** in the AudioPlayer component, resulting in:

- `chunkCount` always showing 0
- No audio buffering
- No audio playback
- Status showing "⏹️ Idle" instead of "▶️ Playing" or "⏸️ Buffered"

## Root Cause

**AudioPlayer.jsx expected the WRONG field name:**

```javascript
// Line 26 - WRONG
addAudioChunk(message.audio_data, message.sample_rate || 22050);
```

**But bridge.py sends:**

```python
# bridge.py lines 140-146
await self.avatar.send_command({
    "type": "audio_chunk",
    "data": audio_hex,  # <-- WRONG: Not "audio_data"
    "sample_rate": 22050,
    "chunk_index": chunk_index,
    "timestamp": event.payload.get("timestamp", 0),
})
```

## Message Contract

**Expected by AudioPlayer:**
```json
{
  "type": "audio_chunk",
  "audio_data": "48656c6c6f...",  // hex string
  "sample_rate": 22050
}
```

**Actually sent by bridge.py:**
```json
{
  "type": "audio_chunk",
  "data": "48656c6c6f...",  // hex string (DIFFERENT FIELD NAME)
  "sample_rate": 22050,
  "chunk_index": 0,
  "timestamp": 1234567890
}
```

## Detection Process

1. **Symptom**: User reports no audio plays after sending message
2. **Logs show**: Server forwarding audio_chunk messages successfully
3. **Browser logs should show**: Chunks being added to buffer, but don't
4. **Hypothesis**: Frontend not receiving chunks or dropping silently
5. **Investigation**: Read AudioPlayer.jsx expecting field name `audio_data`
6. **Discovery**: Field name mismatch — `message.audio_data` is `undefined`
7. **Verification**: Compare with bridge.py sender to confirm field name is `data`

## The Fix

**AudioPlayer.jsx line 26:**

```javascript
// BEFORE (WRONG)
addAudioChunk(message.audio_data, message.sample_rate || 22050);

// AFTER (CORRECT)
addAudioChunk(message.data, message.sample_rate || 22050);
```

Now the field name matches what bridge.py actually sends.

## Verification

1. **Compilation**: No syntax errors (React component)
2. **Field consistency**: `message.data` matches bridge.py line 142
3. **Decoding**: `useAudioPlayer.js` line 18 expects hex string → correctly decodes it
4. **Expected behavior**:
   - Chunks received via WebSocket
   - `addAudioChunk()` decodes hex to PCM float32
   - Chunks buffered in `audioBufferRef.current`
   - `chunkCount` increments
   - `startPlayback()` streams chunks to Web Audio API
   - User hears audio

## Why This Was Missed

- Silent failure: JavaScript doesn't throw on `undefined` field access
- `message.audio_data` is `undefined` → `addAudioChunk(undefined, 22050)` fails silently in try-catch
- No error logged because catch block only logs if JSON parsing fails, not if field is missing
- Misleading server logs: "[Server] Forwarded audio_chunk to 1 agent client(s)" suggests success

## Code Flow (After Fix)

```
Bridge.py (outputs_brain.py)
  ↓ publishes AUDIO_CHUNK event with data=hex_bytes
Bridge._on_audio_chunk()
  ↓ converts bytes to hex
  ↓ sends { type: "audio_chunk", data: hex, sample_rate: 22050 }
WebSocket Server (server.js)
  ↓ receives audio_chunk message
  ↓ forwards to all OTHER clients (browser)
Browser WebSocket Handler (AudioPlayer.jsx)
  ↓ message.type === "audio_chunk" ✓
  ✓ message.data exists (NOW CORRECT)
  ✓ addAudioChunk(message.data, ...) receives HEX string
useAudioPlayer.js
  ↓ converts hex → Uint8Array → Float32Array (PCM)
  ↓ stores in audioBufferRef.current
  ↓ chunkCount increments
  ↓ renders "⏸️ Buffered"
User clicks Play
  ↓ startPlayback() plays chunks via Web Audio API
  ↓ Audio plays 🔊
```

## Testing

**End-to-end test:**

1. Restart Docker: `docker compose -f docker-compose.dev.yml up`
2. Open http://localhost:5173
3. Send text/voice message
4. Observe AudioPlayer status:
   - First chunks arrive: "⏸️ Buffered" with chunk count > 0
   - Audio begins playing: "▶️ Playing"
   - Audio completes: "✓ Complete"

**Browser console:**
```javascript
// Should see NO errors like:
// "addAudioChunk called with undefined audio data"

// Should see chunks being decoded:
// addAudioChunk() called with hex string, decoded to Float32Array
```

## Related Bugs (All Fixed)

1. **Bug #1**: TTS config mismatch (pt_PT → pt_BR)
2. **Bug #2**: STT ring buffer timing (moved clear() before STT)
3. **Bug #3**: Message format mismatch (audio_data → data) - fixed at bridge.py sender
4. **Bug #4**: Missing piper-tts dependency
5. **Bug #5**: AudioPlayer expects WRONG field name (this bug)

All 5 bugs must be fixed for audio to play end-to-end.

## Lesson Learned

**Contract validation is critical for messaging systems:**

- Sender: bridge.py sends field `data`
- Receiver: AudioPlayer expects field `audio_data`
- Result: Silent failure (JavaScript + try-catch swallows errors)

**Prevention for future:**

- Add validation logging: Log field names received vs expected
- Add type checking: Use TypeScript or JSDoc in React components
- Add schema validation: JSON schema for WebSocket message contracts
- Add tests: Unit test message serialization/deserialization round-trip
