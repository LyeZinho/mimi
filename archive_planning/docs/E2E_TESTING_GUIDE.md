# End-to-End Testing Guide: Audio Response Integration

## Overview

This guide walks through manual E2E testing of the complete audio response pipeline: user message → TTS synthesis → audio streaming → avatar lip-sync.

## Prerequisites

All 3 services must be running:

```bash
# Terminal 1: WebSocket Server
cd web_avatar && node server.js
# Expected: WebSocket/HTTP server rodando em ws://localhost:8765

# Terminal 2: Python Agent
source .venv/bin/activate
python agent/main.py
# Expected: Agent connects to WebSocket and shows brain health checks

# Terminal 3: Frontend
cd web_avatar && npm run dev
# Expected: http://localhost:5173 opens
```

## Test Scenarios

### Scenario 1: Basic Audio Playback (Critical Path)

**Goal**: Verify audio plays progressively when TTS response is generated

**Steps**:

1. Open http://localhost:5173 in browser
2. Wait for "🎵 Audio: ⏹️ Idle" to appear in right sidebar
3. In chat input, type: "Olá Mimi, como você está?"
4. Send message

**Expected Behavior**:

- Chat shows user message
- Agent processes (watch ProcessingCards stage updates)
- Within 2-3 seconds:
  - AudioPlayer shows "🎵 Audio: ⏸️ Buffered"
  - Chunks counter increases: "Chunks: 1, 2, 3..."
  - Buffered duration increases: "Buffered: 0.5s, 1.2s, 2.1s..."
- Audio starts playing automatically (speaker icon or sound)
- After ~3-5 seconds of agent response:
  - Status shows "✓ Complete"
  - Chunks stop increasing
  - Audio finishes playing

**What to Check**:

- ✅ Audio chunks arrive in right order (no gaps)
- ✅ Buffered duration is accurate
- ✅ Audio plays without stuttering
- ✅ Play/Stop buttons work when paused
- ✅ Clear button resets buffer

**Failure Modes**:

| Symptom | Likely Cause |
|---------|--------------|
| "Audio: ⏹️ Idle" (nothing happens) | WebSocket not connected or agent not running |
| "Audio: ⏸️ Buffered" but no chunk count | Event not reaching frontend |
| Chunks arrive but don't play | Web Audio API issue or PCM decoding error |
| Stuttering during playback | Buffer underrun or chunk processing lag |
| "Buffered: NaNs" or 0.0s | Sample rate calculation error |

---

### Scenario 2: Avatar Lip-Sync (Visual Verification)

**Goal**: Verify avatar mouth syncs with speech phonemes

**Steps**:

1. Ensure agent is running with Portuguese TTS (Piper pt_BR model)
2. Open browser to http://localhost:5173
3. Wait for avatar to load
4. Send message: "Que dia maravilhoso!"
5. Watch avatar's mouth during audio playback

**Expected Behavior**:

- Avatar appears with neutral expression
- When audio starts playing:
  - Avatar's mouth opens/closes matching speech
  - Phonemes update in real-time
  - No lag between audio and mouth movement (< 100ms)
- In right sidebar AvatarSync shows:
  - "🎤 Phoneme: [letter]" (updates as speech progresses)
  - "Timeline: X phonemes" (matches response length)
  - "Time: 0.00s" (increments with audio)

**What to Check**:

- ✅ Mouth movement starts when audio starts
- ✅ Phonemes match audio content (visual/auditory sync)
- ✅ Blend shapes applied (mouth opens for 'a', 'e', 'i', 'o', 'u')
- ✅ Consonants (s, t, n, l) have appropriate shapes
- ✅ No delay between audio and visual movement
- ✅ Avatar returns to neutral after speech ends

**Failure Modes**:

| Symptom | Likely Cause |
|---------|--------------|
| "🎤 Idle" always | PHONEME_DATA event not reaching frontend |
| "Timeline: 0 phonemes" | Phoneme extraction failed on backend |
| Mouth doesn't move | Blend shapes not applied or VRM missing expressionManager |
| Delayed mouth movement | Timeline calculation off or performance issue |
| Mouth stuck open/closed | Phoneme data incomplete or blend shape not reset |

---

### Scenario 3: Multiple Responses (Continuity Test)

**Goal**: Verify system handles multiple responses without state corruption

**Steps**:

1. Send: "Qual é o seu nome?"
2. Wait for complete playback + "✓ Complete"
3. Send: "Que hora é agora?"
4. Wait for playback
5. Send: "Conte uma piada"
6. Observe all three responses

**Expected Behavior**:

- Each response has independent buffer
- After each "✓ Complete", chunks reset to 0
- No audio from previous responses plays
- Lip-sync resets between responses
- Third response plays correctly without interference

**What to Check**:

- ✅ Buffer cleared properly between responses
- ✅ No audio artifacts from previous response
- ✅ Phoneme timeline resets
- ✅ Avatar returns to neutral between responses
- ✅ Timing calculations remain accurate

---

### Scenario 4: Error Handling (Robustness Test)

**Goal**: Verify system degrades gracefully under error conditions

#### Sub-test 4a: WebSocket Disconnect

1. Open DevTools (F12) → Network tab
2. Send a message (audio should play)
3. Close WebSocket: DevTools → Network → right-click WebSocket → close
4. Try sending another message

**Expected**:
- Audio stops arriving
- Status shows disconnected
- No console errors
- Reconnect button (if present) works

#### Sub-test 4b: Malformed Message

1. Console: `ws.send(JSON.stringify({type: 'audio_chunk', audio_data: 'invalid'}))`
2. Check if AudioPlayer handles gracefully

**Expected**:
- Error logged to console
- No crash
- Application continues responding

#### Sub-test 4c: Agent Timeout

1. Send very long message (1000+ words)
2. Watch if audio eventually arrives

**Expected**:
- Audio starts within 5-10 seconds (streaming)
- Chunks arrive progressively
- No timeout error

---

### Scenario 5: Performance & Latency (Metrics)

**Goal**: Measure and verify performance meets expectations

**Measurement Points**:

| Metric | Expected | How to Measure |
|--------|----------|----------------|
| First chunk latency | < 1 second | Time from message send to first "Chunks: 1" |
| Chunk arrival rate | 1-3 per 200ms | Watch chunk counter increment rate |
| Buffered duration | ≥ 1.0s | Check "Buffered: Xs" value |
| Lip-sync latency | < 100ms | Visual sync between audio + mouth |
| Memory usage | < 50MB increase | DevTools → Performance tab |
| Playback latency | < 50ms after buffer | Audio should play immediately when buffer ready |

**How to Test**:

1. Open DevTools (F12)
2. Go to Performance tab
3. Start recording
4. Send message
5. Stop when audio complete
6. Analyze timeline for:
   - First WebSocket message received
   - First audio chunk processed
   - First animation frame update
   - Memory allocation/GC

**Acceptable Ranges**:

- Total latency (message → first audio): 1-2 seconds
- Chunk processing: < 50ms per chunk
- Animation frame updates: 60 FPS (16ms per frame)
- No long tasks (> 50ms blocking)

---

## Verification Checklist

### Audio Pipeline ✓

- [ ] AudioPlayer component mounts without errors
- [ ] WebSocket connection detected (isConnected = true)
- [ ] Audio chunk messages received and parsed
- [ ] PCM decoding works (no audio distortion)
- [ ] Web Audio API plays audio smoothly
- [ ] Buffer accumulates correctly
- [ ] Play/Stop/Clear buttons functional
- [ ] Chunk counter accurate
- [ ] Buffered duration calculation correct
- [ ] Audio complete event handled

### Avatar Sync Pipeline ✓

- [ ] AvatarSync component mounts without errors
- [ ] VRM object passed and available
- [ ] PHONEME_DATA events received and parsed
- [ ] Phoneme timeline calculated correctly
- [ ] Blend shapes applied to VRM
- [ ] Phoneme updates in real-time
- [ ] Phoneme timeline resets between responses
- [ ] No blend shape memory leaks (reset to 0.0)
- [ ] Audio/visual sync accurate (< 100ms)

### Integration ✓

- [ ] Both components render in right sidebar
- [ ] Components don't interfere with other UI
- [ ] Multiple responses work sequentially
- [ ] Error handling prevents crashes
- [ ] Console has no critical errors
- [ ] Memory usage stable (no leaks)

---

## Troubleshooting

### "Audio: ⏹️ Idle" - nothing happens

**Checklist**:
1. Is WebSocket connected? Check DevTools Network tab for `ws://localhost:8765`
2. Is Python agent running? `ps aux | grep python`
3. Are AUDIO_CHUNK events being sent? DevTools Network → WS messages
4. Check browser console for errors

**Fix**:
- Restart all 3 services in order
- Check agent logs for TTS errors
- Verify Piper model exists: `~/.cache/piper/pt_BR/pt_BR-faber-medium.onnx`

---

### Audio plays but avatar doesn't move

**Checklist**:
1. Is PHONEME_DATA event being sent? Check WS messages in DevTools
2. Does VRM have expressionManager? Check console: `console.log(vrm.expressionManager)`
3. Is AvatarSync component mounted? Check React DevTools

**Fix**:
- Verify OutputBrain publishes PHONEME_DATA (check agent logs)
- Check PiperProvider extracts phonemes correctly
- Ensure VRM model has blend shapes (not all VRM files have them)

---

### Audio stutters or has gaps

**Checklist**:
1. Are chunks arriving regularly? Watch chunk counter in AudioPlayer
2. Is Web Audio API buffer underrunning? Check browser console for warnings
3. Is CPU usage high? Open DevTools Performance tab

**Fix**:
- Increase chunk buffer size in `useAudioPlayer.js` (increase BUFFER_DURATION_SEC)
- Reduce avatar animation complexity
- Close other browser tabs to free memory

---

### Lip-sync is delayed

**Checklist**:
1. Is phoneme timeline calculated correctly? Check console: `phonemeTimelineRef.current`
2. Is currentTime being updated? Check console logs in AvatarSync
3. Is requestAnimationFrame firing regularly? Performance tab

**Fix**:
- Adjust time calculation in `currentTimeRef.current += ...` formula
- Check sample rate used (22050 vs 44100)
- Ensure audio playback is not paused

---

## Debugging Tips

### Enable Console Logging

Add to components:

```javascript
// In AudioPlayer.jsx useEffect
console.log('[AudioPlayer] Received chunk:', message.audio_data.length, 'bytes');
console.log('[AudioPlayer] Buffer now:', bufferedSeconds.toFixed(2), 's');

// In AvatarSync.jsx
console.log('[AvatarSync] Phoneme timeline:', phonemeTimelineRef.current);
console.log('[AvatarSync] Current time:', currentTimeRef.current.toFixed(3), 's');
```

### WebSocket Message Inspector

```javascript
// In browser console
ws.addEventListener('message', (e) => {
  const msg = JSON.parse(e.data);
  if (msg.type === 'audio_chunk' || msg.type === 'phoneme_data') {
    console.log('[WS]', msg.type, msg);
  }
});
```

### VRM Expression Manager Test

```javascript
// In browser console
vrm.expressionManager.setValue('A', 1.0); // Should open mouth
vrm.expressionManager.setValue('A', 0.0); // Should close mouth
```

---

## Test Results Template

**Date**: ___________
**Tester**: ___________

### Basic Audio Playback
- [ ] ✅ Pass
- [ ] ❌ Fail (describe): _________________

### Avatar Lip-Sync
- [ ] ✅ Pass
- [ ] ❌ Fail (describe): _________________

### Multiple Responses
- [ ] ✅ Pass
- [ ] ❌ Fail (describe): _________________

### Error Handling
- [ ] ✅ Pass
- [ ] ❌ Fail (describe): _________________

### Performance
- [ ] ✅ Pass (latency acceptable)
- [ ] ❌ Fail (describe): _________________

**Overall**: ______ / 5 scenarios passed

**Issues Found**:
1. ___________________
2. ___________________
3. ___________________

**Notes**: ___________________

---

## Next Steps (If All Tests Pass)

1. ✅ **Code review** - Request review of AudioPlayer + AvatarSync implementation
2. ✅ **Performance optimization** - If any metrics fail, optimize
3. ✅ **Documentation** - Update API docs with event formats
4. ✅ **Deployment** - Merge to main and deploy

## Additional Resources

- **Component API**: `docs/AUDIO_RESPONSE_INTEGRATION.md`
- **Audio Hook**: `web_avatar/src/hooks/useAudioPlayer.js`
- **WebSocket Events**: See `agent/core/messaging/event_bus.py`
- **Backend Integration**: `tests/integration/test_audio_response_integration.py`
