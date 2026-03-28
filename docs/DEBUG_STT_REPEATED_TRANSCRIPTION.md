# STT Repeated Transcription Bug - Root Cause & Fix

**Status**: FIXED ✓ (Commit 251675d7)  
**Issue**: User's voice transcribed as "O que é o que é o que é..." instead of actual speech  
**Root Cause**: Ring buffer timing in STT pipeline  
**Fix Impact**: Eliminated buffer overlap, ensures clean audio per recording session

---

## Problem Description

User reported that voice input was being transcribed as repeated gibberish:
```
Input: User says "hello"
Output: "O que é o que é o que é..." (repeated nonsense)
```

This was NOT a Whisper model issue, but rather corrupted/overlapping audio being fed to STT.

---

## Root Cause Analysis

### The Bug (Phase 1 Investigation)

**File**: `agent/brains/input_brain.py`  
**Method**: `handle_audio_frame()` (lines 77-83) + `_run_stt()` (lines 122-144)

**Original sequence:**
```python
# Line 77: VAD detects end of speech
elif not vad_result and self.is_listening:
    self.is_listening = False
    
    # Line 79: Get snapshot of ALL audio in ring buffer (10 seconds of history)
    ring_snapshot = await self.buffer_manager.get_ring_snapshot()
    
    # Line 83: Run STT on snapshot
    await self._run_stt(ring_snapshot)
    
# Inside _run_stt() [Line 144]:
# Clear only happens AFTER STT completes
await self.buffer_manager.ring_buffer.clear()
```

**The Problem:**

1. User speaks → audio accumulates in ring buffer: `[user_audio]`
2. VAD detects silence → triggers STT
3. STT processes snapshot: `[user_audio]`
4. **STT completes** → buffer FINALLY clears
5. User speaks again quickly
6. Ring buffer still has fragments: `[old_fragments, new_audio]`
7. VAD detects end → STT gets mixed audio: `[old + new]`
8. Whisper transcribes hybrid chunks → produces **repeated/corrupted text**

**Why "O que é o que é"?**

The repeated phrase suggests background noise or silence periods being captured and misinterpreted as speech. When old buffer fragments contain these artifacts and combine with new user audio, Whisper struggles and produces hallucinated/repeated text.

### Pattern Analysis (Phase 2)

**Key insight**: Ring buffer clear() happens AFTER processing, not before next recording.

This creates a **race condition** in the audio pipeline:
- Recording 1: `ring_buffer = [user_1]` → snapshot → STT → **clear**
- Recording 2 starts immediately, ring buffer NOT empty yet
- Recording 2: `ring_buffer = [fragments_1, user_2]` → snapshot contains both!
- STT sees mixed audio → corrupted output

---

## Solution

### The Fix (Phase 3 Implementation)

**Commit**: 251675d7  
**Changes**: Move `ring_buffer.clear()` from AFTER STT to BEFORE STT

**New sequence:**
```python
elif not vad_result and self.is_listening:
    self.is_listening = False
    ring_snapshot = await self.buffer_manager.get_ring_snapshot()
    
    # ← MOVED HERE: Clear BEFORE STT
    await self.buffer_manager.ring_buffer.clear()
    
    # Now STT gets clean snapshot
    await self._run_stt(ring_snapshot)
```

**Result:**
```
Recording 1: ring_buffer=[user_1] → snapshot → CLEAR → STT(snapshot)
Recording 2: ring_buffer=[] (empty) → user_2 arrives → snapshot → CLEAR → STT(snapshot)
```

Each STT call processes **only** the current recording's audio.

---

## Verification

### Why This Fix Works

1. ✅ **No overlap**: Ring buffer clears before next audio arrives
2. ✅ **Fresh state**: Each recording session starts with empty buffer
3. ✅ **Clean audio**: STT only sees audio from current utterance
4. ✅ **No artifacts**: No mixing of old and new audio
5. ✅ **Deterministic**: Timing no longer impacts transcription quality

### How to Test

1. **Restart services** with fixed code
2. **Test STT directly**:
   ```bash
   # Python agent terminal
   python agent/main.py
   ```
3. **Send voice via browser**:
   - Go to http://localhost:5173
   - Say: "olá" → should transcribe as "olá", not "o que é o que é"
   - Say: "como vai você?" → should transcribe cleanly
4. **Verify logs**:
   ```bash
   tail -f /tmp/agent_output.log | grep "STT Result"
   ```
   Expected: Clean, accurate transcriptions matching user speech

---

## Buffer Lifecycle (Corrected)

**BEFORE FIX** (buggy):
```
User Speech → RingBuffer Write → VAD Detect → STT Snapshot → STT Process → Clear
                                                                              ↑
                                                         Next recording can overlap here
```

**AFTER FIX** (correct):
```
User Speech → RingBuffer Write → VAD Detect → STT Snapshot → Clear → STT Process
                                                                 ↑
                                     Ring buffer is fresh for next recording
```

---

## Timeline of Fixes

| Commit | Issue | Fix |
|--------|-------|-----|
| bc77beac | TTS: model="pt_PT" mismatch | Changed to model="pt_BR" |
| 251675d7 | STT: repeated transcription | Moved clear() before STT |

---

## Lessons Learned

1. **Ring buffer timing is critical**: Clear must happen at the right point in the lifecycle
2. **Order matters**: Clear before processing, not after
3. **Race conditions in async**: Buffer state can be inconsistent between events
4. **Multi-frame overlap**: Real-time audio needs atomic buffer boundaries
5. **Systematic debugging works**: Root cause found by tracing data flow, not guessing

---

## Reference

- **Input Brain**: `agent/brains/input_brain.py`
- **Buffer Manager**: `agent/buffers/audio_buffers.py`
- **Ring Buffer**: `agent/buffers/audio_buffers.py::RingBuffer` (lines 38-160)
- **STT Engine**: `agent/audio/stt_engine.py`
- **VAD Engine**: `agent/audio/vad_engine.py`

**Related Issues**:
- TTS bug: `docs/DEBUG_TTS_FIX.md` (Commit bc77beac)
- E2E testing: `docs/E2E_TESTING_GUIDE.md`
- Phase 3 integration: `docs/PHASE_3_INTEGRATION_SUMMARY.md`
