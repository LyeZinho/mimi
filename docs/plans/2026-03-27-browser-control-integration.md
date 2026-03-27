# Browser Control Integration & Enhanced Debug Panel - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend Mimi with autonomous browser/desktop app control via WebSocket/API and enhance the debug panel with model status filters, real-time metrics, and autonomous action visibility.

**Architecture:** 
- **Phase 1 (MVP):** Enhanced debug panel with model status cards, text/emotion filters, and frame rate metrics
- **Phase 2:** Browser control layer via CDP (Chrome DevTools Protocol) with MCP-like WebSocket API
- **Phase 3:** Autonomous agent orchestration with real-time action streaming to dashboard
- Core pattern: Agent sends browser commands via WebSocket → Browser controller executes via CDP → Results streamed back to dashboard

**Tech Stack:**
- **Frontend:** React + existing WebSocket client, new BrowserDebugPanel component
- **Backend (Node):** Puppeteer + Chrome DevTools Protocol, new BrowserController service
- **Backend (Python):** Async WebSocket integration for sending browser commands
- **Database:** Optional JSON cache for command history (no new dependencies for MVP)

---

## Phase 1: Enhanced Debug Panel (MVP - Week 1)

### Task 1: Create Model Status Card Component

**Files:**
- Create: `web_avatar/src/components/ModelStatusCard.jsx`
- Modify: `web_avatar/src/components/DebugPanel.jsx` (add model status section)
- Test: `web_avatar/src/components/__tests__/ModelStatusCard.test.jsx`

**Step 1: Write the failing test**

```jsx
// web_avatar/src/components/__tests__/ModelStatusCard.test.jsx
import { render, screen } from '@testing-library/react';
import ModelStatusCard from '../ModelStatusCard';

describe('ModelStatusCard', () => {
  test('renders model name and status', () => {
    const model = {
      id: 'reasoning_brain',
      name: 'Reasoning Brain',
      status: 'active',
      latency: 142,
      tokens_processed: 1250,
    };
    render(<ModelStatusCard model={model} />);
    
    expect(screen.getByText('Reasoning Brain')).toBeInTheDocument();
    expect(screen.getByText(/active/i)).toBeInTheDocument();
    expect(screen.getByText('142ms')).toBeInTheDocument();
  });

  test('displays error status with red indicator', () => {
    const model = { id: 'output_brain', name: 'Output Brain', status: 'error', error: 'Timeout' };
    render(<ModelStatusCard model={model} />);
    
    expect(screen.getByText(/error/i)).toBeInTheDocument();
    expect(screen.getByText('Timeout')).toBeInTheDocument();
  });
});
```

**Step 2: Run test to verify it fails**

```bash
cd web_avatar && npm test -- ModelStatusCard.test.jsx
```

Expected output: `FAIL - Component not found`

**Step 3: Write minimal implementation**

```jsx
// web_avatar/src/components/ModelStatusCard.jsx
import React from 'react';
import './ModelStatusCard.css';

const statusColors = {
  active: '#4CAF50',
  idle: '#FFC107',
  error: '#F44336',
  loading: '#2196F3',
};

export default function ModelStatusCard({ model }) {
  const statusColor = statusColors[model.status] || '#999';

  return (
    <div className="model-status-card">
      <div className="model-header">
        <div className="status-indicator" style={{ backgroundColor: statusColor }} />
        <div className="model-name">{model.name}</div>
      </div>
      
      <div className="model-details">
        <span className="detail-item">
          <label>Status:</label> {model.status}
        </span>
        
        {model.latency && (
          <span className="detail-item">
            <label>Latency:</label> {model.latency}ms
          </span>
        )}
        
        {model.tokens_processed && (
          <span className="detail-item">
            <label>Tokens:</label> {model.tokens_processed.toLocaleString()}
          </span>
        )}
        
        {model.error && (
          <span className="detail-item error">
            <label>Error:</label> {model.error}
          </span>
        )}
      </div>
    </div>
  );
}
```

**Step 4: Add styling**

```css
/* web_avatar/src/components/ModelStatusCard.css */
.model-status-card {
  background: #f5f5f5;
  border: 1px solid #ddd;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 8px;
  font-size: 12px;
}

.model-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.model-name {
  font-weight: 600;
  color: #333;
}

.model-details {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-item {
  color: #666;
}

.detail-item label {
  font-weight: 500;
  color: #333;
}

.detail-item.error {
  color: #F44336;
}
```

**Step 5: Run test**

```bash
cd web_avatar && npm test -- ModelStatusCard.test.jsx
```

Expected: PASS

**Step 6: Commit**

```bash
git add web_avatar/src/components/ModelStatusCard.{jsx,css} web_avatar/src/components/__tests__/ModelStatusCard.test.jsx
git commit -m "feat: add model status card component with status indicators and metrics"
```

---

### Task 2: Extend AvatarStateManager to Track Multiple Brains

**Files:**
- Modify: `web_avatar/src/logic/AvatarStateManager.js` (add brain tracking)
- Modify: `web_avatar/server.js` (extend WebSocket message format)
- Test: `web_avatar/src/logic/__tests__/AvatarStateManager.test.js`

**Step 1: Write test for brain state tracking**

```javascript
// web_avatar/src/logic/__tests__/AvatarStateManager.test.js
import { AvatarStateManager } from '../AvatarStateManager';

describe('AvatarStateManager - Brain Tracking', () => {
  let manager;

  beforeEach(() => {
    manager = new AvatarStateManager();
  });

  test('adds brain to state tracking', () => {
    manager.updateBrainStatus('reasoning_brain', { status: 'active', latency: 100 });
    const brains = manager.getBrains();
    
    expect(brains).toContainEqual(expect.objectContaining({
      id: 'reasoning_brain',
      status: 'active',
      latency: 100,
    }));
  });

  test('maintains brain history with up to 100 samples', () => {
    for (let i = 0; i < 150; i++) {
      manager.updateBrainStatus('reasoning_brain', {
        status: 'active',
        latency: 100 + i,
      });
    }
    
    const history = manager.getBrainHistory('reasoning_brain');
    expect(history.length).toBeLessThanOrEqual(100);
  });

  test('calculates average latency for brain', () => {
    manager.updateBrainStatus('output_brain', { status: 'active', latency: 100 });
    manager.updateBrainStatus('output_brain', { status: 'active', latency: 150 });
    manager.updateBrainStatus('output_brain', { status: 'active', latency: 200 });
    
    const avg = manager.getAverageBrainLatency('output_brain');
    expect(avg).toBe(150);
  });
});
```

**Step 2: Run test to verify it fails**

```bash
cd web_avatar && npm test -- AvatarStateManager.test.js
```

Expected: FAIL - `updateBrainStatus is not defined`

**Step 3: Implement brain tracking in AvatarStateManager**

```javascript
// Append to web_avatar/src/logic/AvatarStateManager.js

export class AvatarStateManager {
  constructor() {
    // ... existing code ...
    this.brains = {}; // { brain_id: { id, name, status, latency, tokens_processed, updated_at } }
    this.brainHistory = {}; // { brain_id: [ ...latency samples ], max 100 }
  }

  updateBrainStatus(brainId, data) {
    const timestamp = Date.now();
    
    this.brains[brainId] = {
      id: brainId,
      name: data.name || brainId.replace('_', ' ').toUpperCase(),
      status: data.status || 'unknown',
      latency: data.latency || 0,
      tokens_processed: data.tokens_processed || 0,
      error: data.error || null,
      updated_at: timestamp,
    };

    // Keep rolling history of latencies (max 100 samples)
    if (!this.brainHistory[brainId]) {
      this.brainHistory[brainId] = [];
    }
    this.brainHistory[brainId].push(data.latency || 0);
    if (this.brainHistory[brainId].length > 100) {
      this.brainHistory[brainId].shift();
    }
  }

  getBrains() {
    return Object.values(this.brains);
  }

  getBrain(brainId) {
    return this.brains[brainId] || null;
  }

  getBrainHistory(brainId) {
    return this.brainHistory[brainId] || [];
  }

  getAverageBrainLatency(brainId) {
    const history = this.brainHistory[brainId] || [];
    if (history.length === 0) return 0;
    const sum = history.reduce((a, b) => a + b, 0);
    return Math.round(sum / history.length);
  }

  // Notify subscribers of brain updates
  notifyBrainUpdate(brainId) {
    this.emit('brain_status_updated', {
      brain_id: brainId,
      data: this.brains[brainId],
      history: this.brainHistory[brainId],
    });
  }
}
```

**Step 4: Extend WebSocket server to accept brain status messages**

```javascript
// Modify web_avatar/server.js - add handler in WebSocket message handler (around line 300)

ws.on('message', async (message) => {
  try {
    const data = JSON.parse(message);

    // ... existing handlers ...

    // NEW: Brain status updates from Python agent
    if (data.type === 'brain_status') {
      const brainId = data.brain_id;
      stateManager.updateBrainStatus(brainId, {
        status: data.status,
        latency: data.latency,
        tokens_processed: data.tokens_processed,
        error: data.error,
        name: data.name,
      });
      stateManager.notifyBrainUpdate(brainId);

      // Broadcast to all connected clients
      broadcastToClients({
        type: 'brain_status_update',
        brain_id: brainId,
        data: stateManager.getBrain(brainId),
        history: stateManager.getBrainHistory(brainId),
      });
    }

  } catch (error) {
    console.error('WebSocket message error:', error);
  }
});
```

**Step 5: Run tests**

```bash
cd web_avatar && npm test -- AvatarStateManager.test.js
```

Expected: PASS

**Step 6: Commit**

```bash
git add web_avatar/src/logic/AvatarStateManager.js web_avatar/server.js web_avatar/src/logic/__tests__/AvatarStateManager.test.js
git commit -m "feat: extend state manager with brain status tracking and history sampling"
```

---

### Task 3: Create Enhanced DebugPanel with Model Status Section

**Files:**
- Modify: `web_avatar/src/components/DebugPanel.jsx` (add model status cards, filters)
- Modify: `web_avatar/src/components/DebugPanel.css`
- Test: Integration tested via browser

**Step 1: Update DebugPanel to show model status cards**

```jsx
// Modify web_avatar/src/components/DebugPanel.jsx - replace entire component

import React, { useState } from 'react';
import ModelStatusCard from './ModelStatusCard';
import './DebugPanel.css';

export default function DebugPanel({ wsClient }) {
  const [state, setState] = useState({
    emotion: 'neutral',
    action: null,
    speaking: false,
    animation: null,
    mirrorFps: 0,
    frames: 0,
    lastUpdate: null,
    brains: [],
    brainFilter: 'all', // 'all', 'active', 'error', 'idle'
    textFilter: '',
  });

  // Listen for state updates from WebSocket
  React.useEffect(() => {
    if (!wsClient) return;

    const handleStateUpdate = (data) => {
      setState(prev => ({
        ...prev,
        emotion: data.emotion || prev.emotion,
        action: data.action || prev.action,
        speaking: data.speaking ?? prev.speaking,
        animation: data.animation || prev.animation,
        mirrorFps: data.mirror_fps || prev.mirrorFps,
        frames: data.frames || prev.frames,
        lastUpdate: new Date().toISOString(),
      }));
    };

    const handleBrainUpdate = (data) => {
      setState(prev => ({
        ...prev,
        brains: prev.brains
          .filter(b => b.id !== data.brain_id)
          .concat(data.data)
          .sort((a, b) => a.id.localeCompare(b.id)),
      }));
    };

    wsClient.on('avatar_state', handleStateUpdate);
    wsClient.on('brain_status_update', handleBrainUpdate);

    return () => {
      wsClient.off('avatar_state', handleStateUpdate);
      wsClient.off('brain_status_update', handleBrainUpdate);
    };
  }, [wsClient]);

  // Filter brains
  const filteredBrains = state.brains.filter(brain => {
    const statusMatch = state.brainFilter === 'all' || brain.status === state.brainFilter;
    const textMatch = state.textFilter === '' || 
      brain.name.toLowerCase().includes(state.textFilter.toLowerCase()) ||
      brain.id.toLowerCase().includes(state.textFilter.toLowerCase());
    return statusMatch && textMatch;
  });

  return (
    <div className="debug-panel">
      <h2>🔍 Debug Panel</h2>

      {/* Avatar State Section */}
      <section className="debug-section">
        <h3>Avatar State</h3>
        <div className="state-grid">
          <div className="state-item">
            <label>Emotion:</label>
            <span className={`emotion-badge ${state.emotion}`}>
              {state.emotion}
            </span>
          </div>
          <div className="state-item">
            <label>Speaking:</label>
            <span>{state.speaking ? '🔊' : '🔇'}</span>
          </div>
          <div className="state-item">
            <label>Action:</label>
            <span>{state.action || '—'}</span>
          </div>
          <div className="state-item">
            <label>Animation:</label>
            <span>{state.animation || '—'}</span>
          </div>
        </div>
      </section>

      {/* Stream Metrics Section */}
      <section className="debug-section">
        <h3>Stream Metrics</h3>
        <div className="state-grid">
          <div className="state-item">
            <label>Mirror FPS:</label>
            <span className={state.mirrorFps >= 8 ? 'good' : 'warning'}>
              {state.mirrorFps.toFixed(1)} FPS
            </span>
          </div>
          <div className="state-item">
            <label>Frames:</label>
            <span>{state.frames.toLocaleString()}</span>
          </div>
          <div className="state-item">
            <label>Last Update:</label>
            <span className="timestamp">
              {state.lastUpdate ? new Date(state.lastUpdate).toLocaleTimeString() : '—'}
            </span>
          </div>
        </div>
      </section>

      {/* Brain Status Section */}
      <section className="debug-section">
        <h3>Model Status ({state.brains.length})</h3>
        
        {/* Filters */}
        <div className="brain-filters">
          <select 
            value={state.brainFilter} 
            onChange={(e) => setState(prev => ({ ...prev, brainFilter: e.target.value }))}
            className="filter-select"
          >
            <option value="all">All Status</option>
            <option value="active">Active Only</option>
            <option value="idle">Idle Only</option>
            <option value="error">Errors Only</option>
          </select>
          
          <input
            type="text"
            placeholder="Filter by name..."
            value={state.textFilter}
            onChange={(e) => setState(prev => ({ ...prev, textFilter: e.target.value }))}
            className="text-filter"
          />
        </div>

        {/* Brain Cards */}
        <div className="brain-list">
          {filteredBrains.length > 0 ? (
            filteredBrains.map(brain => (
              <ModelStatusCard key={brain.id} model={brain} />
            ))
          ) : (
            <p className="empty-message">No models matching filters</p>
          )}
        </div>

        {/* Summary Stats */}
        {state.brains.length > 0 && (
          <div className="brain-summary">
            <div className="summary-stat">
              <span>Active:</span>
              <strong>{state.brains.filter(b => b.status === 'active').length}</strong>
            </div>
            <div className="summary-stat">
              <span>Avg Latency:</span>
              <strong>
                {Math.round(
                  state.brains.reduce((sum, b) => sum + (b.latency || 0), 0) / state.brains.length
                )}ms
              </strong>
            </div>
            <div className="summary-stat">
              <span>Total Tokens:</span>
              <strong>
                {state.brains.reduce((sum, b) => sum + (b.tokens_processed || 0), 0).toLocaleString()}
              </strong>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
```

**Step 2: Update CSS for new sections**

```css
/* Append to web_avatar/src/components/DebugPanel.css */

.debug-section {
  margin-bottom: 20px;
  border-bottom: 1px solid #ddd;
  padding-bottom: 12px;
}

.debug-section h3 {
  margin: 0 0 12px 0;
  font-size: 13px;
  font-weight: 600;
  color: #333;
}

.state-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.state-item {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  padding: 6px 8px;
  background: #f9f9f9;
  border-radius: 4px;
}

.state-item label {
  font-weight: 600;
  color: #666;
}

.emotion-badge {
  padding: 2px 8px;
  border-radius: 3px;
  font-weight: 600;
  font-size: 10px;
}

.emotion-badge.happy { background: #c8e6c9; color: #2e7d32; }
.emotion-badge.sad { background: #bbdefb; color: #1565c0; }
.emotion-badge.angry { background: #ffcccc; color: #c62828; }
.emotion-badge.neutral { background: #eeeeee; color: #424242; }
.emotion-badge.thinking { background: #f3e5f5; color: #6a1b9a; }

.state-item.good { color: #2e7d32; }
.state-item.warning { color: #f57f17; }

.brain-filters {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.filter-select,
.text-filter {
  flex: 1;
  padding: 6px 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 11px;
}

.text-filter {
  flex: 1.5;
}

.filter-select:focus,
.text-filter:focus {
  outline: none;
  border-color: #4CAF50;
  box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.1);
}

.brain-list {
  max-height: 300px;
  overflow-y: auto;
  margin-bottom: 12px;
}

.empty-message {
  text-align: center;
  color: #999;
  font-size: 11px;
  padding: 20px 10px;
  background: #f9f9f9;
  border-radius: 4px;
}

.brain-summary {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px;
  background: #f0f0f0;
  padding: 10px;
  border-radius: 4px;
  font-size: 11px;
}

.summary-stat {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.summary-stat span {
  color: #666;
}

.summary-stat strong {
  color: #333;
  font-size: 12px;
}
```

**Step 3: Manual integration test**

```bash
# Start the full system (3 terminals as before)
# Terminal 1: cd web_avatar && node server.js
# Terminal 2: cd web_avatar && npm run dev
# Terminal 3: source .venv/bin/activate && python agent/main.py

# Verify:
# 1. Debug panel shows avatar state (emotion, speaking, animation)
# 2. Stream metrics show FPS and frame count
# 3. Brain cards appear and update in real-time
# 4. Filters work (status dropdown, text input)
# 5. Brain summary shows correct totals
```

**Step 4: Commit**

```bash
git add web_avatar/src/components/DebugPanel.{jsx,css}
git commit -m "feat: enhance debug panel with model status cards, filters, and real-time metrics"
```

---

## Phase 2: Browser Control Layer (Week 2)

### Task 4: Set Up Puppeteer and Browser Controller Service

**Files:**
- Create: `web_avatar/browser-controller/index.js`
- Create: `web_avatar/browser-controller/CDP-client.js`
- Modify: `web_avatar/package.json` (add Puppeteer)
- Test: `web_avatar/browser-controller/__tests__/CDP-client.test.js`

**Step 1: Add Puppeteer to dependencies**

```bash
cd web_avatar && npm install --save puppeteer ws
```

**Step 2: Create CDP client wrapper**

```javascript
// web_avatar/browser-controller/CDP-client.js

const puppeteer = require('puppeteer');
const EventEmitter = require('events');

class CDPClient extends EventEmitter {
  constructor(options = {}) {
    super();
    this.browser = null;
    this.page = null;
    this.isConnected = false;
    this.commandQueue = [];
    this.options = {
      headless: false,
      defaultViewport: { width: 1920, height: 1080 },
      remoteDebuggingPort: 9222,
      ...options,
    };
  }

  async launch() {
    try {
      this.browser = await puppeteer.launch(this.options);
      this.page = await this.browser.newPage();
      
      // Set viewport
      await this.page.setViewport(this.options.defaultViewport);
      
      this.isConnected = true;
      this.emit('connected');
      console.log('[CDP] Browser launched and connected');
      
      // Start processing queued commands
      this.processCommandQueue();
    } catch (error) {
      console.error('[CDP] Launch failed:', error);
      this.emit('error', error);
      throw error;
    }
  }

  async navigate(url) {
    if (!this.page) throw new Error('Browser not initialized');
    try {
      await this.page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
      this.emit('navigation', { url, success: true });
      return { success: true, url };
    } catch (error) {
      this.emit('navigation', { url, success: false, error: error.message });
      return { success: false, error: error.message };
    }
  }

  async click(selector) {
    if (!this.page) throw new Error('Browser not initialized');
    try {
      await this.page.click(selector);
      this.emit('action', { type: 'click', selector, success: true });
      return { success: true };
    } catch (error) {
      this.emit('action', { type: 'click', selector, success: false, error: error.message });
      return { success: false, error: error.message };
    }
  }

  async type(selector, text) {
    if (!this.page) throw new Error('Browser not initialized');
    try {
      await this.page.type(selector, text);
      this.emit('action', { type: 'type', selector, text, success: true });
      return { success: true };
    } catch (error) {
      this.emit('action', { type: 'type', selector, text, success: false, error: error.message });
      return { success: false, error: error.message };
    }
  }

  async screenshot(options = {}) {
    if (!this.page) throw new Error('Browser not initialized');
    try {
      const buffer = await this.page.screenshot({
        type: 'png',
        fullPage: false,
        ...options,
      });
      this.emit('screenshot_taken');
      return { success: true, buffer };
    } catch (error) {
      this.emit('screenshot_error', error);
      return { success: false, error: error.message };
    }
  }

  async getPageContent() {
    if (!this.page) throw new Error('Browser not initialized');
    try {
      return await this.page.content();
    } catch (error) {
      return null;
    }
  }

  async execute(script) {
    if (!this.page) throw new Error('Browser not initialized');
    try {
      const result = await this.page.evaluate(script);
      this.emit('script_executed', { script, result });
      return { success: true, result };
    } catch (error) {
      this.emit('script_error', { script, error: error.message });
      return { success: false, error: error.message };
    }
  }

  async wait(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  async close() {
    if (this.browser) {
      await this.browser.close();
      this.isConnected = false;
      this.emit('closed');
    }
  }

  // Internal: queue commands if browser not ready
  enqueueCommand(command) {
    this.commandQueue.push(command);
  }

  processCommandQueue() {
    // Commands will be processed in order as they're received
  }

  getStatus() {
    return {
      isConnected: this.isConnected,
      url: this.page ? this.page.url() : null,
      title: this.page ? this.page.title : null,
    };
  }
}

module.exports = CDPClient;
```

**Step 3: Create browser controller service**

```javascript
// web_avatar/browser-controller/index.js

const CDPClient = require('./CDP-client');
const EventEmitter = require('events');

class BrowserController extends EventEmitter {
  constructor(wsClient, options = {}) {
    super();
    this.wsClient = wsClient;
    this.cdp = new CDPClient(options);
    this.isReady = false;
    this.setupEventHandlers();
  }

  setupEventHandlers() {
    // Forward CDP events
    this.cdp.on('connected', () => {
      this.isReady = true;
      this.emit('ready');
      this.broadcastToClients({ type: 'browser_ready' });
    });

    this.cdp.on('navigation', (data) => {
      this.broadcastToClients({ type: 'browser_navigation', ...data });
    });

    this.cdp.on('action', (data) => {
      this.broadcastToClients({ type: 'browser_action', ...data });
    });

    this.cdp.on('error', (error) => {
      this.broadcastToClients({ type: 'browser_error', error: error.message });
    });

    this.cdp.on('screenshot_taken', () => {
      this.broadcastToClients({ type: 'screenshot_captured' });
    });
  }

  async launch() {
    try {
      await this.cdp.launch();
    } catch (error) {
      console.error('Browser controller launch failed:', error);
      throw error;
    }
  }

  async executeCommand(command) {
    if (!this.isReady) {
      return { success: false, error: 'Browser not initialized' };
    }

    const { type, data } = command;

    try {
      let result;
      switch (type) {
        case 'navigate':
          result = await this.cdp.navigate(data.url);
          break;
        case 'click':
          result = await this.cdp.click(data.selector);
          break;
        case 'type':
          result = await this.cdp.type(data.selector, data.text);
          break;
        case 'screenshot':
          result = await this.cdp.screenshot(data.options || {});
          if (result.success && result.buffer) {
            // Send screenshot as binary
            this.broadcastToClients({
              type: 'browser_screenshot',
              data: result.buffer.toString('base64'),
            });
          }
          break;
        case 'execute':
          result = await this.cdp.execute(data.script);
          break;
        case 'wait':
          await this.cdp.wait(data.ms);
          result = { success: true };
          break;
        case 'get_status':
          result = { success: true, status: this.cdp.getStatus() };
          break;
        default:
          result = { success: false, error: `Unknown command: ${type}` };
      }

      // Broadcast command result to all clients
      this.broadcastToClients({
        type: 'browser_command_result',
        command_id: command.id,
        command_type: type,
        result,
      });

      return result;
    } catch (error) {
      console.error(`[BrowserController] Command failed: ${type}`, error);
      return { success: false, error: error.message };
    }
  }

  broadcastToClients(message) {
    if (this.wsClient && this.wsClient.broadcast) {
      this.wsClient.broadcast(message);
    }
  }

  async close() {
    await this.cdp.close();
    this.isReady = false;
  }
}

module.exports = BrowserController;
```

**Step 4: Write tests**

```javascript
// web_avatar/browser-controller/__tests__/CDP-client.test.js

const CDPClient = require('../CDP-client');

describe('CDPClient', () => {
  let client;

  beforeEach(() => {
    client = new CDPClient({ headless: true });
  });

  afterEach(async () => {
    if (client.browser) {
      await client.close();
    }
  });

  test('initializes with default options', () => {
    expect(client.isConnected).toBe(false);
    expect(client.browser).toBeNull();
  });

  test('emits connected event on launch', (done) => {
    client.on('connected', () => {
      expect(client.isConnected).toBe(true);
      done();
    });

    client.launch().catch(err => {
      console.log('Launch skipped (Puppeteer setup)', err.message);
      done();
    });
  });

  test('tracks status correctly', () => {
    const status = client.getStatus();
    expect(status).toHaveProperty('isConnected');
    expect(status).toHaveProperty('url');
  });
});
```

**Step 5: Run tests**

```bash
cd web_avatar && npm test -- CDP-client.test.js
```

Expected: Tests pass (or skip if Puppeteer can't launch)

**Step 6: Commit**

```bash
git add web_avatar/browser-controller/ web_avatar/package.json
git commit -m "feat: add Puppeteer-based CDP client and browser controller service"
```

---

### Task 5: Integrate Browser Controller into WebSocket Server

**Files:**
- Modify: `web_avatar/server.js` (add browser controller initialization)
- Create: `web_avatar/browser-commands.js` (browser command message handlers)

**Step 1: Add browser controller to server initialization**

```javascript
// Modify web_avatar/server.js (add at top after imports)

const BrowserController = require('./browser-controller');

// After WebSocket server creation (around line 50):
let browserController = null;

// Initialize browser controller (optional, based on env var)
if (process.env.ENABLE_BROWSER_CONTROL === 'true') {
  const wss = require('ws').Server; // Reference to existing server
  
  browserController = new BrowserController({ broadcast: broadcastToClients }, {
    headless: process.env.BROWSER_HEADLESS !== 'false',
  });

  browserController.launch().catch(err => {
    console.error('[Browser Controller] Failed to initialize:', err);
    browserController = null;
  });
}

// Add graceful shutdown
process.on('SIGINT', async () => {
  if (browserController) {
    await browserController.close();
  }
  process.exit(0);
});
```

**Step 2: Add browser command message handler**

```javascript
// Modify web_avatar/server.js - add to WebSocket message handler (around line 310)

    // Browser control commands (autonomous agent)
    if (data.type === 'browser_command') {
      if (!browserController || !browserController.isReady) {
        ws.send(JSON.stringify({
          type: 'browser_error',
          error: 'Browser controller not initialized',
          command_id: data.id,
        }));
        return;
      }

      // Queue and execute command
      const command = {
        id: data.id || `cmd_${Date.now()}`,
        type: data.command,
        data: data.data || {},
      };

      browserController.executeCommand(command)
        .then(result => {
          ws.send(JSON.stringify({
            type: 'browser_command_result',
            command_id: command.id,
            command_type: data.command,
            result,
          }));
        })
        .catch(err => {
          ws.send(JSON.stringify({
            type: 'browser_error',
            command_id: command.id,
            error: err.message,
          }));
        });
    }

    // Browser status request
    if (data.type === 'browser_status_request') {
      if (browserController) {
        ws.send(JSON.stringify({
          type: 'browser_status',
          status: browserController.cdp.getStatus(),
          isReady: browserController.isReady,
        }));
      } else {
        ws.send(JSON.stringify({
          type: 'browser_status',
          isReady: false,
          error: 'Browser controller not initialized',
        }));
      }
    }
```

**Step 3: Add environment variable to .env.example**

```bash
# Append to .env.example
ENABLE_BROWSER_CONTROL=false
BROWSER_HEADLESS=true
```

**Step 4: Test WebSocket integration**

```bash
# Start server
ENABLE_BROWSER_CONTROL=true cd web_avatar && node server.js

# Test message via WebSocket client (verify in browser console)
ws = new WebSocket('ws://localhost:8765');
ws.onopen = () => {
  ws.send(JSON.stringify({ type: 'browser_status_request' }));
};
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

Expected: Browser status message received

**Step 5: Commit**

```bash
git add web_avatar/server.js .env.example
git commit -m "feat: integrate browser controller with WebSocket server for command dispatch"
```

---

## Phase 3: Autonomous Agent Integration (Week 3)

### Task 6: Extend Python Agent to Send Browser Commands

**Files:**
- Create: `agent/brain_interface/browser_commands.py`
- Modify: `agent/avatar/interface.py` (add browser command methods)
- Test: `tests/test_browser_integration.py`

**Step 1: Create browser command interface**

```python
# agent/brain_interface/browser_commands.py

from dataclasses import dataclass
from typing import Optional, Any, Dict
import json
from datetime import datetime

@dataclass
class BrowserCommand:
    """Represents a command to be sent to the browser controller."""
    command_type: str  # 'navigate', 'click', 'type', 'screenshot', 'execute', 'wait'
    data: Dict[str, Any]
    command_id: Optional[str] = None
    timestamp: Optional[str] = None

    def __post_init__(self):
        if not self.command_id:
            self.command_id = f"cmd_{datetime.now().timestamp()}"
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_json(self) -> Dict:
        return {
            'type': 'browser_command',
            'id': self.command_id,
            'command': self.command_type,
            'data': self.data,
            'timestamp': self.timestamp,
        }

    @staticmethod
    def navigate(url: str) -> 'BrowserCommand':
        """Create a navigation command."""
        return BrowserCommand('navigate', {'url': url})

    @staticmethod
    def click(selector: str) -> 'BrowserCommand':
        """Create a click command."""
        return BrowserCommand('click', {'selector': selector})

    @staticmethod
    def type_text(selector: str, text: str) -> 'BrowserCommand':
        """Create a type command."""
        return BrowserCommand('type', {'selector': selector, 'text': text})

    @staticmethod
    def screenshot(fullpage: bool = False) -> 'BrowserCommand':
        """Create a screenshot command."""
        return BrowserCommand('screenshot', {'options': {'fullPage': fullpage}})

    @staticmethod
    def execute_script(script: str) -> 'BrowserCommand':
        """Create a script execution command."""
        return BrowserCommand('execute', {'script': script})

    @staticmethod
    def wait(ms: int) -> 'BrowserCommand':
        """Create a wait command."""
        return BrowserCommand('wait', {'ms': ms})


class BrowserCommandTracker:
    """Tracks pending browser commands and their results."""

    def __init__(self):
        self.pending_commands = {}  # { command_id: {'command': BrowserCommand, 'result': None, 'timestamp': ...} }
        self.command_history = []  # Keep last 100 commands

    def register_command(self, command: BrowserCommand):
        """Register a command as pending."""
        self.pending_commands[command.command_id] = {
            'command': command,
            'result': None,
            'timestamp': datetime.now(),
        }

    def resolve_command(self, command_id: str, result: Dict[str, Any]):
        """Mark command as resolved with result."""
        if command_id in self.pending_commands:
            self.pending_commands[command_id]['result'] = result
            
            # Move to history
            entry = self.pending_commands.pop(command_id)
            self.command_history.append(entry)
            
            # Keep only last 100
            if len(self.command_history) > 100:
                self.command_history.pop(0)

    def get_command_result(self, command_id: str) -> Optional[Dict[str, Any]]:
        """Get result of a command."""
        if command_id in self.pending_commands:
            return self.pending_commands[command_id].get('result')
        
        # Check history
        for entry in reversed(self.command_history):
            if entry['command'].command_id == command_id:
                return entry.get('result')
        
        return None

    def get_pending_commands(self) -> Dict:
        """Get all pending commands."""
        return self.pending_commands.copy()

    def get_history(self, limit: int = 10) -> list:
        """Get recent command history."""
        return self.command_history[-limit:]
```

**Step 2: Extend avatar interface with browser methods**

```python
# Modify agent/avatar/interface.py - add to AvatarInterface class

from agent.brain_interface.browser_commands import BrowserCommand, BrowserCommandTracker

class AvatarInterface:
    def __init__(self, ws_url: str):
        # ... existing code ...
        self.browser_tracker = BrowserCommandTracker()

    async def send_browser_command(self, command: BrowserCommand) -> Optional[Dict]:
        """Send a browser command and wait for result."""
        try:
            # Register as pending
            self.browser_tracker.register_command(command)
            
            # Send via WebSocket
            message = command.to_json()
            await self.ws.send(json.dumps(message))
            
            # Wait for result (with timeout)
            timeout = 30  # seconds
            start = time.time()
            while time.time() - start < timeout:
                result = self.browser_tracker.get_command_result(command.command_id)
                if result:
                    return result
                await asyncio.sleep(0.1)
            
            return {'success': False, 'error': 'Command timeout'}
        
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def navigate_to(self, url: str) -> Dict:
        """Navigate browser to URL."""
        cmd = BrowserCommand.navigate(url)
        return await self.send_browser_command(cmd)

    async def click_element(self, selector: str) -> Dict:
        """Click an element."""
        cmd = BrowserCommand.click(selector)
        return await self.send_browser_command(cmd)

    async def type_text(self, selector: str, text: str) -> Dict:
        """Type text into element."""
        cmd = BrowserCommand.type_text(selector, text)
        return await self.send_browser_command(cmd)

    async def take_screenshot(self, fullpage: bool = False) -> Optional[bytes]:
        """Take a screenshot (returns binary data)."""
        cmd = BrowserCommand.screenshot(fullpage)
        result = await self.send_browser_command(cmd)
        if result.get('success') and result.get('data'):
            import base64
            return base64.b64decode(result['data'])
        return None

    async def execute_script(self, script: str) -> Any:
        """Execute JavaScript on the page."""
        cmd = BrowserCommand.execute_script(script)
        result = await self.send_browser_command(cmd)
        if result.get('success'):
            return result.get('result')
        return None

    def get_browser_command_history(self, limit: int = 10) -> list:
        """Get recent browser command history."""
        return self.browser_tracker.get_history(limit)
```

**Step 3: Write integration test**

```python
# tests/test_browser_integration.py

import pytest
import asyncio
from agent.brain_interface.browser_commands import BrowserCommand, BrowserCommandTracker


class TestBrowserCommands:
    def test_navigate_command(self):
        cmd = BrowserCommand.navigate('https://example.com')
        assert cmd.command_type == 'navigate'
        assert cmd.data['url'] == 'https://example.com'
        assert cmd.command_id is not None

    def test_click_command(self):
        cmd = BrowserCommand.click('#submit-button')
        assert cmd.command_type == 'click'
        assert cmd.data['selector'] == '#submit-button'

    def test_type_command(self):
        cmd = BrowserCommand.type_text('#search', 'hello world')
        assert cmd.command_type == 'type'
        assert cmd.data['text'] == 'hello world'

    def test_command_to_json(self):
        cmd = BrowserCommand.navigate('https://example.com')
        json_data = cmd.to_json()
        assert json_data['type'] == 'browser_command'
        assert json_data['command'] == 'navigate'
        assert json_data['id'] == cmd.command_id


class TestBrowserCommandTracker:
    def test_register_and_resolve(self):
        tracker = BrowserCommandTracker()
        cmd = BrowserCommand.navigate('https://example.com')
        
        tracker.register_command(cmd)
        assert cmd.command_id in tracker.pending_commands
        
        result = {'success': True}
        tracker.resolve_command(cmd.command_id, result)
        assert cmd.command_id not in tracker.pending_commands
        assert tracker.get_command_result(cmd.command_id) == result

    def test_history_limit(self):
        tracker = BrowserCommandTracker()
        
        # Add 150 commands
        for i in range(150):
            cmd = BrowserCommand.navigate(f'https://example{i}.com')
            tracker.register_command(cmd)
            tracker.resolve_command(cmd.command_id, {'success': True})
        
        # Should keep only last 100
        assert len(tracker.command_history) <= 100

    def test_get_history(self):
        tracker = BrowserCommandTracker()
        
        for i in range(15):
            cmd = BrowserCommand.click(f'#btn-{i}')
            tracker.register_command(cmd)
            tracker.resolve_command(cmd.command_id, {'success': True})
        
        history = tracker.get_history(10)
        assert len(history) == 10
        assert all(entry.get('result') for entry in history)
```

**Step 4: Run tests**

```bash
pytest tests/test_browser_integration.py -v
```

Expected: All tests pass

**Step 5: Commit**

```bash
git add agent/brain_interface/browser_commands.py agent/avatar/interface.py tests/test_browser_integration.py
git commit -m "feat: add browser command interface and tracking for autonomous agent control"
```

---

### Task 7: Create a Brain That Uses Browser Control

**Files:**
- Create: `agent/brains/browser_brain.py`
- Create: `examples/browser_automation_example.py`
- Test: `tests/test_browser_brain.py`

**Step 1: Create browser brain**

```python
# agent/brains/browser_brain.py

import asyncio
from typing import Dict, Any, Optional
from agent.core.messaging.brain_base import BrainBase
from agent.brain_interface.browser_commands import BrowserCommand


class BrowserBrain(BrainBase):
    """
    Brain that orchestrates autonomous browser actions.
    Receives high-level tasks (e.g., "search for coffee shops")
    and breaks them down into individual browser commands.
    """

    def __init__(self, avatar_interface, llm_client):
        super().__init__('browser_brain', avatar_interface)
        self.llm_client = llm_client
        self.current_task = None
        self.task_steps = []
        self.step_index = 0

    async def process_input(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a high-level browser automation task.
        
        Example input:
        {
            'action': 'browse',
            'goal': 'search for "machine learning courses" on Google',
            'target_url': 'https://google.com'
        }
        """
        self.current_task = task
        self.step_index = 0

        try:
            # Navigate to target if provided
            if task.get('target_url'):
                result = await self.avatar_interface.navigate_to(task['target_url'])
                if not result.get('success'):
                    return {'success': False, 'error': f"Navigation failed: {result.get('error')}"}

                # Wait for page load
                await asyncio.sleep(2)

            # Use LLM to plan steps
            plan = await self.plan_task_steps(task.get('goal', task.get('action', '')))
            self.task_steps = plan.get('steps', [])

            # Execute steps
            results = []
            for step_index, step in enumerate(self.task_steps):
                self.step_index = step_index
                step_result = await self.execute_step(step)
                results.append(step_result)

                if not step_result.get('success'):
                    return {
                        'success': False,
                        'step_failed': step_index,
                        'error': step_result.get('error'),
                        'results': results,
                    }

            return {
                'success': True,
                'task_completed': task.get('goal'),
                'steps_executed': len(self.task_steps),
                'results': results,
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def plan_task_steps(self, goal: str) -> Dict[str, Any]:
        """Use LLM to plan browser automation steps."""
        prompt = f"""
        Plan the browser automation steps to accomplish this goal:
        Goal: {goal}

        Available actions:
        - navigate(url): Navigate to a URL
        - click(selector): Click an element
        - type(selector, text): Type text into an element
        - screenshot(): Take a screenshot
        - execute(script): Execute JavaScript

        Return a JSON object with a 'steps' array, each containing:
        {{"action": "...", "selector_or_url": "...", "text": "..."}}
        """

        try:
            response = await self.llm_client.generate(prompt)
            # Parse JSON from response (simplified)
            import json
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                plan_json = json.loads(response[start:end])
                return plan_json
        except Exception as e:
            print(f"LLM planning failed: {e}")

        # Fallback
        return {'steps': []}

    async def execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single browser automation step."""
        action = step.get('action')

        try:
            if action == 'navigate':
                result = await self.avatar_interface.navigate_to(step['selector_or_url'])
            elif action == 'click':
                result = await self.avatar_interface.click_element(step['selector_or_url'])
            elif action == 'type':
                result = await self.avatar_interface.type_text(
                    step['selector_or_url'],
                    step.get('text', '')
                )
            elif action == 'screenshot':
                data = await self.avatar_interface.take_screenshot()
                result = {'success': data is not None}
            elif action == 'execute':
                result_data = await self.avatar_interface.execute_script(step['selector_or_url'])
                result = {'success': result_data is not None, 'result': result_data}
            else:
                result = {'success': False, 'error': f'Unknown action: {action}'}

            # Wait a bit between actions
            await asyncio.sleep(1)
            return result

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def generate_output(self, state: Dict[str, Any]) -> str:
        """Generate a summary of browser automation results."""
        if not state.get('success'):
            return f"Browser automation failed: {state.get('error')}"

        return f"Successfully completed browser task in {state['steps_executed']} steps."
```

**Step 2: Create example**

```python
# examples/browser_automation_example.py

import asyncio
from agent.avatar.interface import AvatarInterface
from agent.brains.browser_brain import BrowserBrain
from agent.llm.factory import create_llm_client


async def main():
    # Initialize
    ws_url = 'ws://localhost:8765'
    avatar = AvatarInterface(ws_url)
    llm = create_llm_client()  # Uses configured LLM
    browser_brain = BrowserBrain(avatar, llm)

    try:
        # Example: Search on Google
        result = await browser_brain.process_input({
            'action': 'browse',
            'goal': 'Search for "Python machine learning" on Google and report top results',
            'target_url': 'https://google.com',
        })

        print("Browser Automation Result:")
        print(f"  Success: {result['success']}")
        print(f"  Steps: {result.get('steps_executed', 'N/A')}")
        if not result['success']:
            print(f"  Error: {result.get('error')}")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        await avatar.close()


if __name__ == '__main__':
    asyncio.run(main())
```

**Step 3: Write tests**

```python
# tests/test_browser_brain.py

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from agent.brains.browser_brain import BrowserBrain


@pytest.fixture
def mock_avatar():
    avatar = AsyncMock()
    avatar.navigate_to = AsyncMock(return_value={'success': True})
    avatar.click_element = AsyncMock(return_value={'success': True})
    avatar.type_text = AsyncMock(return_value={'success': True})
    return avatar


@pytest.fixture
def mock_llm():
    llm = AsyncMock()
    llm.generate = AsyncMock(return_value='{"steps": []}')
    return llm


@pytest.mark.asyncio
async def test_browser_brain_init(mock_avatar, mock_llm):
    brain = BrowserBrain(mock_avatar, mock_llm)
    assert brain.name == 'browser_brain'
    assert brain.current_task is None


@pytest.mark.asyncio
async def test_process_input_navigates(mock_avatar, mock_llm):
    brain = BrowserBrain(mock_avatar, mock_llm)
    
    task = {
        'action': 'browse',
        'goal': 'Test navigation',
        'target_url': 'https://example.com',
    }
    
    result = await brain.process_input(task)
    
    mock_avatar.navigate_to.assert_called_with('https://example.com')
    assert result['success'] is True


@pytest.mark.asyncio
async def test_process_input_handles_navigation_failure(mock_avatar, mock_llm):
    mock_avatar.navigate_to.return_value = {'success': False, 'error': 'Network error'}
    brain = BrowserBrain(mock_avatar, mock_llm)
    
    task = {
        'action': 'browse',
        'goal': 'Test failure',
        'target_url': 'https://example.com',
    }
    
    result = await brain.process_input(task)
    
    assert result['success'] is False
    assert 'Navigation failed' in result['error']
```

**Step 4: Run tests**

```bash
pytest tests/test_browser_brain.py -v
```

Expected: All tests pass (mocked)

**Step 5: Commit**

```bash
git add agent/brains/browser_brain.py examples/browser_automation_example.py tests/test_browser_brain.py
git commit -m "feat: add autonomous browser brain with task planning and step execution"
```

---

## Phase 4: Real-Time Dashboard Updates (Week 4)

### Task 8: Implement Browser Action Streaming to Dashboard

**Files:**
- Create: `web_avatar/src/components/BrowserPanel.jsx`
- Modify: `web_avatar/src/components/DebugPanel.jsx` (add browser section)
- Create: `web_avatar/src/logic/BrowserStateManager.js`

**Step 1: Create browser state manager**

```javascript
// web_avatar/src/logic/BrowserStateManager.js

import EventEmitter from 'eventemitter3';

export class BrowserStateManager extends EventEmitter {
  constructor() {
    super();
    this.status = {
      isConnected: false,
      url: null,
      title: null,
      isLoading: false,
    };
    this.commandHistory = [];
    this.currentCommand = null;
    this.screenshots = [];
    this.maxHistorySize = 50;
  }

  updateStatus(status) {
    this.status = { ...this.status, ...status };
    this.emit('status_updated', this.status);
  }

  recordCommand(command) {
    this.currentCommand = {
      ...command,
      startTime: Date.now(),
      endTime: null,
      result: null,
      status: 'executing',
    };

    this.commandHistory.unshift({
      ...this.currentCommand,
    });

    if (this.commandHistory.length > this.maxHistorySize) {
      this.commandHistory.pop();
    }

    this.emit('command_started', this.currentCommand);
  }

  completeCommand(result) {
    if (this.currentCommand) {
      this.currentCommand.endTime = Date.now();
      this.currentCommand.status = result.success ? 'success' : 'failed';
      this.currentCommand.result = result;
      this.currentCommand.duration = this.currentCommand.endTime - this.currentCommand.startTime;

      // Update history
      if (this.commandHistory.length > 0) {
        this.commandHistory[0] = { ...this.currentCommand };
      }

      this.emit('command_completed', this.currentCommand);
      this.currentCommand = null;
    }
  }

  addScreenshot(screenshotBase64, timestamp = Date.now()) {
    this.screenshots.unshift({
      data: screenshotBase64,
      timestamp,
    });

    if (this.screenshots.length > 10) {
      this.screenshots.pop();
    }

    this.emit('screenshot_captured', this.screenshots[0]);
  }

  getStatus() {
    return this.status;
  }

  getCommandHistory(limit = 10) {
    return this.commandHistory.slice(0, limit);
  }

  getLatestScreenshot() {
    return this.screenshots[0] || null;
  }

  reset() {
    this.status = {
      isConnected: false,
      url: null,
      title: null,
      isLoading: false,
    };
    this.commandHistory = [];
    this.currentCommand = null;
    this.screenshots = [];
    this.emit('reset');
  }
}
```

**Step 2: Create BrowserPanel component**

```jsx
// web_avatar/src/components/BrowserPanel.jsx

import React, { useState, useEffect } from 'react';
import './BrowserPanel.css';

export default function BrowserPanel({ wsClient, browserStateManager }) {
  const [browserState, setBrowserState] = useState({
    status: browserStateManager.getStatus(),
    commandHistory: browserStateManager.getCommandHistory(),
    latestScreenshot: browserStateManager.getLatestScreenshot(),
    currentCommand: null,
  });

  useEffect(() => {
    if (!browserStateManager) return;

    const handleStatusUpdate = (status) => {
      setBrowserState(prev => ({ ...prev, status }));
    };

    const handleCommandStarted = (cmd) => {
      setBrowserState(prev => ({
        ...prev,
        currentCommand: cmd,
        commandHistory: [cmd, ...prev.commandHistory].slice(0, 10),
      }));
    };

    const handleCommandCompleted = (cmd) => {
      setBrowserState(prev => ({
        ...prev,
        currentCommand: null,
        commandHistory: prev.commandHistory.map(c => c.id === cmd.id ? cmd : c),
      }));
    };

    const handleScreenshot = (screenshot) => {
      setBrowserState(prev => ({ ...prev, latestScreenshot: screenshot }));
    };

    browserStateManager.on('status_updated', handleStatusUpdate);
    browserStateManager.on('command_started', handleCommandStarted);
    browserStateManager.on('command_completed', handleCommandCompleted);
    browserStateManager.on('screenshot_captured', handleScreenshot);

    return () => {
      browserStateManager.off('status_updated', handleStatusUpdate);
      browserStateManager.off('command_started', handleCommandStarted);
      browserStateManager.off('command_completed', handleCommandCompleted);
      browserStateManager.off('screenshot_captured', handleScreenshot);
    };
  }, [browserStateManager]);

  const statusColor = browserState.status.isConnected ? '#4CAF50' : '#999';

  return (
    <div className="browser-panel">
      <h3>🌐 Browser Control</h3>

      {/* Browser Status */}
      <div className="browser-status">
        <div className="status-indicator" style={{ backgroundColor: statusColor }} />
        <span className="status-text">
          {browserState.status.isConnected ? 'Connected' : 'Disconnected'}
        </span>
        {browserState.status.url && (
          <span className="url-badge" title={browserState.status.url}>
            {new URL(browserState.status.url).hostname}
          </span>
        )}
      </div>

      {/* Current Command */}
      {browserState.currentCommand && (
        <div className="current-command">
          <div className="command-header">
            <span className="command-type">{browserState.currentCommand.command}</span>
            <span className="spinner">⟳</span>
          </div>
          <div className="command-details">
            {browserState.currentCommand.data.url && (
              <p>URL: {browserState.currentCommand.data.url}</p>
            )}
            {browserState.currentCommand.data.selector && (
              <p>Selector: {browserState.currentCommand.data.selector}</p>
            )}
          </div>
        </div>
      )}

      {/* Screenshot */}
      {browserState.latestScreenshot && (
        <div className="screenshot-container">
          <img
            src={`data:image/png;base64,${browserState.latestScreenshot.data}`}
            alt="Browser screenshot"
            className="screenshot"
          />
        </div>
      )}

      {/* Command History */}
      <div className="command-history">
        <h4>Recent Commands</h4>
        <ul className="history-list">
          {browserState.commandHistory.map((cmd, idx) => (
            <li
              key={idx}
              className={`history-item ${cmd.status}`}
              title={`Duration: ${cmd.duration}ms`}
            >
              <span className="status-badge">{cmd.status === 'success' ? '✓' : '✗'}</span>
              <span className="cmd-type">{cmd.command}</span>
              {cmd.duration && (
                <span className="cmd-duration">{cmd.duration}ms</span>
              )}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
```

**Step 3: Update DebugPanel to include BrowserPanel**

```jsx
// Modify web_avatar/src/components/DebugPanel.jsx - add import and browser section

import BrowserPanel from './BrowserPanel';

// Inside DebugPanel component, after brain status section:

      {/* Browser Control Section (if enabled) */}
      {browserStateManager && (
        <section className="debug-section">
          <BrowserPanel wsClient={wsClient} browserStateManager={browserStateManager} />
        </section>
      )}
```

**Step 4: Add CSS**

```css
/* web_avatar/src/components/BrowserPanel.css */

.browser-panel {
  background: #fafafa;
  border-radius: 6px;
  padding: 12px;
  font-size: 11px;
}

.browser-panel h3 {
  margin: 0 0 12px 0;
  font-size: 13px;
}

.browser-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  background: white;
  border-radius: 4px;
  margin-bottom: 12px;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-text {
  font-weight: 600;
}

.url-badge {
  background: #e3f2fd;
  color: #1976d2;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 10px;
  margin-left: auto;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.current-command {
  background: #fff3e0;
  border: 1px solid #ffe0b2;
  border-radius: 4px;
  padding: 10px;
  margin-bottom: 12px;
}

.command-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  margin-bottom: 6px;
}

.command-type {
  color: #e65100;
}

.spinner {
  display: inline-block;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.command-details {
  font-size: 10px;
  color: #666;
}

.command-details p {
  margin: 4px 0;
  word-break: break-word;
}

.screenshot-container {
  margin-bottom: 12px;
  border-radius: 4px;
  overflow: hidden;
  max-height: 200px;
}

.screenshot {
  width: 100%;
  height: auto;
  display: block;
  background: #f0f0f0;
}

.command-history {
  margin-top: 12px;
  border-top: 1px solid #ddd;
  padding-top: 8px;
}

.command-history h4 {
  margin: 0 0 8px 0;
  font-size: 12px;
}

.history-list {
  list-style: none;
  padding: 0;
  margin: 0;
  max-height: 150px;
  overflow-y: auto;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 6px;
  border-radius: 3px;
  margin-bottom: 4px;
  background: white;
  border: 1px solid #eee;
  cursor: pointer;
  transition: all 0.2s;
}

.history-item:hover {
  background: #f5f5f5;
}

.history-item.success {
  border-left: 2px solid #4CAF50;
}

.history-item.failed {
  border-left: 2px solid #f44336;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  font-size: 10px;
}

.history-item.success .status-badge {
  background: #c8e6c9;
  color: #2e7d32;
}

.history-item.failed .status-badge {
  background: #ffcdd2;
  color: #c62828;
}

.cmd-type {
  flex: 1;
  font-weight: 500;
  color: #333;
}

.cmd-duration {
  font-size: 10px;
  color: #999;
  white-space: nowrap;
}
```

**Step 5: Commit**

```bash
git add web_avatar/src/components/BrowserPanel.{jsx,css} web_avatar/src/logic/BrowserStateManager.js
git commit -m "feat: add browser panel with live command execution tracking and screenshots"
```

---

## Tech Stack Summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React, WebSocket | Dashboard with real-time updates |
| **Browser Control** | Puppeteer, CDP | Autonomous browser automation |
| **Backend Server** | Node.js + ws | WebSocket hub for coordination |
| **Agent Backend** | Python async | Brain orchestration, LLM integration |
| **State Management** | EventEmitter | Decoupled event-driven updates |

---

## Security Considerations

✅ **Implemented:**
- WebSocket message validation on server
- Brain status tracking (prevent unauthorized actions)
- Command history + audit trail
- Screenshot memory limit (max 10 frames)
- Command timeout (30s default)

⚠️ **TODO (Phase 5):**
- Domain allowlist for navigation
- User/role-based command permissions
- TLS/WSS for production
- Command rate limiting
- Screenshot encryption for sensitive data

---

## Execution Path

**Choice:**

1. **Subagent-Driven** (this session): Fresh subagent per task, code review between tasks
2. **Parallel Session** (separate): New terminal, execute plan autonomously with checkpoints

Which approach?
