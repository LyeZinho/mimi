# Browser Control + Debug Panel Design

**Date:** 2026-03-27  
**Status:** Approved

---

## 1. Overview

**Objective:** Allow Mimi agent to autonomously operate a Chrome browser for web research and tasks, with an improved debug panel for monitoring.

**Architecture (4 phases):**

```
┌─────────────┐     WebSocket      ┌─────────────────┐     CDP      ┌──────────┐
│  Agente     │ ◄────────────────► │  Node.js Server │ ◄──────────► │  Chrome  │
│  Python     │                    │  + Puppeteer   │              │  (clean) │
└─────────────┘                    └─────────────────┘              └──────────┘
       │                                   │
       │                                   ▼
       │                          ┌─────────────────┐
       └─────────────────────────►│  React Frontend │
                                  │  Debug Panel    │
                                  │  + BrowserPanel │
                                  └─────────────────┘
```

---

## 2. Phase 1 - Enhanced Debug Panel (MVP - 1 week)

### New Components

| Component | Description |
|-----------|-------------|
| `ModelStatusCard` | LLM model status (emotion, tokens, latency) |
| `FilterBar` | Filters by status (active/idle/error) + text filter |
| `LatencyChart` | Latency history (last 100 samples) |
| `SummaryStats` | Active count, avg latency, total tokens |

### Data Flow

```
WebSocket message (agent_status) 
  → DebugPanel component 
  → State update 
  → Render metrics
```

---

## 3. Phase 2 - Browser Control Layer (1 week)

### New WebSocket Message Types

| Type | Direction | Payload |
|------|-----------|---------|
| `browser_command` | Python → Node | `{ action: "navigate", url: "..." }` |
| `browser_command_result` | Node → Python | `{ success: true, data: "..." }` |
| `browser_action` | Node → Frontend | `{ type: "screenshot", data: "base64" }` |

### BrowserController API (Node.js)

```javascript
class BrowserController {
  async navigate(url)        // open URL
  async click(selector)       // click element
  async type(selector, text) // type text
  async screenshot()         // capture screen
  async executeScript(code)  // execute JS
  async wait(ms)             // wait
  async extractText()        // extract page text
  async goBack()             // navigate back
  async goForward()          // navigate forward
}
```

### Chrome Launch Config

```javascript
const chromeLauncher = puppeteer.launch({
  headless: false,  // User wants to see the browser
  args: [
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--user-data-dir=/tmp/mimi-chrome-profile',  // empty profile
    '--disable-dev-shm-usage'
  ]
});
```

---

## 4. Phase 3 - BrowserBrain (Python)

### Integration in Agent

```python
class BrowserBrain:
    """Brain que decide quando usar o navegador"""
    
    async def should_browse(self, user_input: str) -> bool:
        keywords = ["pesquisar", "buscar", "procurar", "abrir", "ver", "search", "look up"]
        return any(k in user_input.lower() for k in keywords)
    
    async def plan_action(self, user_input: str) -> BrowserAction:
        # LLM decides action: navigate, click, extract text
        pass
```

### Audit Trail

```python
class BrowserCommandTracker:
    """Auditoria de comandos do browser"""
    history: list[BrowserCommand]  # command, timestamp, result
```

---

## 5. Phase 4 - Real-Time Dashboard (1 week)

### BrowserPanel Components

| Component | Description |
|-----------|-------------|
| `BrowserStatus` | Connected/disconnected indicator |
| `ScreenshotCarousel` | Last 10 screenshots |
| `CommandHistory` | Commands with duration and result |
| `LivePreview` | Real-time visualization |

---

## 6. Security

| Measure | Implementation |
|---------|---------------|
| Message validation | JSON Schema for all messages |
| Command history | BrowserCommandTracker for audit |
| Memory limits | Screenshot cache (max 10, max 2MB each) |
| Timeout enforcement | 30s default, configurable |
| Clean browser | Chrome flags: `--no-sandbox`, empty profile |
| Domain allowlist | Optional: whitelist of allowed domains |

---

## 7. Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Chrome won't open | Clear error fallback in frontend |
| Page doesn't load | Timeout + automatic retry |
| Selectors fail | Fallback by text/position |
| High memory | Screenshot limit, automatic cleanup |

---

## 8. Tech Stack

- **Frontend:** React + WebSocket (existing)
- **Browser Ctrl:** Puppeteer + Chrome DevTools Protocol
- **Backend Server:** Node.js + ws (existing)
- **Agent Backend:** Python async (existing)
- **State Mgmt:** EventEmitter (event-driven)

---

## 9. Implementation Priority

1. **Phase 1:** Debug Panel enhancements (lowest risk)
2. **Phase 2:** Browser Controller (medium risk)
3. **Phase 3:** BrowserBrain integration (highest risk)
4. **Phase 4:** Real-time dashboard (UI polish)
