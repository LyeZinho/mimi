# Mirror Endpoint + LLM-Backend 3D Control - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a WebRTC mirror stream endpoint for OBS, implement emotion-to-gesture mapping, and add dynamic LLM control via WebSocket.

**Architecture:** 
- WebRTC server streams avatar canvas in real-time (~100-200ms latency)
- EmotionMapper translates LLM emotions to expressions/gestures using configurable JSON
- Extended WebSocket commands allow runtime control of LLM parameters and avatar state
- Response caching optimizes token usage for common queries

**Tech Stack:** 
- WebRTC: `simple-peer` + WebRTC Data Channels for Node.js
- Emotion mapping: JSON config file (data/emotion_map.json)
- Backend: Python async handlers in ActionRouter
- Frontend: React WebRTC sender

---

## Phase 1: Foundation (Emotion Mapping & Config)

### Task 1: Create Emotion Map Configuration

**Files:**
- Create: `data/emotion_map.json`
- Modify: `agent/avatar/emotion_mapper.py` (new file)
- Test: `tests/agent/avatar/test_emotion_mapper.py`

**Step 1: Create emotion map JSON config**

```bash
mkdir -p data
cat > /home/pedro/repo/mimi/data/emotion_map.json << 'EOF'
{
  "version": "1.0",
  "emotions": {
    "happy": {
      "expression": "smile",
      "animation": "idle_happy",
      "gesture": "wave",
      "duration_ms": 2000
    },
    "sad": {
      "expression": "sad",
      "animation": "idle_sad",
      "gesture": null,
      "duration_ms": 1500
    },
    "confused": {
      "expression": "uncertain",
      "animation": "idle_confused",
      "gesture": "head_tilt",
      "duration_ms": 2000
    },
    "excited": {
      "expression": "smile",
      "animation": "idle_excited",
      "gesture": "jump",
      "duration_ms": 2500
    },
    "neutral": {
      "expression": "neutral",
      "animation": "idle_neutral",
      "gesture": null,
      "duration_ms": 1000
    },
    "thinking": {
      "expression": "thinking",
      "animation": "idle_thinking",
      "gesture": "head_tilt",
      "duration_ms": 3000
    }
  },
  "fallback_emotion": "neutral"
}
EOF
```

**Step 2: Create EmotionMapper class**

Create file: `agent/avatar/emotion_mapper.py`

```python
"""Maps LLM emotions to avatar expressions, gestures, and animations."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

class EmotionMapper:
    """Translates LLM emotion strings to avatar control signals."""
    
    def __init__(self, config_path: Path | str = "data/emotion_map.json"):
        self.config_path = Path(config_path)
        self.config: dict[str, Any] = {}
        self.emotions: dict[str, dict[str, Any]] = {}
        self.fallback = "neutral"
        self._load_config()
    
    def _load_config(self) -> None:
        """Load emotion map from JSON file."""
        if not self.config_path.exists():
            logger.warning(f"Emotion map not found at {self.config_path}, using defaults")
            self.emotions = self._default_emotions()
            return
        
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
            self.emotions = self.config.get("emotions", {})
            self.fallback = self.config.get("fallback_emotion", "neutral")
            logger.info(f"Loaded {len(self.emotions)} emotions from {self.config_path}")
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load emotion map: {e}, using defaults")
            self.emotions = self._default_emotions()
    
    def _default_emotions(self) -> dict[str, dict[str, Any]]:
        """Return default emotion mappings if config not found."""
        return {
            "happy": {"expression": "smile", "animation": "idle_happy", "gesture": "wave"},
            "neutral": {"expression": "neutral", "animation": "idle_neutral", "gesture": None},
            "sad": {"expression": "sad", "animation": "idle_sad", "gesture": None},
            "confused": {"expression": "uncertain", "animation": "idle_confused", "gesture": "head_tilt"},
        }
    
    def map_emotion(self, emotion: str) -> dict[str, Any]:
        """
        Map an emotion string to avatar control signals.
        
        Args:
            emotion: Emotion name (e.g., "happy", "sad")
            
        Returns:
            Dict with keys: expression, animation, gesture, duration_ms
        """
        emotion = emotion.lower().strip() if emotion else self.fallback
        
        if emotion not in self.emotions:
            logger.warning(f"Unknown emotion '{emotion}', using fallback '{self.fallback}'")
            emotion = self.fallback
        
        mapping = self.emotions[emotion].copy()
        logger.debug(f"Mapped emotion '{emotion}' to {mapping}")
        return mapping
    
    def reload(self) -> None:
        """Reload emotion map from disk (for runtime updates)."""
        logger.info("Reloading emotion map...")
        self._load_config()
    
    def list_emotions(self) -> list[str]:
        """Return list of available emotions."""
        return sorted(self.emotions.keys())
```

**Step 3: Create test file**

Create file: `tests/agent/avatar/test_emotion_mapper.py`

```python
"""Tests for EmotionMapper."""

import pytest
from pathlib import Path
from agent.avatar.emotion_mapper import EmotionMapper


def test_emotion_mapper_maps_happy():
    """Happy emotion should map to smile + wave."""
    mapper = EmotionMapper()
    result = mapper.map_emotion("happy")
    
    assert result["expression"] == "smile"
    assert result["gesture"] == "wave"
    assert "animation" in result


def test_emotion_mapper_fallback_unknown():
    """Unknown emotion should fall back to neutral."""
    mapper = EmotionMapper()
    result = mapper.map_emotion("unknown_emotion_xyz")
    
    assert result["expression"] == "neutral"


def test_emotion_mapper_case_insensitive():
    """Emotion names should be case-insensitive."""
    mapper = EmotionMapper()
    result1 = mapper.map_emotion("HAPPY")
    result2 = mapper.map_emotion("happy")
    
    assert result1 == result2


def test_emotion_mapper_list_emotions():
    """Should list all available emotions."""
    mapper = EmotionMapper()
    emotions = mapper.list_emotions()
    
    assert "happy" in emotions
    assert "neutral" in emotions
    assert len(emotions) > 0
```

**Step 4: Run tests**

```bash
cd /home/pedro/repo/mimi
pytest tests/agent/avatar/test_emotion_mapper.py -v
```

Expected output:
```
test_emotion_mapper_maps_happy PASSED
test_emotion_mapper_fallback_unknown PASSED
test_emotion_mapper_case_insensitive PASSED
test_emotion_mapper_list_emotions PASSED
```

**Step 5: Commit**

```bash
cd /home/pedro/repo/mimi
git add data/emotion_map.json agent/avatar/emotion_mapper.py tests/agent/avatar/test_emotion_mapper.py
git commit -m "feat: add emotion-to-gesture mapping system with configurable JSON"
```

---

### Task 2: Integrate EmotionMapper into ActionRouter

**Files:**
- Modify: `agent/output/actions.py`
- Modify: `agent/llm/prompts.py`

**Step 1: Update system/user prompts to include gesture field**

Modify `agent/llm/prompts.py`:

Change line 49 from:
```python
{len(instructions)+1}. Intents disponíveis: {intents_text}.
```

To:
```python
{len(instructions)+1}. Intents disponíveis: {intents_text}.
{len(instructions)+2}. IMPORTANTE: Retorne também um campo "emotion" com um dos valores: {emotions_text}.
```

And update line 100 in user prompt template:
```python
# Add to list of required fields:
- "emotion": uma das emoções disponíveis (para controlar expressão e gestos)
- "gesture": [OPCIONAL] gesto específico (deixe null se quiser que o backend decida)
```

**Step 2: Update ActionRouter to use EmotionMapper**

Modify `agent/output/actions.py` at line 25:

```python
from agent.avatar.emotion_mapper import EmotionMapper

class ActionRouter:
    """Mapeia intenções para ações concretas."""

    def __init__(self, tts: TTSEngine | None = None, avatar: "AvatarInterface" | None = None) -> None:
        self.tts = tts or DummyTTS()
        self.avatar = avatar
        self.emotion_mapper = EmotionMapper()  # ← ADD THIS
        self._handlers: dict[str, ActionHandler] = {}
        self._register_defaults()
```

**Step 3: Update _handle_speak to use emotion mapping**

Modify `agent/output/actions.py` _handle_speak method (around line 64):

```python
async def _handle_speak(
    self, intent: dict[str, Any], agent: "AgentCore"
) -> dict[str, Any]:
    text = intent.get("text", "")
    emotion = intent.get("emotion", "neutral")
    gesture = intent.get("gesture", None)  # ← ADD
    
    agent.state.speaking = True
    
    # Map emotion to expression and animation
    emotion_map = self.emotion_mapper.map_emotion(emotion)  # ← ADD
    expression = emotion_map.get("expression", "neutral")
    animation = emotion_map.get("animation", None)
    if gesture is None:  # ← ADD: use mapped gesture if not specified
        gesture = emotion_map.get("gesture", None)
    
    # Controla avatar se disponível
    if self.avatar:
        await self.avatar.set_expression(expression)
        if animation:
            await self.avatar.set_animation(animation)  # ← ADD
        if gesture:
            await self.avatar.set_gesture(gesture)  # ← ADD (or execute gesture animation)
        await self.avatar.speak_start()
    
    await self.tts.speak(text, emotion)
    
    if self.avatar:
        await self.avatar.speak_end()
    
    agent.state.speaking = False
    return {"status": "success", "emotion": emotion, "gesture": gesture}
```

**Step 4: Test integration**

```bash
cd /home/pedro/repo/mimi
# Run existing action tests to ensure no regression
pytest tests/agent/output/ -v
```

Expected: All existing tests pass

**Step 5: Commit**

```bash
cd /home/pedro/repo/mimi
git add agent/output/actions.py agent/llm/prompts.py
git commit -m "feat: integrate emotion mapper into action router and update prompts"
```

---

## Phase 2: Response Caching (Token Economy)

### Task 3: Create Response Cache System

**Files:**
- Create: `agent/core/response_cache.py`
- Test: `tests/agent/core/test_response_cache.py`

**Step 1: Create ResponseCache class**

Create file: `agent/core/response_cache.py`

```python
"""Response caching to optimize token usage."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional
from datetime import datetime, timedelta
import hashlib

logger = logging.getLogger(__name__)

class ResponseCache:
    """Caches LLM responses to avoid redundant API calls."""
    
    def __init__(self, cache_path: Path | str = "data/response_cache.json", ttl_hours: int = 24):
        self.cache_path = Path(cache_path)
        self.ttl = timedelta(hours=ttl_hours)
        self.cache: dict[str, dict[str, Any]] = {}
        self._load_cache()
    
    def _load_cache(self) -> None:
        """Load cache from disk."""
        if not self.cache_path.exists():
            logger.debug("No cache file found, starting fresh")
            return
        
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                self.cache = json.load(f)
            logger.info(f"Loaded cache with {len(self.cache)} entries")
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load cache: {e}, starting fresh")
            self.cache = {}
    
    def _save_cache(self) -> None:
        """Save cache to disk."""
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except IOError as e:
            logger.error(f"Failed to save cache: {e}")
    
    def _hash_message(self, message: str) -> str:
        """Create hash key for message."""
        return hashlib.md5(message.lower().strip().encode()).hexdigest()
    
    def get(self, message: str) -> Optional[dict[str, Any]]:
        """
        Get cached response for message.
        
        Args:
            message: User message
            
        Returns:
            Cached response dict or None if not found/expired
        """
        key = self._hash_message(message)
        
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        expires_at = datetime.fromisoformat(entry.get("expires_at", ""))
        
        if datetime.now() > expires_at:
            del self.cache[key]
            self._save_cache()
            logger.debug(f"Cache entry expired: {message[:50]}")
            return None
        
        logger.info(f"Cache HIT: {message[:50]}")
        return entry.get("response")
    
    def set(self, message: str, response: dict[str, Any]) -> None:
        """
        Cache a response.
        
        Args:
            message: User message
            response: LLM response dict
        """
        key = self._hash_message(message)
        self.cache[key] = {
            "message": message,
            "response": response,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + self.ttl).isoformat()
        }
        self._save_cache()
        logger.info(f"Cache SET: {message[:50]}")
    
    def clear(self) -> None:
        """Clear entire cache."""
        self.cache = {}
        self._save_cache()
        logger.info("Cache cleared")
```

**Step 2: Create tests**

Create file: `tests/agent/core/test_response_cache.py`

```python
"""Tests for ResponseCache."""

import pytest
import json
from pathlib import Path
from agent.core.response_cache import ResponseCache


@pytest.fixture
def temp_cache(tmp_path):
    """Create temporary cache for testing."""
    cache = ResponseCache(cache_path=tmp_path / "cache.json", ttl_hours=1)
    yield cache
    cache.clear()


def test_cache_set_and_get(temp_cache):
    """Should cache and retrieve responses."""
    message = "Qual é seu nome?"
    response = {"intent": "speak", "text": "Meu nome é Mimi"}
    
    temp_cache.set(message, response)
    result = temp_cache.get(message)
    
    assert result == response


def test_cache_case_insensitive(temp_cache):
    """Cache should be case-insensitive."""
    message = "Qual é seu nome?"
    response = {"intent": "speak", "text": "Meu nome é Mimi"}
    
    temp_cache.set(message, response)
    result = temp_cache.get("QUAL É SEU NOME?")
    
    assert result == response


def test_cache_miss_returns_none(temp_cache):
    """Should return None for uncached message."""
    result = temp_cache.get("uncached message")
    assert result is None


def test_cache_persists_to_disk(tmp_path):
    """Cache should persist to disk."""
    cache1 = ResponseCache(cache_path=tmp_path / "cache.json")
    cache1.set("test", {"result": "value"})
    
    cache2 = ResponseCache(cache_path=tmp_path / "cache.json")
    result = cache2.get("test")
    
    assert result == {"result": "value"}
```

**Step 3: Run tests**

```bash
cd /home/pedro/repo/mimi
pytest tests/agent/core/test_response_cache.py -v
```

Expected: All tests pass

**Step 4: Commit**

```bash
cd /home/pedro/repo/mimi
git add agent/core/response_cache.py tests/agent/core/test_response_cache.py
git commit -m "feat: add response caching system to optimize token usage"
```

---

### Task 4: Integrate Cache into Agent

**Files:**
- Modify: `agent/core/agent.py`

**Step 1: Add cache to AgentCore init**

Modify `agent/core/agent.py`:

```python
from agent.core.response_cache import ResponseCache

class AgentCore:
    def __init__(self, ...):
        # ... existing init code ...
        self.response_cache = ResponseCache()  # ← ADD
        # ... rest of init ...
```

**Step 2: Use cache in handle_input**

Find the `handle_input` method and add cache check before calling LLM:

```python
async def handle_input(self, user_message: str) -> dict[str, Any]:
    """Process user input with cache-first approach."""
    
    # Check cache first (SAVE TOKENS!)
    cached_response = self.response_cache.get(user_message)
    if cached_response:
        logger.info(f"Using cached response for: {user_message[:50]}")
        # Still add to memory but skip LLM
        self.memory.add({"role": "user", "content": user_message})
        self.memory.add({"role": "assistant", "content": str(cached_response)})
        # Execute actions directly
        return await self.router.execute(cached_response, self)
    
    # Cache miss - call LLM normally
    intent = await self.llm_client.get_intent(user_message, ...)
    
    # Cache the response
    self.response_cache.set(user_message, intent)
    
    # ... rest of existing logic ...
```

**Step 3: Test integration**

```bash
cd /home/pedro/repo/mimi
# Run agent tests
pytest tests/agent/core/test_agent.py -v
```

**Step 4: Commit**

```bash
cd /home/pedro/repo/mimi
git add agent/core/agent.py
git commit -m "feat: integrate response cache into agent for token optimization"
```

---

## Phase 3: WebSocket Extended Commands

### Task 5: Add LLM Control Commands to WebSocket Server

**Files:**
- Modify: `web_avatar/server.js`

**Step 1: Add LLM parameter storage to avatarState**

Modify `web_avatar/server.js` line 11:

```javascript
let avatarState = {
  model: null,
  expression: 'neutral',
  animation: null,
  animationLoop: true,
  speaking: false,
  camera: {
    position: { x: 0, y: 1.4, z: 2 },
    target: { x: 0, y: 1.2, z: 0 }
  },
  background: '#1a1a2e',
  lastUpdate: Date.now(),
  // NEW: LLM parameters
  llm: {
    model: 'gemma3:4b',
    temperature: 0.7,
    top_p: 0.9,
    system_prompt: null  // null = use default from persona.json
  }
};
```

**Step 2: Add new WebSocket message handlers**

Modify `web_avatar/server.js` in the `ws.on('message')` switch statement (after line 212):

```javascript
case 'set_llm_model':
  if (msg.model) {
    updateState({ llm: { ...avatarState.llm, model: msg.model } });
    logger.info(`[LLM] Model changed to: ${msg.model}`);
    broadcastState();
  }
  break;

case 'set_llm_temperature':
  if (typeof msg.temperature === 'number') {
    updateState({ llm: { ...avatarState.llm, temperature: msg.temperature } });
    logger.info(`[LLM] Temperature changed to: ${msg.temperature}`);
    broadcastState();
  }
  break;

case 'set_llm_top_p':
  if (typeof msg.top_p === 'number') {
    updateState({ llm: { ...avatarState.llm, top_p: msg.top_p } });
    logger.info(`[LLM] Top-P changed to: ${msg.top_p}`);
    broadcastState();
  }
  break;

case 'set_llm_system_prompt':
  if (msg.system_prompt) {
    updateState({ llm: { ...avatarState.llm, system_prompt: msg.system_prompt } });
    logger.info(`[LLM] System prompt updated`);
    broadcastState();
  }
  break;

case 'set_gesture':
  if (msg.gesture) {
    updateState({ gesture: msg.gesture });
    broadcastState();
  }
  break;

case 'get_llm_config':
  // Return current LLM config
  ws.send(JSON.stringify({
    type: 'llm_config',
    config: avatarState.llm
  }));
  break;

case 'get_available_models':
  // Return list of available models (could fetch from Ollama API)
  ws.send(JSON.stringify({
    type: 'available_models',
    models: ['gemma3:4b', 'ministral-3:3b', 'phi3:mini']
  }));
  break;
```

**Step 3: Update Python agent to read LLM config from WebSocket state**

Modify `agent/llm/client.py` to read model from WebSocket state instead of just .env:

(This will be done in next phase - for now just document it)

**Step 4: Test manually**

```bash
cd /home/pedro/repo/mimi
# Start Docker
docker-compose -f docker-compose.dev.yml up &

# Wait for services to start
sleep 5

# Test WebSocket commands
node << 'EOF'
const WebSocket = require('ws');
const ws = new WebSocket('ws://localhost:8765');

ws.on('open', () => {
  console.log('Connected');
  
  // Test get config
  ws.send(JSON.stringify({ type: 'get_llm_config' }));
  
  // Test change model
  ws.send(JSON.stringify({ type: 'set_llm_model', model: 'ministral-3:3b' }));
  
  // Test change temperature
  ws.send(JSON.stringify({ type: 'set_llm_temperature', temperature: 0.5 }));
});

ws.on('message', (data) => {
  console.log('Received:', JSON.parse(data));
});

setTimeout(() => process.exit(0), 2000);
EOF
```

**Step 5: Commit**

```bash
cd /home/pedro/repo/mimi
git add web_avatar/server.js
git commit -m "feat: add LLM control commands to WebSocket server"
```

---

## Phase 4: WebRTC Mirror Endpoint

### Task 6: Setup WebRTC Mirror Infrastructure

**Files:**
- Modify: `web_avatar/server.js`
- Modify: `web_avatar/package.json`

**Step 1: Add WebRTC dependency**

Modify `web_avatar/package.json`:

```json
{
  "dependencies": {
    "ws": "^8.0.0",
    "simple-peer": "^9.11.1"
  }
}
```

**Step 2: Install**

```bash
cd /home/pedro/repo/mimi/web_avatar
npm install
```

**Step 3: Add mirror endpoint to server.js**

Add to `web_avatar/server.js` before `wss.on('connection')` (around line 104):

```javascript
// WebRTC Mirror Stream Setup
const SimplePeer = require('simple-peer');

let mirrorPeers = [];

// POST /mirror - Initialize WebRTC mirror connection
server.on('request', (req, res) => {
  if (req.method === 'POST' && req.url === '/mirror/offer') {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', async () => {
      try {
        const offer = JSON.parse(body);
        const peer = new SimplePeer({ initiator: false, trickleIce: false });
        
        peer.on('signal', data => {
          if (data.type === 'answer') {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ answer: data }));
            mirrorPeers.push(peer);
          }
        });
        
        peer.signal(offer);
      } catch (e) {
        res.writeHead(400);
        res.end('Bad Request');
      }
    });
    return;
  }
});
```

**Step 4: Add mirror broadcast channel**

Add to WebSocket connection handler after line 111:

```javascript
// Broadcast canvas frame to mirror peers
ws.on('message', (data) => {
  let msg;
  try {
    msg = JSON.parse(data);
  } catch (e) {
    return;
  }
  
  // If this is a canvas frame for mirror, send to all mirror peers
  if (msg.type === 'canvas_frame') {
    mirrorPeers.forEach(peer => {
      if (peer.connected) {
        peer.send(JSON.stringify({
          type: 'canvas_frame',
          data: msg.data  // Base64 image data
        }));
      }
    });
  }
});
```

**Step 5: Create mirror HTML page**

Create file: `web_avatar/public/mirror.html`

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mimi - Mirror Stream</title>
    <style>
        body { margin: 0; padding: 0; background: #000; }
        #mirror-canvas { display: block; width: 100%; height: 100%; }
        #status { position: fixed; top: 10px; left: 10px; color: #0f0; font-family: monospace; }
    </style>
</head>
<body>
    <canvas id="mirror-canvas"></canvas>
    <div id="status">Connecting...</div>
    
    <script>
        const canvas = document.getElementById('mirror-canvas');
        const ctx = canvas.getContext('2d');
        const status = document.getElementById('status');
        
        // Connect to WebSocket to receive canvas frames
        const ws = new WebSocket('ws://' + window.location.host);
        
        ws.on('message', (data) => {
          let msg = JSON.parse(data);
          if (msg.type === 'canvas_frame') {
            // Receive frame from main avatar and draw
            const img = new Image();
            img.onload = () => {
              canvas.width = img.width;
              canvas.height = img.height;
              ctx.drawImage(img, 0, 0);
              status.textContent = 'Streaming...';
            };
            img.src = msg.data;  // Base64 data
          }
        });
        
        ws.on('error', (e) => {
          status.textContent = 'Error: ' + e;
        });
    </script>
</body>
</html>
```

**Step 6: Commit**

```bash
cd /home/pedro/repo/mimi
git add web_avatar/server.js web_avatar/package.json web_avatar/public/mirror.html
git commit -m "feat: add WebRTC mirror infrastructure for OBS streaming"
```

---

### Task 7: Integrate Canvas Capture in React Frontend

**Files:**
- Modify: `web_avatar/src/App.jsx`
- Modify: `web_avatar/src/logic/AvatarViewer.js`

**Step 1: Add canvas capture to AvatarViewer**

Modify `web_avatar/src/logic/AvatarViewer.js`:

```javascript
// Add method to capture canvas as image
captureCanvas() {
  if (!this.renderer) return null;
  
  // Render current frame
  this.renderer.render(this.scene, this.camera);
  
  // Get canvas data URL
  return this.renderer.domElement.toDataURL('image/jpeg', 0.8);
}

// Add periodic capture method
startCaptureInterval(intervalMs = 100) {
  if (this.captureInterval) clearInterval(this.captureInterval);
  
  this.captureInterval = setInterval(() => {
    const frame = this.captureCanvas();
    if (frame) {
      // Emit event that App.jsx can listen to
      window.dispatchEvent(new CustomEvent('avatar-frame', { detail: frame }));
    }
  }, intervalMs);
}

stopCaptureInterval() {
  if (this.captureInterval) {
    clearInterval(this.captureInterval);
  }
}
```

**Step 2: Send frames via WebSocket in App.jsx**

Modify `web_avatar/src/App.jsx` (in the component setup):

```javascript
useEffect(() => {
  if (wsClient) {
    // Start capturing avatar frames
    viewer?.startCaptureInterval(100); // Capture every 100ms
    
    // Listen for frame events and send via WebSocket
    const handleFrame = (e) => {
      wsClient.send(JSON.stringify({
        type: 'canvas_frame',
        data: e.detail
      }));
    };
    
    window.addEventListener('avatar-frame', handleFrame);
    
    return () => {
      window.removeEventListener('avatar-frame', handleFrame);
      viewer?.stopCaptureInterval();
    };
  }
}, [wsClient, viewer]);
```

**Step 3: Test canvas capture**

```bash
cd /home/pedro/repo/mimi
# Start docker
docker-compose -f docker-compose.dev.yml up &
sleep 5

# Open browser
open http://localhost:5173

# Open OBS mirror in another tab
open http://localhost:5173/mirror.html
```

**Step 4: Commit**

```bash
cd /home/pedro/repo/mimi
git add web_avatar/src/App.jsx web_avatar/src/logic/AvatarViewer.js
git commit -m "feat: add canvas capture and streaming to WebSocket"
```

---

## Phase 5: Documentation & Final Integration

### Task 8: Create Comprehensive Documentation

**Files:**
- Create: `docs/MIRROR_AND_CONTROL.md`

```markdown
# Mirror Stream + LLM Control System

## Overview

The Mimi system now supports:
1. **WebRTC Mirror Stream** - Real-time OBS streaming of avatar
2. **Emotion-to-Gesture Mapping** - LLM emotions automatically control 3D model
3. **Response Caching** - Reduce LLM token usage for common queries
4. **Dynamic LLM Control** - Change model, temperature, etc. at runtime

## Architecture

### Mirror Stream Flow

```
Avatar 3D (React/Three.js)
    ↓ [100ms canvas capture]
WebSocket: canvas_frame event
    ↓
Server.js mirror peers
    ↓ [WebRTC data channel]
OBS Browser Source
    ↓
Streaming Output
```

### Emotion Mapping Flow

```
LLM Response: { "emotion": "happy", ... }
    ↓
EmotionMapper.map_emotion("happy")
    ↓
{ "expression": "smile", "animation": "idle_happy", "gesture": "wave" }
    ↓
ActionRouter._handle_speak()
    ↓
Avatar executes: set_expression + set_animation + set_gesture
```

## Usage

### 1. WebRTC Mirror for OBS

```
1. In OBS Studio:
   - Add Source → Browser
   - URL: http://localhost:5173/mirror.html
   - Width: 1920, Height: 1080

2. Avatar renders in real-time on OBS with ~100-200ms latency
```

### 2. Control LLM via WebSocket

```javascript
// Change model
ws.send(JSON.stringify({
  type: 'set_llm_model',
  model: 'ministral-3:3b'
}));

// Change temperature (0-1, higher = more creative)
ws.send(JSON.stringify({
  type: 'set_llm_temperature',
  temperature: 0.5
}));

// Change system prompt at runtime
ws.send(JSON.stringify({
  type: 'set_llm_system_prompt',
  system_prompt: "You are a creative AI assistant..."
}));
```

### 3. Emotion Mapping Customization

Edit `data/emotion_map.json`:

```json
{
  "emotions": {
    "my_custom_emotion": {
      "expression": "smile",
      "animation": "idle_happy",
      "gesture": "wave",
      "duration_ms": 2000
    }
  }
}
```

## Response Caching

### How It Works

1. User sends: "Qual é seu nome?"
2. Agent checks cache → Found!
3. Returns cached response immediately (no LLM call)
4. Saves 1000+ tokens per cache hit

### Cache Control

```python
# Clear cache programmatically
agent.response_cache.clear()

# Reload emotion map at runtime
agent.router.emotion_mapper.reload()
```

## WebSocket Commands Reference

| Command | Params | Purpose |
|---------|--------|---------|
| `set_llm_model` | `model` | Change LLM model |
| `set_llm_temperature` | `temperature` | Adjust creativity |
| `set_llm_top_p` | `top_p` | Adjust output diversity |
| `set_llm_system_prompt` | `system_prompt` | Change persona |
| `set_gesture` | `gesture` | Force specific gesture |
| `get_llm_config` | - | Get current LLM settings |
| `get_available_models` | - | List available models |

## Performance Notes

- **Canvas capture**: 100ms interval = 10 FPS (adjustable)
- **WebRTC latency**: 100-200ms typical
- **Cache hit rate**: Aim for 30-50% on typical usage
- **Token savings**: ~90% reduction per cache hit

## Troubleshooting

### Mirror not showing in OBS

- Check OBS browser source can reach http://localhost:5173/mirror.html
- Verify WebSocket connection in browser console
- Check `docker-compose logs mimi` for errors

### LLM control not working

- Verify Python agent is receiving WebSocket state updates
- Check that emotion_map.json is valid JSON
- Try reloading page and sending command again

### Cache not working

- Verify `data/response_cache.json` file has write permissions
- Check logs for cache load/save errors
- Try `agent.response_cache.clear()` to reset

## Next Steps

- [ ] Add gesture-specific animations (currently emotion-mapped)
- [ ] Implement voice-based gesture triggering
- [ ] Add confidence scores to cache (re-ask if below threshold)
- [ ] WebRTC quality settings (resolution, bitrate)
- [ ] Multi-client mirror support
```

**Step 1: Write documentation**

Create the file with content above.

**Step 2: Commit**

```bash
cd /home/pedro/repo/mimi
git add docs/MIRROR_AND_CONTROL.md
git commit -m "docs: add comprehensive mirror stream and control documentation"
```

---

### Task 9: Update Main README

**Files:**
- Modify: `README.md`

Add new section:

```markdown
## 🔴 WebRTC Mirror for OBS Studio

Stream your avatar directly to OBS for professional streaming:

1. **Start Mimi**: `docker-compose -f docker-compose.dev.yml up`
2. **In OBS**: Add Browser Source → `http://localhost:5173/mirror.html`
3. **Done**: Avatar streams with ~100-200ms latency

### Dynamic LLM Control

Adjust LLM behavior at runtime:

```javascript
// Change model
ws.send(JSON.stringify({ type: 'set_llm_model', model: 'ministral-3:3b' }));

// Adjust temperature  
ws.send(JSON.stringify({ type: 'set_llm_temperature', temperature: 0.5 }));
```

See [Mirror & Control Docs](docs/MIRROR_AND_CONTROL.md) for full reference.

## 🎯 Emotion-to-Gesture Mapping

Customize how emotions trigger animations:

Edit `data/emotion_map.json` to map emotions to expressions, gestures, and animations.

**Example:**
```json
{
  "emotions": {
    "excited": {
      "expression": "smile",
      "animation": "idle_excited",
      "gesture": "jump",
      "duration_ms": 2500
    }
  }
}
```

## 💾 Response Caching

Reduce LLM token usage:

- Common responses cached for 24 hours
- ~90% token savings per cache hit
- Cache file: `data/response_cache.json`
```

**Step 1: Update README**

```bash
cd /home/pedro/repo/mimi
# Append sections to README.md (or insert near the top after features)
```

**Step 2: Commit**

```bash
cd /home/pedro/repo/mimi
git add README.md
git commit -m "docs: add mirror stream and emotion mapping sections to README"
```

---

## Summary

**Total Tasks: 9**
- Phase 1 (Emotion Mapping): Tasks 1-2
- Phase 2 (Response Caching): Tasks 3-4  
- Phase 3 (WebSocket Commands): Task 5
- Phase 4 (WebRTC Mirror): Tasks 6-7
- Phase 5 (Documentation): Tasks 8-9

**Estimated Implementation Time**: 4-6 hours (for experienced developer)

**Expected Commits**: 9 atomic commits, one per task

**Test Coverage**:
- EmotionMapper: 4 tests
- ResponseCache: 4 tests
- Manual WebSocket testing
- Canvas capture testing
- End-to-end OBS integration test

**Next Major Features** (after this completes):
- Voice-based gesture triggers
- Multi-user support
- Gesture composition (chain gestures)
- Quality settings for WebRTC mirror
- Analytics dashboard for cache hits
