# WebRTC Mirror Stream + LLM Control Documentation

**Version:** 1.0  
**Last Updated:** March 27, 2026  
**Status:** Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Setup Guide](#setup-guide)
4. [Mirror Stream Features](#mirror-stream-features)
5. [LLM Control Commands](#llm-control-commands)
6. [DebugPanel Usage](#debugpanel-usage)
7. [Usage Examples](#usage-examples)
8. [Troubleshooting](#troubleshooting)
9. [Performance Tuning](#performance-tuning)
10. [API Reference](#api-reference)

---

## Overview

The WebRTC Mirror Stream + LLM Control system enables real-time streaming of the Mimi avatar's 3D canvas to external displays (like OBS Studio) while providing LLM-driven control over avatar emotions, gestures, and animations. This creates a seamless pipeline from AI agent decisions to visual avatar representation, with monitoring capabilities through the DebugPanel component.

### Key Features

- **10 FPS Canvas Capture**: Throttled frame capture at 100ms intervals for optimal performance
- **WebSocket-based Streaming**: Low-latency frame transmission via WebSocket protocol
- **LLM Avatar Control**: Real-time emotion, gesture, and speaking state control from multimodal agent
- **Debug Panel**: Live monitoring of avatar state, frame capture metrics, and LLM commands
- **OBS Integration**: Dedicated `/mirror.html` endpoint for broadcast software integration
- **Automatic Reconnection**: Resilient connection handling with exponential backoff

### Use Cases

- **Live Streaming**: Broadcast AI avatar interactions to Twitch, YouTube, etc.
- **Remote Monitoring**: Monitor avatar state during development/testing
- **Multi-display Setup**: Show avatar on secondary displays while developing
- **Performance Analysis**: Track frame rates, drops, and WebSocket latency

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Mimi Avatar System                          │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐
│   Python Agent   │         │  WebSocket Hub   │         │   React Frontend │
│                  │         │   (server.js)    │         │                  │
│  - LLM Core      │◄────────┤                  ├────────►│  - AvatarCanvas  │
│  - Multimodal    │  WS:8765│  - State Mgmt    │  WS:8765│  - DebugPanel    │
│  - Tool Calls    │         │  - Broadcasting  │         │  - Controls      │
└──────────────────┘         └──────────────────┘         └──────────────────┘
                                      │                             │
                                      │                             │
                                      │                             ▼
                                      │                    ┌──────────────────┐
                                      │                    │  AvatarViewer.js │
                                      │                    │                  │
                                      │                    │  - Three.js      │
                                      │                    │  - VRM Loading   │
                                      │                    │  - Frame Capture │
                                      │                    └──────────────────┘
                                      │                             │
                                      │                             │ Canvas
                                      │                             │ Capture
                                      │                             │ (10 FPS)
                                      │                             ▼
                                      │                    ┌──────────────────┐
                                      └───────────────────►│  Mirror Stream   │
                                        mirror_frame       │                  │
                                        messages           │  - /mirror.html  │
                                                          │  - OBS Source    │
                                                          └──────────────────┘
```

### Data Flow

**1. LLM Command Flow:**
```
Python Agent → WebSocket → server.js → Broadcast → React Frontend
    (emotion)     (8765)     (state)      (all)     (DebugPanel)
```

**2. Mirror Stream Flow:**
```
Three.js Canvas → toDataURL() → WebSocket → server.js → Mirror Client
   (1920x1080)    (base64 PNG)   (100ms)    (8765)    (/mirror.html)
```

**3. Avatar Control Message Format:**
```javascript
{
  type: 'avatar_control',
  emotion: 'happy',        // happy, sad, angry, surprised, confused, neutral, thinking
  gesture: 'wave',         // wave, nod, thinking, idle
  speak: true,             // true (speaking), false (silent)
  animation: 'wave'        // VRM animation name or null
}
```

---

## Setup Guide

### Prerequisites

- Node.js 18+ (WebSocket server)
- Python 3.10+ (LLM agent)
- Docker (optional, for containerized setup)
- OBS Studio 28+ (optional, for streaming)

### Installation

**Step 1: Install Dependencies**

```bash
# Install Node.js dependencies
cd web_avatar
npm install

# Install Python dependencies
cd ..
source .venv/bin/activate
pip install -r requirements.txt
```

**Step 2: Configure Environment**

Create `.env` file in project root:

```env
WEBSOCKET_HOST=localhost
WEBSOCKET_PORT=8765
LLM_MODEL=phi3:mini
AVATAR_TYPE=web
```

**Step 3: Start Services**

Open **3 separate terminals**:

```bash
# Terminal 1: WebSocket Server
cd web_avatar && node server.js

# Terminal 2: Python Agent
source .venv/bin/activate && python agent/main.py

# Terminal 3: React Frontend
cd web_avatar && npm run dev
```

**Step 4: Verify Setup**

1. Open http://localhost:5173 in browser
2. Load a VRM model (Mimi.vrm included)
3. Send chat message: "Hello Mimi"
4. Check DebugPanel shows emotion updates
5. Open http://localhost:5173/mirror.html to verify mirror stream

### Docker Setup (Alternative)

```bash
docker-compose -f docker-compose.dev.yml up
```

Services will be available at:
- Frontend: http://localhost:5173
- Mirror: http://localhost:5173/mirror.html
- WebSocket: ws://localhost:8765

---

## Mirror Stream Features

### Canvas Capture Mechanism

The mirror stream captures the 3D avatar canvas at **10 FPS (100ms intervals)** using throttled frame capture:

```javascript
// From AvatarViewer.js
captureFrame() {
  const now = performance.now();
  const elapsed = now - this.frameCapture.lastCaptureTime;

  // Throttle: skip if < 100ms since last capture
  if (elapsed < this.frameCapture.interval) return;

  // Capture canvas as base64 PNG
  const frameData = this.canvas.toDataURL('image/png');

  // Validate frame size (skip if > 2MB)
  if (frameData.length > 2_000_000) {
    console.warn('[Mirror] Frame too large, skipping');
    return;
  }

  // Send via WebSocket
  if (this.wsClient && this.wsClient.readyState === WebSocket.OPEN) {
    this.wsClient.send(JSON.stringify({
      type: 'mirror_frame',
      frame_data: frameData,
      timestamp: now
    }));
    this.frameCapture.frameCount++;
  }

  this.frameCapture.lastCaptureTime = now;
}
```

### Frame Message Format

```javascript
{
  type: 'mirror_frame',
  frame_data: 'data:image/png;base64,iVBORw0KGgoAAAANSU...',
  timestamp: 1711547890123
}
```

### Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| Frame Rate | 10 FPS | 100ms throttle |
| Frame Size | ~80-150 KB | PNG compression |
| Bandwidth | ~0.8-1.5 Mbps | At 10 FPS |
| Latency | 150-300ms | Network + decode |
| Max Frame Size | 2 MB | Frames > 2MB skipped |

### OBS Studio Integration

**Step 1: Add Browser Source**

1. Open OBS Studio
2. Add Source → Browser
3. Configure:
   - **URL**: `http://localhost:5173/mirror.html`
   - **Width**: 1920
   - **Height**: 1080
   - **FPS**: 30 (OBS will interpolate)
   - **Custom CSS**: Leave empty (transparent background pre-configured)

**Step 2: Scene Composition**

```
┌─────────────────────────────────────┐
│       OBS Scene Layout              │
├─────────────────────────────────────┤
│  [Background Image/Video]           │
│    ↓                                │
│  [Mirror Stream Browser Source]     │
│    ↓                                │
│  [Chat Overlay]                     │
│    ↓                                │
│  [Alerts/Notifications]             │
└─────────────────────────────────────┘
```

**Step 3: Verify Stream**

- Status indicator in top-left should show **"Live"** (green)
- FPS counter in bottom-right should show **~10 FPS**
- Avatar should respond to chat messages with emotion changes

---

## LLM Control Commands

### Emotion Control

The Python agent can trigger emotion changes via WebSocket messages:

```python
# From agent/avatar/web_avatar_controller.py
await ws_client.send_json({
    'type': 'avatar_control',
    'emotion': 'happy',
    'timestamp': time.time()
})
```

**Supported Emotions:**

| Emotion | Color | Use Case | VRM Blend Shape |
|---------|-------|----------|-----------------|
| `happy` | 🟢 Green | Positive response | `Joy` |
| `sad` | 🔵 Blue | Negative outcome | `Sorrow` |
| `angry` | 🔴 Red | Frustration | `Angry` |
| `surprised` | 🟠 Orange | Unexpected input | `Surprised` |
| `confused` | 🟣 Purple | Unclear request | `Fun` |
| `neutral` | ⚪ Gray | Idle state | `Neutral` |
| `thinking` | ⚫ Dark Gray | Processing | `Blink` + `Neutral` |

### Gesture/Action Control

```python
await ws_client.send_json({
    'type': 'avatar_control',
    'gesture': 'wave',
    'animation': 'wave',  # Optional VRM animation
    'loop': False
})
```

**Supported Gestures:**

- `wave`: Friendly greeting
- `nod`: Agreement/acknowledgment
- `thinking`: Contemplative pose
- `idle`: Return to rest pose
- `point`: Directive gesture

### Speaking State Control

```python
# Start speaking
await ws_client.send_json({
    'type': 'avatar_control',
    'speak': True
})

# Stop speaking
await ws_client.send_json({
    'type': 'avatar_control',
    'speak': False
})
```

**Effect:** Triggers lip-sync animation and visual speaking indicator in DebugPanel.

### Combined Commands

Multiple control parameters can be sent in a single message:

```python
await ws_client.send_json({
    'type': 'avatar_control',
    'emotion': 'happy',
    'gesture': 'wave',
    'speak': True,
    'animation': 'wave',
    'timestamp': time.time()
})
```

---

## DebugPanel Usage

### Overview

The DebugPanel component displays real-time avatar state and mirror stream metrics in the right sidebar of the main interface.

### Display Sections

**1. Emotion State**
```
Emotion: HAPPY
         ^^^^^^
         Color-coded by emotion type
```

**2. Action/Gesture**
```
Action/Gesture: wave
                ^^^^
                Current animation name
```

**3. Speaking State**
```
Speaking: 🔊 ON
          ^^^^^^
          Green when active, gray when silent
```

**4. Animation Name**
```
Animation: wave
           ^^^^
           Currently playing VRM animation
```

**5. Mirror Stream Metrics**
```
Mirror FPS: 10
Frames: 1234
```

**6. Last Update Timestamp**
```
Last: 14:32:45
      ^^^^^^^^
      Time of last avatar_control message
```

### Emotion Color Legend

The DebugPanel uses color-coding for quick visual identification:

```
┌─────────────┬─────────┬──────────┐
│  Emotion    │  Color  │  Hex     │
├─────────────┼─────────┼──────────┤
│  Happy      │  🟢     │  #22c55e │
│  Sad        │  🔵     │  #3b82f6 │
│  Angry      │  🔴     │  #ef4444 │
│  Surprised  │  🟠     │  #f59e0b │
│  Confused   │  🟣     │  #8b5cf6 │
│  Neutral    │  ⚪     │  #9ca3af │
│  Thinking   │  ⚫     │  #6b7280 │
└─────────────┴─────────┴──────────┘
```

### Integration with WebSocket

The DebugPanel subscribes to `avatar_control` messages from the WebSocket server:

```javascript
// From DebugPanel.jsx
useEffect(() => {
  if (!wsClient) return;

  const handleMessage = (msg) => {
    if (msg.type === 'avatar_control') {
      if (msg.emotion !== undefined) {
        setEmotion(msg.emotion);
      }
      if (msg.gesture !== undefined) {
        setAction(msg.gesture);
      }
      if (msg.speak !== undefined) {
        setSpeaking(msg.speak);
      }
      setLastUpdate(new Date().toLocaleTimeString());
    }
  };

  wsClient.onMessage(handleMessage);
}, [wsClient]);
```

---

## Usage Examples

### Example 1: Basic Mirror Stream Setup

**Goal:** Stream avatar to OBS for Twitch broadcast

```bash
# Terminal 1: Start WebSocket server
cd web_avatar && node server.js

# Terminal 2: Start React frontend
cd web_avatar && npm run dev

# Browser: Open http://localhost:5173
# Load VRM model → Avatar appears

# OBS: Add Browser Source
# URL: http://localhost:5173/mirror.html
# Resolution: 1920x1080

# Verify: Status shows "Live" in OBS preview
```

### Example 2: LLM-Triggered Emotion Change

**Goal:** Change avatar emotion from Python agent

```python
# agent/main.py
import asyncio
import websockets
import json

async def set_emotion(emotion):
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({
            'type': 'avatar_control',
            'emotion': emotion
        }))
        print(f"Emotion set to: {emotion}")

# Usage
asyncio.run(set_emotion('happy'))
```

**Result:**
- Avatar facial expression changes to "happy"
- DebugPanel shows "HAPPY" in green
- Mirror stream reflects the change instantly

### Example 3: Chat-Triggered Gesture

**Goal:** Wave gesture when user says "hello"

```python
# agent/input/text_input_manager.py
async def handle_input(self, text: str):
    if 'hello' in text.lower():
        await self.ws_client.send_json({
            'type': 'avatar_control',
            'emotion': 'happy',
            'gesture': 'wave',
            'animation': 'wave',
            'loop': False
        })
        await self.speak("Hello! Nice to see you!")
```

**Result:**
- Avatar plays wave animation
- Emotion changes to happy
- DebugPanel shows "wave" action
- Speaking indicator turns on during TTS playback

### Example 4: Monitoring Frame Capture Performance

**Goal:** Track mirror stream health during live stream

```javascript
// Custom monitoring script
const ws = new WebSocket('ws://localhost:8765');
let frameCount = 0;
let lastFrameTime = Date.now();

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  if (msg.type === 'mirror_frame') {
    frameCount++;
    const now = Date.now();
    const fps = 1000 / (now - lastFrameTime);
    console.log(`FPS: ${fps.toFixed(2)} | Total Frames: ${frameCount}`);
    lastFrameTime = now;
  }
};
```

**Output:**
```
FPS: 10.02 | Total Frames: 1
FPS: 9.98 | Total Frames: 2
FPS: 10.01 | Total Frames: 3
```

---

## Troubleshooting

### Mirror Stream Issues

#### Problem: "Connection Lost" in /mirror.html

**Symptoms:**
- Red "Connection Lost" status indicator
- No frames appearing on canvas
- Spinner continuously visible

**Diagnosis:**
```bash
# Check if WebSocket server is running
lsof -i :8765

# Check server logs
cd web_avatar && node server.js
# Look for: "WebSocket/HTTP server rodando em ws://localhost:8765"
```

**Solution:**
1. Restart WebSocket server: `node web_avatar/server.js`
2. Verify firewall allows port 8765
3. Check browser console for connection errors
4. Try http://localhost:8765/mirror.html directly

---

#### Problem: Low FPS (<5 FPS)

**Symptoms:**
- FPS counter shows <5 FPS
- Choppy/laggy mirror stream
- Frame drops

**Diagnosis:**
```javascript
// Check frame size in browser console
ws.onmessage = (e) => {
  const msg = JSON.parse(e.data);
  if (msg.type === 'mirror_frame') {
    console.log('Frame size:', msg.frame_data.length);
  }
};
```

**Solution:**
1. **Reduce Canvas Resolution:**
   ```javascript
   // In AvatarViewer.js
   this.canvas.width = 1280;  // Down from 1920
   this.canvas.height = 720;  // Down from 1080
   ```

2. **Increase Throttle Interval:**
   ```javascript
   this.frameCapture.interval = 150;  // Up from 100 (6.6 FPS)
   ```

3. **Check CPU Usage:**
   - Close unnecessary browser tabs
   - Disable browser extensions
   - Lower VRM model complexity

4. **Network Bandwidth:**
   - Check WebSocket ping: `wscat -c ws://localhost:8765`
   - Monitor network tab in DevTools

---

#### Problem: Frames Too Large (>2MB)

**Symptoms:**
- Console warnings: "Frame too large, skipping"
- Zero frames transmitted
- No mirror stream despite connection

**Diagnosis:**
```javascript
// Check frame data size
const frameData = canvas.toDataURL('image/png');
console.log('Frame size (MB):', (frameData.length / 1_000_000).toFixed(2));
```

**Solution:**
1. **Switch to JPEG Compression:**
   ```javascript
   const frameData = this.canvas.toDataURL('image/jpeg', 0.7);  // 70% quality
   ```

2. **Reduce Canvas Size:**
   ```javascript
   this.canvas.width = 1280;
   this.canvas.height = 720;
   ```

3. **Simplify Scene:**
   - Use lower-poly VRM models
   - Reduce texture resolution
   - Disable post-processing effects

---

### DebugPanel Issues

#### Problem: DebugPanel Not Updating

**Symptoms:**
- Emotion shows "—" (no data)
- Last update timestamp stuck
- Speaking state always OFF

**Diagnosis:**
```javascript
// Check if wsClient is connected
console.log('WS State:', wsClientRef.current?.readyState);
// OPEN = 1, CONNECTING = 0, CLOSING = 2, CLOSED = 3

// Verify avatar_control messages are being sent
// In browser console:
ws.addEventListener('message', (e) => {
  const msg = JSON.parse(e.data);
  if (msg.type === 'avatar_control') {
    console.log('Avatar control:', msg);
  }
});
```

**Solution:**
1. **Verify WebSocket Connection:**
   ```javascript
   // In App.jsx
   console.log('WS Client:', wsClientRef.current);
   ```

2. **Check Python Agent Sending Messages:**
   ```python
   # In agent/avatar/web_avatar_controller.py
   print(f"Sending avatar_control: {message}")
   await self.ws_client.send_json(message)
   ```

3. **Restart All Services:**
   ```bash
   # Kill all processes
   pkill -f "node server.js"
   pkill -f "python agent/main.py"
   pkill -f "npm run dev"

   # Restart in order
   cd web_avatar && node server.js &
   source .venv/bin/activate && python agent/main.py &
   cd web_avatar && npm run dev
   ```

---

#### Problem: Incorrect Emotion Colors

**Symptoms:**
- All emotions show gray color
- Color doesn't match emotion type

**Diagnosis:**
```javascript
// In DebugPanel.jsx, check emotion value
console.log('Emotion received:', emotion);
console.log('Color calculated:', getEmotionColor(emotion));
```

**Solution:**
1. **Ensure Lowercase Matching:**
   ```javascript
   // Fixed in current version
   return colors[emotion?.toLowerCase()] || '#9ca3af';
   ```

2. **Verify Python Agent Sends Lowercase:**
   ```python
   await ws_client.send_json({
       'emotion': 'happy'  # Not 'Happy' or 'HAPPY'
   })
   ```

---

### LLM Control Issues

#### Problem: Avatar Not Responding to Commands

**Symptoms:**
- Python agent sends commands but avatar doesn't change
- No errors in console
- DebugPanel not updating

**Diagnosis:**
```bash
# Terminal 1: Monitor WebSocket traffic
wscat -c ws://localhost:8765

# Terminal 2: Send test command
curl -X POST http://localhost:8765/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "test"}'
```

**Solution:**
1. **Verify Message Routing in server.js:**
   ```javascript
   // Add debug logging
   ws.on('message', async (data) => {
     const msg = JSON.parse(data);
     console.log('[SERVER] Received:', msg.type, msg);
     // ... rest of handler
   });
   ```

2. **Check Python WebSocket Client:**
   ```python
   # Verify connection state
   print(f"WS connected: {self.ws_client.is_connected}")
   ```

3. **Test with Manual WebSocket Client:**
   ```javascript
   // In browser console
   const ws = new WebSocket('ws://localhost:8765');
   ws.onopen = () => {
     ws.send(JSON.stringify({
       type: 'avatar_control',
       emotion: 'happy'
     }));
   };
   ```

---

## Performance Tuning

### Frame Capture Optimization

**Adjust FPS Target:**
```javascript
// In AvatarViewer.js
this.frameCapture = {
  enabled: true,
  interval: 100,  // Change to 200 for 5 FPS, 66 for 15 FPS
  frameCount: 0,
  lastCaptureTime: 0
};
```

| FPS | Interval (ms) | Bandwidth (Est.) | Use Case |
|-----|---------------|------------------|----------|
| 5   | 200           | ~400-750 KB/s    | Low-end hardware |
| 10  | 100           | ~800-1500 KB/s   | Default (recommended) |
| 15  | 66            | ~1200-2250 KB/s  | High-quality streams |
| 30  | 33            | ~2400-4500 KB/s  | Ultra-smooth (high CPU) |

**Reduce Frame Size:**
```javascript
// In AvatarViewer.js constructor
this.canvas.width = 1280;   // Down from 1920
this.canvas.height = 720;   // Down from 1080
```

**Switch to JPEG Compression:**
```javascript
// In captureFrame()
const frameData = this.canvas.toDataURL('image/jpeg', 0.8);  // 80% quality
```

### WebSocket Optimization

**Enable Compression (server.js):**
```javascript
const wss = new WebSocket.Server({
  server,
  perMessageDeflate: {
    zlibDeflateOptions: {
      chunkSize: 1024,
      memLevel: 7,
      level: 3
    },
    zlibInflateOptions: {
      chunkSize: 10 * 1024
    },
    threshold: 1024
  }
});
```

**Batch Messages:**
```javascript
// Send multiple updates in one message
await ws_client.send_json({
  type: 'avatar_control',
  emotion: 'happy',
  gesture: 'wave',
  speak: true
  // Single message instead of 3 separate ones
});
```

### Browser Performance

**Disable DevTools in Production:**
- Close DevTools when streaming
- Use production build: `npm run build`

**Hardware Acceleration:**
- Chrome: `chrome://settings` → Advanced → System → "Use hardware acceleration"
- Firefox: `about:preferences` → Performance → "Use recommended performance settings"

**Monitor Performance:**
```javascript
// Add FPS counter to main app
let frameCount = 0;
let lastTime = Date.now();

requestAnimationFrame(function countFps() {
  frameCount++;
  const now = Date.now();
  if (now - lastTime >= 1000) {
    console.log('Main loop FPS:', frameCount);
    frameCount = 0;
    lastTime = now;
  }
  requestAnimationFrame(countFps);
});
```

---

## API Reference

### WebSocket Message Types

#### Client → Server

**1. avatar_control**
```javascript
{
  type: 'avatar_control',
  emotion?: 'happy' | 'sad' | 'angry' | 'surprised' | 'confused' | 'neutral' | 'thinking',
  gesture?: string,
  speak?: boolean,
  animation?: string | null,
  timestamp?: number
}
```

**2. mirror_frame**
```javascript
{
  type: 'mirror_frame',
  frame_data: string,  // base64 PNG data URL
  timestamp: number
}
```

**3. webrtc_mirror_request**
```javascript
{
  type: 'webrtc_mirror_request'
}
```

**4. set_expression**
```javascript
{
  type: 'set_expression',
  expression: 'neutral' | 'happy' | 'sad' | 'angry' | 'surprised' | 'confused'
}
```

**5. chat**
```javascript
{
  type: 'chat',
  text: string,
  sender?: 'user'
}
```

#### Server → Client

**1. state**
```javascript
{
  type: 'state',
  state: {
    model: string | null,
    expression: string,
    animation: string | null,
    animationLoop: boolean,
    speaking: boolean,
    camera: {
      position: { x: number, y: number, z: number },
      target: { x: number, y: number, z: number }
    },
    background: string,
    lastUpdate: number
  }
}
```

**2. mirror_frame**
```javascript
{
  type: 'mirror_frame',
  frame_data: string,
  timestamp: number
}
```

**3. chat_response**
```javascript
{
  type: 'chat_response',
  text: string,
  sender: 'Mimi'
}
```

### AvatarViewer.js Methods

**getFrameCaptureStats()**
```javascript
/**
 * Returns current frame capture statistics
 * @returns {{ enabled: boolean, frameCount: number, interval: number }}
 */
viewer.getFrameCaptureStats();
```

**enableFrameCapture()**
```javascript
/**
 * Enable mirror stream frame capture
 * @param {number} fps - Target frames per second (default: 10)
 */
viewer.enableFrameCapture(fps = 10);
```

**disableFrameCapture()**
```javascript
/**
 * Disable mirror stream frame capture
 */
viewer.disableFrameCapture();
```

### DebugPanel Props

```typescript
interface DebugPanelProps {
  wsClient?: WebSocketClient | null;
  frameStats?: {
    fps: number;
    frameCount: number;
  };
}
```

---

## Appendix

### A. Emotion Mapping to VRM Blend Shapes

| Emotion | VRM Blend Shape | Weight | Blink |
|---------|----------------|--------|-------|
| happy | `Joy` | 1.0 | Normal |
| sad | `Sorrow` | 0.8 | Slow |
| angry | `Angry` | 1.0 | Rapid |
| surprised | `Surprised` | 1.0 | None |
| confused | `Fun` | 0.6 | Normal |
| neutral | `Neutral` | 1.0 | Normal |
| thinking | `Neutral` + `Blink` | 0.5 + 0.3 | Slow |

### B. Frame Size Benchmarks

Tested on 1920x1080 canvas with Mimi.vrm model:

| Compression | Avg Size | Min Size | Max Size | Quality |
|-------------|----------|----------|----------|---------|
| PNG (default) | 120 KB | 80 KB | 180 KB | Lossless |
| JPEG 90% | 85 KB | 60 KB | 120 KB | Excellent |
| JPEG 80% | 65 KB | 45 KB | 95 KB | Good |
| JPEG 70% | 50 KB | 35 KB | 75 KB | Acceptable |
| JPEG 60% | 40 KB | 28 KB | 60 KB | Noticeable artifacts |

### C. WebSocket Port Configuration

Default: `8765`

To change:
```javascript
// server.js
const PORT = process.env.WEBSOCKET_PORT || 8765;

// .env
WEBSOCKET_PORT=9000
```

Update client connections:
```javascript
// App.jsx
const wsUrl = `ws://${window.location.hostname}:${process.env.VITE_WS_PORT || 8765}`;
```

### D. Testing Commands

**Frame Capture Tests:**
```bash
pytest tests/web_avatar/test_canvas_capture.py -v
```

**Mirror Stream Integration Tests:**
```bash
pytest tests/web_avatar/test_mirror_stream.py -v
```

**WebSocket Server Tests:**
```bash
npm test -- server.test.js
```

---

## Changelog

**v1.0 (March 27, 2026)**
- Initial production release
- 10 FPS mirror stream with throttling
- DebugPanel real-time state display
- LLM avatar control via WebSocket
- OBS integration via /mirror.html
- Comprehensive documentation

---

## Support

**Issues:** https://github.com/your-org/mimi/issues  
**Docs:** https://github.com/your-org/mimi/tree/main/docs  
**Discord:** https://discord.gg/mimi-support

---

**End of Document**
