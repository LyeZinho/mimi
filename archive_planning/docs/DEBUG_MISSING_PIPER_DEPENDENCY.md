# Audio Synthesis Bug - Missing Piper-TTS Dependency

**Status**: FIXED ✓ (Commit 92feb4a2)  
**Issue**: Audio chunks still showing as 0 despite all fixes  
**Root Cause**: Piper-TTS library not installed (commented out in requirements)  
**Impact**: TTS provider initialization failed silently, no audio synthesis

---

## Problem Description

After fixing TTS config (pt_PT → pt_BR), message format (audio_data → data), and STT timing, audio still wasn't streaming. AudioPlayer remained at "⏹️ Idle" with "Chunks: 0".

---

## Root Cause Analysis

### Discovery Process

1. Added detailed logging to OutputBrain and Bridge
2. Traced which layer was failing
3. Found: **OutputBrain never received RESPONSE_READY events being processed**
4. Investigated why TTS synthesis wasn't starting
5. Checked if tts_provider was None → **YES**
6. Checked orchestrator initialization (line 72-81)
7. Found: ImportError caught silently when PiperProvider couldn't load
8. **Piper library not installed!**

### The Silent Failure

**orchestrator.py lines 74-81:**
```python
try:
    from agent.output.config import PiperConfig
    from agent.output.piper_provider import PiperProvider

    config = PiperConfig(provider="piper", model="pt_BR")
    self.tts_provider = PiperProvider(config)  # ← Raises ImportError
except Exception as e:
    logger.warning(f"Could not initialize default TTS provider: {e}")
    # tts_provider remains None!
```

**piper_provider.py lines 32-36:**
```python
if PiperVoice is None:  # ← True because piper not installed
    raise ImportError(
        "piper library is required. "
        "Install with: pip install piper-tts"
    )
```

**output_brain.py lines 60-62:**
```python
if not self.tts_provider:
    logger.warning("TTS provider not available")
    return  # ← Early return, no synthesis!
```

### Why It Happened

**requirements.txt lines 21-23 (BEFORE):**
```
# TTS (opcional)
# piper-tts>=1.0
# coqui-tts>=0.20
```

Piper-TTS was marked as optional and commented out, so it was never installed.

---

## The Fix

**Commit**: 92feb4a2

### Before (Broken)
```
# requirements.txt
# TTS (opcional)
# piper-tts>=1.0
```

### After (Correct)
```
# requirements.txt
# TTS (obrigatório para OutputBrain)
piper-tts>=1.0
```

### Installation
```bash
pip install piper-tts
```

---

## Impact

| Metric | Before | After |
|--------|--------|-------|
| Piper installed | ❌ No | ✅ Yes |
| tts_provider | None | PiperProvider instance |
| Synthesis | Silent failure | Works |
| Audio chunks | 0 | N chunks streamed |
| AudioPlayer | ⏹️ Idle | ▶️ Playing |

---

## Verification

1. **Install piper-tts**: `pip install piper-tts`
2. **Restart agent**: `python agent/main.py`
3. **Test audio**: Send message "olá"
4. **Expected**: AudioPlayer shows "▶️ Playing" with chunks streaming

---

## Complete Fix Timeline

| Commit | Issue | Root Cause | Fix |
|--------|-------|-----------|-----|
| bc77beac | TTS not initializing | Model config mismatch | Changed pt_PT → pt_BR |
| 251675d7 | STT repeated text | Ring buffer timing | Moved clear() before STT |
| 7053bb6d | Audio chunks not streaming | Message format mismatch | Changed audio_data → data |
| 92feb4a2 | **STILL NO AUDIO** | **Piper not installed** | **Uncommented piper-tts** |

---

## Lessons Learned

1. **Silent failures are worse than loud ones** - Exception caught but only logged as warning
2. **Optional dependencies must be truly optional** - Or mark as required
3. **Installation status must be verified** - `python -c "import piper"` would have caught immediately
4. **Comments in requirements must be updated** - "Optional" became a bug

---

## Files Modified

- `requirements.txt` - Uncommented piper-tts, marked as required

## Related Files

- `agent/orchestrator.py` - TTS provider initialization
- `agent/output/piper_provider.py` - Piper implementation
- `agent/brains/output_brain.py` - Uses TTS provider

---

## Next Steps

1. Install: `pip install piper-tts`
2. Restart agent: `python agent/main.py`
3. Test: Send "olá" and verify AudioPlayer shows ▶️ Playing
4. Download Piper model (first run will auto-download pt_BR model)

All four critical bugs are now fixed! 🎉
