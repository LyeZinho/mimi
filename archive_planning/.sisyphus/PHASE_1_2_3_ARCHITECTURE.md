# 🎯 Fases 1-3: Enhanced Debug Panel → Browser Control → Autonomous Agent

**Status**: ANALYSIS MODE COMPLETE ✅
**Data**: 2026-03-27
**Tech Stack**: React + WebSocket (frontend), Node.js (server), Python async (agent backend)

---

## 📊 FASE 1: Enhanced Debug Panel (MVP - 1 semana)

### 1.1 Objetivo
Melhorar painel de debug existente com:
- Modelo status components (emotion, latency, tokens)
- Filtros (active/idle/error) + text search
- Histórico de latência (últimas 100 amostras)
- Summary stats

### 1.2 Arquitetura
```
frontend/DebugPanel.jsx (MODIFY)
  ├── ModelMetricsCard (NEW)
  │   ├── Emotion indicator (existing)
  │   ├── Latency gauge (NEW)
  │   └── Token counter (NEW)
  ├── FilterPanel (NEW)
  │   ├── Status filter dropdown
  │   └── Text search
  ├── LatencyChart (NEW)
  │   └── 100-sample history (line chart)
  └── SummaryStats (NEW)
      ├── Active count
      ├── Avg latency
      └── Total tokens

agent/brains/output_brain.py (MODIFY)
  └── Publish METRICS event with: emotion, latency_ms, tokens_used

web_avatar/server.js (MODIFY)
  └── Broadcast metrics to all WebSocket clients
```

### 1.3 Data Flow
```
1. OutputBrain processes inference
2. Publishes METRICS event: { latency_ms, emotion, tokens_used, timestamp }
3. Orchestrator aggregates metrics
4. WebSocket sends to frontend: { type: 'metrics', data: {...} }
5. DebugPanel receives and updates (useState hooks)
6. Chart shows rolling 100-sample history
```

### 1.4 Deliverables
- `web_avatar/src/components/ModelMetricsCard.jsx` (NEW) — emotion + latency + tokens
- `web_avatar/src/components/FilterPanel.jsx` (NEW) — status/text filters
- `web_avatar/src/components/LatencyChart.jsx` (NEW) — line chart (100 samples)
- `web_avatar/src/components/SummaryStats.jsx` (NEW) — active/avg/total
- `DebugPanel.jsx` (MODIFY) — integrate new subcomponents
- Backend metrics publishing (agent-side)
- WebSocket message type: `metrics` payload

### 1.5 Key Files to Modify/Create
| File | Change | Type |
|------|--------|------|
| `web_avatar/src/components/DebugPanel.jsx` | Add subcomponents | MODIFY |
| `web_avatar/src/components/ModelMetricsCard.jsx` | NEW | CREATE |
| `web_avatar/src/components/FilterPanel.jsx` | NEW | CREATE |
| `web_avatar/src/components/LatencyChart.jsx` | NEW | CREATE |
| `web_avatar/src/components/SummaryStats.jsx` | NEW | CREATE |
| `agent/brains/output_brain.py` | Publish metrics | MODIFY |
| `web_avatar/server.js` | Forward metrics events | MODIFY |

---

## 🌐 FASE 2: Browser Control Layer (1 semana)

### 2.1 Objetivo
Camada de controle Chromium/desktop apps:
- Puppeteer + Chrome DevTools Protocol
- BrowserController service (Node.js)
- WebSocket message types: browser_command, browser_command_result, browser_action
- Suporta: navigate, click, type, screenshot, execute_script, wait

### 2.2 Arquitetura
```
web_avatar/server.js (MODIFY)
  └── BrowserController (NEW)
      ├── Initialize Puppeteer (headless/headful)
      ├── Command queue (async FIFO)
      ├── Timeout enforcement (30s default)
      ├── Screenshot cache (max 10, LRU eviction)
      └── Error recovery (reconnect on crash)

WebSocket Message Types:
  ├── browser_command: { type: 'navigate'|'click'|'type'|'screenshot'|'execute_script'|'wait', params: {...} }
  ├── browser_command_result: { command_id: str, success: bool, result: {...}, duration_ms: int }
  └── browser_action: { action: 'page_loaded'|'element_found'|'error', details: {...} }

agent/tools/browser_control.py (NEW)
  └── BrowserTool (extends BaseTool)
      ├── navigate(url)
      ├── click(selector)
      ├── type(selector, text)
      ├── screenshot()
      ├── execute_script(script)
      └── wait(selector, timeout)
```

### 2.3 Data Flow
```
1. Python agent wants to navigate
2. Sends browser_command via WebSocket: { type: 'navigate', url: 'https://...' }
3. Node.js BrowserController queues command
4. Executes via Puppeteer with 30s timeout
5. Captures screenshot (if needed)
6. Sends browser_command_result: { success: true, result: {...}, duration_ms: 245 }
7. Python agent receives and continues
```

### 2.4 Deliverables
- `web_avatar/services/BrowserController.js` (NEW) — Puppeteer wrapper
- `web_avatar/services/ScreenshotCache.js` (NEW) — LRU cache (max 10)
- `agent/tools/browser_control.py` (NEW) — Tool interface
- `agent/tools/registry.py` (MODIFY) — Register browser_control
- `web_avatar/server.js` (MODIFY) — Add browser command handlers
- WebSocket handlers for browser_command/browser_command_result/browser_action

### 2.5 Key Files to Modify/Create
| File | Change | Type |
|------|--------|------|
| `web_avatar/services/BrowserController.js` | Puppeteer controller | CREATE |
| `web_avatar/services/ScreenshotCache.js` | Screenshot LRU cache | CREATE |
| `agent/tools/browser_control.py` | Browser tool | CREATE |
| `agent/tools/registry.py` | Register browser tool | MODIFY |
| `web_avatar/server.js` | Add browser handlers | MODIFY |

---

## 🤖 FASE 3: Autonomous Agent Integration (1 semana)

### 3.1 Objetivo
Novo BrowserBrain autônomo:
- LLM-based task planning
- BrowserCommandTracker para auditoria
- Real-time browser state streaming
- Exemplo: "pesquisar X no Google"

### 3.2 Arquitetura
```
agent/brains/browser_brain.py (NEW)
  ├── Subscribe to: TOOL_STARTED, TOOL_RESULT, TOOL_ERROR
  ├── Maintain: browser_state (current_url, page_title, elements_found)
  ├── On task: generate plan (LLM prompt)
  ├── Execute commands sequentially
  ├── Publish: BROWSER_COMMAND events
  └── Publish: BROWSER_STATE_CHANGED events

BrowserCommandTracker (NEW - in shared_state)
  ├── Track all commands (audit trail)
  ├── Store: command_id, timestamp, type, params, result, duration_ms
  ├── Max 1000 commands (circular buffer)
  └── Enable replay/debugging

BrowserBrain Workflow:
  1. Agent asks: "pesquisar sobre IA no Google"
  2. BrowserBrain generates plan:
     - Navigate to google.com
     - Click search box
     - Type "IA"
     - Wait for results
     - Capture screenshot
  3. Execute commands via browser_control tool
  4. Track results in BrowserCommandTracker
  5. Publish state changes to frontend
```

### 3.3 Data Flow
```
1. ReasoningBrain detects: "pesquisar X no Google"
2. PlanningBrain creates task: { type: 'browser_search', params: { query: 'IA' } }
3. ExecutionBrain dispatches to BrowserBrain
4. BrowserBrain generates multi-step plan (LLM)
5. Execute: navigate → click → type → wait → screenshot
6. Each command: browser_command → browser_command_result
7. Track in BrowserCommandTracker
8. Publish BROWSER_STATE_CHANGED with new state
9. Frontend receives and updates BrowserPanel
```

### 3.4 Deliverables
- `agent/brains/browser_brain.py` (NEW) — Autonomous browser brain
- `agent/core/messaging/browser_tracker.py` (NEW) — Command audit trail
- `agent/core/messaging/shared_state.py` (MODIFY) — Add BrowserCommandTracker
- `agent/orchestrator.py` (MODIFY) — Add BrowserBrain to 8-brain system
- Event types: BROWSER_COMMAND, BROWSER_COMMAND_RESULT, BROWSER_STATE_CHANGED

### 3.5 Key Files to Modify/Create
| File | Change | Type |
|------|--------|------|
| `agent/brains/browser_brain.py` | Browser brain | CREATE |
| `agent/core/messaging/browser_tracker.py` | Command tracker | CREATE |
| `agent/core/messaging/shared_state.py` | Add tracker | MODIFY |
| `agent/core/messaging/event_bus.py` | Add event types | MODIFY |
| `agent/orchestrator.py` | Add browser brain | MODIFY |

---

## 🎨 FASE 4: Real-Time Dashboard Updates (1 semana)

### 4.1 Objetivo
BrowserPanel na UI:
- Histórico de comandos (últimos 50)
- Live screenshots (últimas 10)
- Status indicador (connected/disconnected)
- Command history com duração e resultado

### 4.2 Arquitetura
```
web_avatar/src/components/BrowserPanel.jsx (NEW)
  ├── BrowserStatusIndicator (NEW) — green/red/yellow
  ├── BrowserScreenshotViewer (NEW) — grid of 10 latest
  ├── CommandHistoryTable (NEW) — type/duration/result
  └── BrowserStateInfo (NEW) — current_url, page_title

Frontend Hooks:
  - useBrowserState() — subscribes to BROWSER_STATE_CHANGED
  - useBrowserScreenshots() — latest 10 screenshots
  - useBrowserCommands() — latest 50 commands
  - useBrowserStatus() — connected/disconnected
```

### 4.3 Data Flow
```
1. BrowserBrain executes commands
2. Each result: { command_id, type, duration_ms, result, screenshot }
3. WebSocket broadcasts: { type: 'browser_state', state: {...} }
4. Frontend BrowserPanel receives and updates
5. Screenshots rendered in grid (thumbnail + full-size on click)
6. Command history table shows last 50 with filters
```

### 4.4 Deliverables
- `web_avatar/src/components/BrowserPanel.jsx` (NEW)
- `web_avatar/src/components/BrowserStatusIndicator.jsx` (NEW)
- `web_avatar/src/components/BrowserScreenshotViewer.jsx` (NEW)
- `web_avatar/src/components/CommandHistoryTable.jsx` (NEW)
- `web_avatar/src/components/BrowserStateInfo.jsx` (NEW)
- WebSocket message type: `browser_state` payload

---

## 🔒 Segurança (Scope: Considerações)

| Item | Status | Notes |
|------|--------|-------|
| Message validation | ✅ TODO | Validate all browser commands (whitelist) |
| Command history | ✅ TODO | BrowserCommandTracker audit trail |
| Memory limits | ✅ TODO | Screenshot cache (max 10, LRU eviction) |
| Timeout enforcement | ✅ TODO | 30s default per command |
| Domain allowlist | ⚠️ FUTURE | Whitelist allowed domains |
| Role-based permissions | ⚠️ FUTURE | Who can trigger browser commands |
| TLS/WSS | ⚠️ FUTURE | Encrypt WebSocket (Phase 4+) |

---

## 📈 Implementation Timeline

| Phase | Duration | Start | End | Key Deliverables |
|-------|----------|-------|-----|------------------|
| **Phase 1** | 1 week | Week 1 | Week 1 | Enhanced DebugPanel components |
| **Phase 2** | 1 week | Week 2 | Week 2 | BrowserController + browser_control tool |
| **Phase 3** | 1 week | Week 3 | Week 3 | BrowserBrain autonomous + command tracker |
| **Phase 4** | 1 week | Week 4 | Week 4 | BrowserPanel UI + real-time updates |

---

## 🔧 Tech Stack Summary

| Layer | Technology | Role |
|-------|-----------|------|
| **Frontend** | React 18 + Hooks | DebugPanel, BrowserPanel components |
| **WebSocket Protocol** | JSON over WebSocket | All inter-process communication |
| **Browser Automation** | Puppeteer + CDP | Navigate, click, screenshot, etc. |
| **Node.js Backend** | WebSocket server | Message router, BrowserController |
| **Python Backend** | asyncio + event bus | Agent orchestrator, brain coordination |
| **State Management** | EventBus + SharedState | Centralized event-driven coordination |

---

## 🎯 Success Criteria

- ✅ Phase 1: DebugPanel shows live metrics (emotion, latency, tokens) with filters
- ✅ Phase 2: BrowserController executes commands reliably with < 30s timeout
- ✅ Phase 3: BrowserBrain autonomously plans and executes browser tasks
- ✅ Phase 4: BrowserPanel displays real-time state, screenshots, command history
- ✅ All: Zero browser crashes, screenshot cache stays < 50MB, command audit trail complete
- ✅ Testing: E2E test "pesquisar IA no Google" works end-to-end

---

## 📝 Notes

1. **Phase 1 is independent** — can ship before Phase 2
2. **Phase 2 is foundational** — Phase 3 depends on reliable browser_command protocol
3. **Phase 3 requires LLM-based planning** — leverage existing ReasoningBrain patterns
4. **Phase 4 is UI-only** — just rendering Phase 3's data

**Next Step**: Get approval on architecture, then start Phase 1 implementation.
