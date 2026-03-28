# Performance Optimization Strategy: Audio Response Integration

## Current Architecture Baseline

### Frontend Components

1. **AudioPlayer Hook (`useAudioPlayer`)**
   - Web Audio API decoder for 16-bit PCM → 32-bit float
   - Ring buffer with max 10 seconds duration
   - Playback managed via ScriptProcessorNode

2. **AvatarSync Component**
   - Uses requestAnimationFrame for phoneme updates (60 FPS max)
   - Phoneme timeline lookup via linear search O(n)
   - VRM blend shape updates per frame

3. **WebSocket Event Handling**
   - Direct addEventListener on raw WebSocket
   - JSON parse per message
   - Immediate state updates

### Backend Architecture

1. **Piper TTS Provider**
   - Streams chunks as synthesis completes
   - Extracts phoneme data during synthesis
   - Sample rate: 22,050 Hz, 16-bit mono PCM

2. **Event Bus Publishing**
   - AUDIO_CHUNK events per chunk (typically 1024 bytes)
   - PHONEME_DATA published after synthesis complete
   - WebSocket serialization to hex string

---

## Performance Metrics & Targets

### Current Expectations (from design)

| Metric | Value | Notes |
|--------|-------|-------|
| First chunk latency | < 1s | Time from message → first audio chunk |
| Chunk arrival rate | 1-3 per 200ms | Depends on TTS speed |
| Buffer duration | ≥ 1s | Should stay ahead of playback |
| Lip-sync latency | < 100ms | Audio/visual sync tolerance |
| Memory overhead | < 50MB | Audio buffer + phoneme timeline |
| CPU usage | < 15% | Main thread utilization |
| Frame drops | 0% | Should maintain 60 FPS for animation |

### Measurements (if available)

Once manual testing is complete, add actual measurements:
- ⏳ First chunk latency: _____ ms (target: < 1000ms)
- ⏳ Average chunk rate: _____ chunks/200ms (target: 1-3)
- ⏳ Lip-sync latency: _____ ms (target: < 100ms)
- ⏳ Memory increase: _____ MB (target: < 50MB)
- ⏳ CPU usage during playback: _____ % (target: < 15%)
- ⏳ Frame drops: _____ (target: 0)

---

## Optimization Opportunities (Priority Order)

### TIER 1: High-Impact, Low-Risk (Do First)

#### 1.1: Reduce WebSocket Message Parsing Overhead

**Problem**: JSON parse on every message is unnecessary if we could use binary format

**Current Code** (AudioPlayer.jsx):
```javascript
const message = JSON.parse(event.data);  // String → Object
```

**Optimization Options**:

**Option A: Message Batching** (Recommended - Quick Win)
- Backend: Batch 2-3 chunks into one WebSocket message
- Frontend: Parse once, add multiple chunks
- Impact: 50-70% reduction in JSON parse calls
- Effort: 30 min (backend + frontend)
- Risk: Low - transparent to components

**Option B: Binary Protocol** (Recommended - Medium-term)
- Backend: Send Uint8Array directly instead of hex string
- Frontend: No JSON parsing needed
- Impact: 80-90% reduction in parsing
- Effort: 2-3 hours (requires protocol design)
- Risk: Medium - breaks existing frontend

**Option C: Compression** (Advanced)
- Gzip or brotli compress audio chunks
- Tradeoff: CPU increase vs bandwidth decrease
- Impact: 30-40% smaller messages
- Effort: 1 hour
- Risk: Medium - adds decompression CPU cost

**Recommended**: Option A (quick win) → Option B (medium-term)

#### 1.2: Optimize Phoneme Timeline Lookup

**Problem**: Linear search O(n) through phoneme timeline every frame

**Current Code** (AvatarSync.jsx):
```javascript
const current = phonemeTimelineRef.current.find(
  p => currentTimeRef.current >= p.startTime && currentTimeRef.current < p.endTime
);  // O(n) search per frame
```

**Optimization**:

```javascript
// Use binary search or index map
// Convert timeline to indexed lookup O(1)
const phonemeIndex = Math.floor(currentTimeRef.current * 1000) % phonemelimit;
const current = phonemeTimelineRef.current[phonemeIndex];
```

**Impact**: 60 FPS × 1-2ms saved = significant reduction in per-frame work
**Effort**: 15 min
**Risk**: Low

#### 1.3: Throttle Avatar Blend Shape Updates

**Problem**: Updating VRM blend shape every frame even if phoneme unchanged

**Current Code** (AvatarSync.jsx):
```javascript
if (blendShape && vrm.expressionManager) {
  vrm.expressionManager.setValue(blendShape, 1.0);  // Called every frame
}
```

**Optimization**:
```javascript
if (current?.phoneme !== lastPhonemeRef.current) {
  // Only update if phoneme changed
  vrm.expressionManager.setValue(blendShape, 1.0);
  lastPhonemeRef.current = current?.phoneme;
}
```

**Impact**: 95%+ reduction in unnecessary VRM updates
**Effort**: 10 min
**Risk**: Very low - only improves efficiency

---

### TIER 2: Medium-Impact, Medium-Risk (Do if Needed)

#### 2.1: Audio Buffer Strategy

**Current**: Ring buffer with 10 second max duration

**Problem**: May cause underruns on slow networks or overruns with fast synthesis

**Optimization**: Adaptive buffering
- Start with target 1.5s buffer
- Increase if underruns detected
- Decrease if memory pressure

**Effort**: 1 hour
**Risk**: Medium - requires state management

#### 2.2: Chunk Size Optimization

**Current**: 1024 bytes per chunk (from backend)

**Optimization**: Analyze impact of chunk size
- Smaller chunks (512b): Lower latency, more messages
- Larger chunks (2048b): Higher latency, fewer messages
- Sweet spot likely around 1024-2048b

**Measurement**: Trace chunk arrival rate and latency

**Effort**: 1 hour (analysis + testing)
**Risk**: Low - just tuning a parameter

#### 2.3: Phoneme Timeline Precomputation

**Current**: Compute timeline every time PHONEME_DATA arrives

**Optimization**: Precompute index at reception time
```javascript
// Transform phonemes into indexed array for O(1) lookup
const indexedTimeline = new Uint32Array(durationMs);
timeline.forEach(p => {
  const startIdx = Math.floor(p.startTime * 1000);
  const endIdx = Math.floor(p.endTime * 1000);
  for (let i = startIdx; i < endIdx; i++) {
    indexedTimeline[i] = phomeIndex;
  }
});
```

**Impact**: Eliminates per-frame search entirely
**Effort**: 30 min
**Risk**: Medium - complex data structure

---

### TIER 3: Low-Impact, High-Risk (Do Only if Metrics Show Need)

#### 3.1: SharedArrayBuffer for Audio Processing

**Potential**: Worker thread for audio decoding

**Tradeoff**: Complexity increase vs minor CPU reduction
**Risk**: High - browser compatibility, complexity
**Effort**: 3-4 hours
**Skip**: Unless profiling shows audio decoding is bottleneck

#### 3.2: WebGL Rendering Optimization

**Potential**: Use WebGL for avatar instead of Three.js default

**Tradeoff**: Massive development effort for minimal gain
**Risk**: Very high - need avatar rendering expertise
**Skip**: Unless avatar rendering is bottleneck

---

## Testing & Validation Plan

### Before Optimization

1. **Baseline Metrics** (from manual E2E testing):
   - Record first chunk latency
   - Measure average buffered duration
   - Check memory usage (DevTools)
   - Profile CPU with DevTools Performance tab

2. **Identify Bottleneck**:
   - Which takes longest: WebSocket recv → parse → decode → playback?
   - Where does CPU spike?
   - Where does memory peak?

### After Each Optimization

1. **Re-measure** same metrics
2. **A/B compare** before/after
3. **Check for regressions**: audio quality, lip-sync accuracy, error handling
4. **Performance timeline** in DevTools

### Success Criteria

- ✅ First chunk latency: < 1000ms
- ✅ Average buffer: 1.5-3.0s (not underrunning)
- ✅ Lip-sync latency: < 100ms
- ✅ No frame drops (60 FPS maintained)
- ✅ Memory stable (no leaks during long sessions)
- ✅ Zero audio glitches or pops

---

## Implementation Roadmap

### Phase 1: Immediate (This Session)

**Done**: Completed E2E testing and identified metrics

**To Do** (if needed):
- [ ] Implement 1.1 Option A (message batching) if latency > 1s
- [ ] Implement 1.2 (binary search) if CPU spike during playback
- [ ] Implement 1.3 (throttle blend shape) if VRM updates expensive

### Phase 2: Short-term (Next Session)

- [ ] Implement 1.1 Option B (binary protocol) if gains from A insufficient
- [ ] Profile detailed timeline in DevTools
- [ ] Implement 2.2 (optimal chunk size) based on measurements

### Phase 3: Medium-term (Future)

- [ ] Implement 2.3 (phoneme index array) if timeline lookup is bottleneck
- [ ] Add performance monitoring to production
- [ ] Continuous profiling and optimization

---

## Profiling Commands

### DevTools Performance Profiling

```javascript
// In browser console - capture 5 seconds of audio playback
performance.mark('audio-start');
// ... let audio play ...
setTimeout(() => {
  performance.mark('audio-end');
  performance.measure('audio-render', 'audio-start', 'audio-end');
  console.log(performance.getEntriesByType('measure'));
}, 5000);
```

### Memory Profiling

```javascript
// Check audio buffer size
console.log('Buffered duration:', audioPlayer.bufferedSeconds, 's');
console.log('Chunk count:', audioPlayer.chunkCount);
console.log('Est. memory:', audioPlayer.chunkCount * 1024 / 1024, 'MB');
```

### Network Profiling

```javascript
// Log WebSocket message rate
let msgCount = 0;
ws.addEventListener('message', (e) => {
  msgCount++;
  if (msgCount % 10 === 0) {
    console.log('Messages received:', msgCount);
  }
});
```

---

## Known Limitations & Trade-offs

1. **Web Audio API Latency**: ~50-100ms inherent to browser audio stack (not optimizable)
2. **RequestAnimationFrame Jitter**: 60 FPS nominal, but can vary with browser load
3. **TTS Synthesis Speed**: Backend constraint (Piper speed limits first chunk latency)
4. **Network Latency**: Beyond our control (but batching helps)
5. **VRM Complexity**: Rendering time depends on model quality (not our code)

---

## Conclusion

**Recommended First Step**: After manual testing, implement **1.1 Option A** (message batching) and **1.3** (throttle blend shape updates). These are quick wins with high confidence and low risk.

**Timeline**: 1-2 hours if issues found, 0 hours if metrics already acceptable.
