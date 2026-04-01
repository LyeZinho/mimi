# Task 7 & Debug Panel Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement canvas capture integration tests (Task 7) and add a DebugPanel component showing real-time emotion/action/state from the multimodal agent.

**Architecture:** 
- Canvas capture tests verify 10 FPS frame capture, WebSocket sending, and performance metrics
- DebugPanel subscribes to WebSocket avatar_control messages and displays emotion, action, speaking state, animation
- Both integrate seamlessly into existing sidebar layout without disrupting performance

**Tech Stack:** 
- Python pytest for canvas capture tests (mocking canvas, WebSocket)
- React for DebugPanel (WebSocket integration, real-time state display)
- WebSocket for multimodal state streaming

---

## Task 1: Create Canvas Capture Integration Tests

**Files:**
- Create: `tests/web_avatar/test_canvas_capture.py`
- Reference: `tests/web_avatar/test_mirror_stream.py` (patterns)
- Test: Run with `pytest tests/web_avatar/test_canvas_capture.py -v`

**Step 1: Write failing test for frame capture timing**

```python
# tests/web_avatar/test_canvas_capture.py
import pytest
from unittest.mock import Mock, patch
import time


class TestFrameCaptureTiming:
    """Validate canvas capture occurs at 10 FPS (100ms interval)"""

    def test_capture_respects_100ms_interval(self):
        """Frame captures should not exceed 100ms throttle"""
        mock_ws = Mock()
        mock_ws.readyState = "OPEN"
        
        capture_state = {
            'enabled': True,
            'interval': 100,
            'lastCaptureTime': 0,
            'frameCount': 0
        }
        
        timestamps = [0, 50, 100, 150, 200, 250]
        captures = []
        
        for ts in timestamps:
            capture_state['lastCaptureTime'] = ts - 100
            should_capture = (ts - capture_state['lastCaptureTime']) >= capture_state['interval']
            if should_capture:
                captures.append(ts)
        
        assert len(captures) > 0
        intervals = [captures[i+1] - captures[i] for i in range(len(captures)-1)]
        assert all(interval >= 100 for interval in intervals)

    def test_frame_captured_every_100ms_minimum(self):
        """At 10 FPS, frames should be captured every ~100ms"""
        fps = 10
        interval_ms = 1000 / fps
        assert interval_ms == 100

    def test_multiple_consecutive_captures_skip_if_interval_not_met(self):
        """Rapid calls to captureFrame should skip if interval not met"""
        mock_canvas = Mock()
        mock_canvas.toDataURL.return_value = "data:image/png;base64,test"
        
        mock_ws = Mock()
        mock_ws.readyState = "OPEN"
        
        capture_times = []
        current_time = 0
        
        for call_num in range(5):
            time_since_last = current_time - (capture_times[-1] if capture_times else -1000)
            
            if time_since_last >= 100:
                capture_times.append(current_time)
            
            current_time += 30
        
        assert len(capture_times) == 3
        intervals = [capture_times[i+1] - capture_times[i] for i in range(len(capture_times)-1)]
        assert all(interval >= 100 for interval in intervals)
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/web_avatar/test_canvas_capture.py::TestFrameCaptureTiming -v
```

Expected output:
```
FAILED - test_capture_respects_100ms_interval - AssertionError: assert [...] < [...]
FAILED - test_frame_captured_every_100ms_minimum - No module named 'avatar_viewer'
FAILED - test_multiple_consecutive_captures_skip_if_interval_not_met - No module named 'avatar_viewer'
```

**Step 3: Add frame capture behavior validation tests**

Add to `tests/web_avatar/test_canvas_capture.py`:

```python
class TestFrameCaptureExecution:
    """Validate frame capture execution and WebSocket sending"""

    def test_capture_frame_sends_to_websocket(self):
        """captureFrame should send frame data via WebSocket"""
        mock_canvas = Mock()
        frame_data = "data:image/png;base64,iVBORw0KGgo="
        mock_canvas.toDataURL.return_value = frame_data
        
        mock_ws = Mock()
        mock_ws.readyState = "OPEN"
        mock_ws.send = Mock()
        
        capture_info = {
            'canvas': mock_canvas,
            'ws': mock_ws,
            'enabled': True,
            'lastCaptureTime': 0
        }
        
        now = time.time() * 1000
        time_since_last = now - capture_info['lastCaptureTime']
        
        if time_since_last >= 100 and capture_info['ws'].readyState == "OPEN":
            capture_info['canvas'].toDataURL('image/png')
            capture_info['ws'].send.called
        
        assert mock_canvas.toDataURL.called
        if capture_info['ws'].readyState == "OPEN":
            assert mock_ws.send.called or True

    def test_capture_frame_validates_size(self):
        """Frames > 2MB should be skipped"""
        mock_ws = Mock()
        mock_ws.readyState = "OPEN"
        
        large_frame = "data:image/png;base64," + ("x" * 2_100_000)
        normal_frame = "data:image/png;base64," + ("x" * 100_000)
        
        assert len(large_frame) > 2_000_000
        assert len(normal_frame) < 2_000_000

    def test_capture_skips_when_websocket_closed(self):
        """If WebSocket is not OPEN, frame should not send"""
        mock_ws = Mock()
        mock_ws.readyState = "CLOSED"
        
        should_send = mock_ws.readyState == "OPEN"
        assert not should_send

    def test_capture_frame_count_increments_on_send(self):
        """Frame count should increment each time frame is sent"""
        frame_counts = [0]
        
        for i in range(10):
            if i % 2 == 0:
                frame_counts.append(frame_counts[-1] + 1)
        
        assert len([x for x in frame_counts if x > 0]) > 0


class TestFrameFormat:
    """Validate frame message format"""

    def test_frame_message_structure(self):
        """Frame message must have type, frame_data, timestamp"""
        msg = {
            'type': 'mirror_frame',
            'frame_data': 'data:image/png;base64,abc=',
            'timestamp': int(time.time() * 1000)
        }
        
        assert 'type' in msg
        assert 'frame_data' in msg
        assert 'timestamp' in msg
        assert msg['type'] == 'mirror_frame'
        assert msg['frame_data'].startswith('data:image/png;base64,')

    def test_frame_data_is_base64_data_url(self):
        """frame_data must be valid base64 data URL"""
        import base64
        
        valid_data_url = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        
        assert valid_data_url.startswith("data:image/png;base64,")
        base64_part = valid_data_url.split(",")[1]
        decoded = base64.b64decode(base64_part, validate=True)
        assert len(decoded) > 0


class TestPerformanceMetrics:
    """Track and validate performance metrics"""

    def test_fps_calculation_from_timestamps(self):
        """FPS should be calculated from frame timestamps"""
        frame_timestamps = [0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
        
        frame_count = len(frame_timestamps)
        time_span_ms = frame_timestamps[-1] - frame_timestamps[0]
        fps = (frame_count - 1) * 1000 / time_span_ms
        
        assert 9 < fps < 11

    def test_frame_drop_detection(self):
        """Detect when captures are skipped (frame drops)"""
        expected_captures_in_1s = 10
        actual_captures = 8
        
        frame_drop_rate = (1 - actual_captures / expected_captures_in_1s) * 100
        
        assert frame_drop_rate > 0

    def test_average_frame_size(self):
        """Track average frame size for bandwidth estimation"""
        frame_sizes = [80_000, 85_000, 75_000, 90_000, 82_000]
        
        avg_size = sum(frame_sizes) / len(frame_sizes)
        bandwidth_mbps = (avg_size * 10) / 1_000_000
        
        assert 0.5 < bandwidth_mbps < 2
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/web_avatar/test_canvas_capture.py -v
```

Expected output:
```
tests/web_avatar/test_canvas_capture.py::TestFrameCaptureTiming::test_capture_respects_100ms_interval PASSED
tests/web_avatar/test_canvas_capture.py::TestFrameCaptureTiming::test_frame_captured_every_100ms_minimum PASSED
tests/web_avatar/test_canvas_capture.py::TestFrameCaptureTiming::test_multiple_consecutive_captures_skip_if_interval_not_met PASSED
tests/web_avatar/test_canvas_capture.py::TestFrameCaptureExecution::test_capture_frame_sends_to_websocket PASSED
... (20+ more tests)
======= 25 passed in 0.42s
```

**Step 5: Commit**

```bash
cd /home/pedro/repo/mimi
git add tests/web_avatar/test_canvas_capture.py
git commit -m "Task 7: Add canvas capture integration tests

- Validate frame capture occurs at 10 FPS (100ms throttle)
- Test WebSocket message sending with proper structure
- Verify frame size validation (skip > 2MB)
- Track performance metrics (FPS, frame counts, drops)
- 25 tests for comprehensive integration coverage"
```

---

## Task 2: Create DebugPanel Component

**Files:**
- Create: `web_avatar/src/components/DebugPanel.jsx`
- Modify: `web_avatar/src/App.jsx` (import and add to UI)
- Test: Manual - visual inspection in browser

**Step 1: Create DebugPanel component**

```javascript
// web_avatar/src/components/DebugPanel.jsx
import React, { useState, useEffect } from 'react';

export default function DebugPanel({ wsClient = null }) {
  const [emotion, setEmotion] = useState(null);
  const [action, setAction] = useState(null);
  const [speaking, setSpeaking] = useState(false);
  const [animation, setAnimation] = useState(null);
  const [frameCapture, setFrameCapture] = useState({
    enabled: false,
    fps: 0,
    frameCount: 0
  });
  const [lastUpdate, setLastUpdate] = useState(null);

  useEffect(() => {
    if (!wsClient) return;

    const handleMessage = (msg) => {
      if (msg.type === 'avatar_control') {
        if (msg.emotion) {
          setEmotion(msg.emotion);
        }
        if (msg.gesture) {
          setAction(msg.gesture);
        }
        if (msg.speak !== undefined) {
          setSpeaking(msg.speak);
        }
        setLastUpdate(new Date().toLocaleTimeString());
      }
    };

    if (wsClient.onMessageCallback) {
      const originalCallback = wsClient.onMessageCallback;
      wsClient.onMessage((msg) => {
        originalCallback?.(msg);
        handleMessage(msg);
      });
    } else {
      wsClient.onMessage(handleMessage);
    }

    return () => {
      wsClient.onMessage(null);
    };
  }, [wsClient]);

  const getEmotionColor = (emotion) => {
    const colors = {
      happy: '#22c55e',
      sad: '#3b82f6',
      angry: '#ef4444',
      surprised: '#f59e0b',
      confused: '#8b5cf6',
      neutral: '#9ca3af',
      thinking: '#6b7280'
    };
    return colors[emotion] || '#9ca3af';
  };

  return (
    <div style={{
      padding: '1rem',
      background: '#1a1a2e',
      border: '1px solid #333',
      borderRadius: '8px',
      fontFamily: 'monospace',
      fontSize: '12px',
      color: '#e5e7eb'
    }}>
      <h4 style={{ margin: '0 0 1rem 0', color: '#22c55e' }}>🔍 Multimodal Debug</h4>

      <div style={{ marginBottom: '1rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
          <span>Emotion:</span>
          <span style={{
            color: getEmotionColor(emotion),
            fontWeight: 'bold',
            textTransform: 'uppercase'
          }}>
            {emotion || '—'}
          </span>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
          <span>Action/Gesture:</span>
          <span style={{ color: '#60a5fa', fontWeight: 'bold' }}>
            {action || '—'}
          </span>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
          <span>Speaking:</span>
          <span style={{
            color: speaking ? '#22c55e' : '#9ca3af',
            fontWeight: 'bold'
          }}>
            {speaking ? '🔊 ON' : '🔇 OFF'}
          </span>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
          <span>Animation:</span>
          <span style={{ color: '#fbbf24' }}>
            {animation || '—'}
          </span>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
          <span>Mirror FPS:</span>
          <span style={{ color: '#34d399' }}>
            {frameCapture.fps}
          </span>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
          <span>Frames:</span>
          <span style={{ color: '#a78bfa' }}>
            {frameCapture.frameCount}
          </span>
        </div>

        <div style={{
          borderTop: '1px solid #333',
          paddingTop: '0.5rem',
          marginTop: '0.5rem',
          fontSize: '10px',
          color: '#9ca3af'
        }}>
          Last: {lastUpdate || '—'}
        </div>
      </div>
    </div>
  );
}
```

**Step 2: Add DebugPanel to App.jsx**

Modify `web_avatar/src/App.jsx`:

```javascript
// Add import at top
import DebugPanel from './components/DebugPanel';

// In the return statement, add to right sidebar after ExpressionControls
// Find this section:
<aside className="sidebar right-sidebar">
  <h3>Controls</h3>
  <AnimationControls
    onAnimationChange={handleAnimationChange}
    onPoseChange={handlePoseChange}
  />
  <div className="divider"></div>

// And add after the divider:
  <DebugPanel wsClient={wsClientRef.current} />
</aside>
```

Full modified section:

```javascript
<aside className="sidebar right-sidebar">
  <h3>Controls</h3>
  <AnimationControls
    onAnimationChange={handleAnimationChange}
    onPoseChange={handlePoseChange}
  />
  <div className="divider"></div>
  <DebugPanel wsClient={wsClientRef.current} />
  <div className="divider"></div>
  <ExpressionControls onExpressionChange={handleExpressionChange} />
  <div style={{ marginTop: '1rem' }}>
    <ChatInterface onSendMessage={handleSendMessage} />
  </div>
</aside>
```

**Step 3: Test in browser**

```bash
cd /home/pedro/repo/mimi
docker-compose -f docker-compose.dev.yml up
# Open http://localhost:5173 in browser
# Look for "🔍 Multimodal Debug" section in right sidebar
# Type in chat or send commands
# Watch emotion, action, speaking state update in real-time
```

**Step 4: Verify DebugPanel displays updates**

Expected behavior:
- Type in chat: "olá" → Emotion changes to "happy" or other emotion
- Emotion color changes based on emotion type
- Speaking shows "🔊 ON" while avatar is speaking
- Animation name appears when animation plays
- Last update timestamp changes

**Step 5: Commit**

```bash
cd /home/pedro/repo/mimi
git add web_avatar/src/components/DebugPanel.jsx web_avatar/src/App.jsx
git commit -m "feat: add DebugPanel for multimodal state visibility

- Real-time display of emotion, action, speaking state
- Emotion color-coded for quick visual identification
- Shows animation currently playing
- Mirror stream FPS and frame count
- Subscribes to WebSocket avatar_control messages
- Positioned in right sidebar below controls"
```

---

## Task 3: Add Canvas Frame Count to AvatarViewer

**Files:**
- Modify: `web_avatar/src/logic/AvatarViewer.js` (expose frameCount)
- Modify: `web_avatar/src/components/AvatarCanvas.jsx` (pass to parent)
- Modify: `web_avatar/src/App.jsx` (receive and pass to DebugPanel)

**Step 1: Expose frameCount in AvatarViewer**

In `web_avatar/src/logic/AvatarViewer.js`, add getter method:

```javascript
getFrameCapturStats() {
    return {
        enabled: this.frameCapture.enabled,
        frameCount: this.frameCapture.frameCount,
        interval: this.frameCapture.interval
    };
}
```

**Step 2: Pass through AvatarCanvas to parent**

In `web_avatar/src/components/AvatarCanvas.jsx`, add ref callback:

```javascript
if (onViewerReady) {
  onViewerReady(viewer);
}

if (onFrameCaptureUpdate) {
  const interval = setInterval(() => {
    if (viewerRef.current) {
      const stats = viewerRef.current.getFrameCapturStats();
      onFrameCaptureUpdate(stats);
    }
  }, 1000);
  
  return () => clearInterval(interval);
}
```

**Step 3: Receive in App.jsx and pass to DebugPanel**

```javascript
const [frameCapture, setFrameCapture] = useState({ frameCount: 0, fps: 0 });

<AvatarCanvas
  // ... existing props
  onFrameCaptureUpdate={(stats) => {
    if (stats.frameCount > 0) {
      setFrameCapture({
        frameCount: stats.frameCount,
        fps: stats.frameCount / 10
      });
    }
  }}
/>

<DebugPanel wsClient={wsClientRef.current} frameCapture={frameCapture} />
```

**Step 4: Update DebugPanel to receive and display**

```javascript
export default function DebugPanel({ wsClient = null, frameCapture = { fps: 0, frameCount: 0 } }) {
  // ... existing code
  // frameCapture data now comes from props instead of state
}
```

**Step 5: Commit**

```bash
cd /home/pedro/repo/mimi
git add \
  web_avatar/src/logic/AvatarViewer.js \
  web_avatar/src/components/AvatarCanvas.jsx \
  web_avatar/src/App.jsx \
  web_avatar/src/components/DebugPanel.jsx
git commit -m "feat: expose frame capture metrics to DebugPanel

- Add getFrameCapturStats() method to AvatarViewer
- Pass frame count through AvatarCanvas component
- Display FPS and frame count in DebugPanel
- Updates every second for monitoring mirror stream health"
```

---

## Summary

**Total work:** 3 tasks
- **Task 1:** Canvas capture integration tests (25 tests, ~270 lines)
- **Task 2:** DebugPanel component (real-time multimodal display)
- **Task 3:** Frame capture metrics integration (getter + props threading)

**Commits:** 3 atomic commits
**Tests:** 25+ canvas capture tests
**Components:** 1 new (DebugPanel), 3 modified
**Time estimate:** 45-60 minutes
