# 📋 PLANO DETALHADO: Implementação Fases 1-3 (Análise + Arquitetura)

**Status**: ANALYSIS COMPLETE (bg_e30d1df3 ainda coletando dados externos)
**Última atualização**: 2026-03-27 15:35 UTC
**Repositório**: C:\Users\Pedro Jesus\Downloads\mimi (main branch)

---

## 🎯 RESUMO EXECUTIVO

Seu objetivo é transformar o Mimi em um sistema **completamente autônomo com controle de browser**:

1. **Fase 1 (MVP)**: Melhorar painel de debug existente (emotion, latency, tokens, filtros)
2. **Fase 2**: Integrar Puppeteer para controle automático de browser
3. **Fase 3**: Criar BrowserBrain que executa tarefas de forma autônoma (ex: "pesquisar IA no Google")
4. **Fase 4**: Dashboard UI em tempo real mostrando histórico de comandos + screenshots

**Timeline**: 4 semanas (1 semana por fase)
**Complexidade**: Alta (arquitetura autônoma)
**Risco**: Médio (Puppeteer + async coordination)

---

## 📊 CONTEXTO ATUAL DO PROJETO

### Infraestrutura Existente ✅
| Componente | Status | Arquivo | Notas |
|-----------|--------|---------|-------|
| WebSocket Server (Node.js) | ✅ Ativo | `web_avatar/server.js` | Port 8765, handles avatar state |
| React Frontend | ✅ Ativo | `web_avatar/src/` | Components: AvatarCanvas, DebugPanel, ChatInterface |
| Python Orchestrator | ✅ Ativo | `agent/orchestrator.py` | 7 brains, event-driven |
| EventBus (pub/sub) | ✅ Ativo | `agent/core/messaging/event_bus.py` | Typed events, async handlers |
| SharedState | ✅ Ativo | `agent/core/messaging/shared_state.py` | Centralized state + locking |
| Tool Registry | ✅ Ativo | `agent/tools/registry.py` | 10+ tools (search, weather, etc.) |
| DebugPanel | ✅ Existe | `web_avatar/src/components/DebugPanel.jsx` | Emotion, gesture, speaking, FPS |

### WebSocket Message Types (Existentes)
```
avatar_control: { emotion, gesture, speak, animation }
chat_response: { text, intent, emotion }
mirror_frame: { base64_image, timestamp }
state: { model, expression, animation, speaking, camera, background }
POSE_PLAYBACK: { frame_id, poses }
```

### Padrões Arquiteturais
- **Frontend State**: useState hooks em componentes individuais
- **Backend State**: SharedState com async locking
- **Comunicação**: WebSocket callbacks (onMessage, onStatusChange)
- **Eventos**: EventBus com tipo Enum + handler registry
- **Brains**: Classe base Brain com initialize/process/shutdown

---

## ✅ FASE 1: Enhanced Debug Panel (1 semana)

### 1.1 Objetivos Específicos

```
HOJE (MVP atual):
- DebugPanel mostra: emotion, gesture, speaking, animation, FPS, frame count, last update
- Dados fluem via WebSocket (avatar_control messages)
- Sem filtros, sem histórico, sem métricas de latência

APÓS FASE 1:
- Mostra: emotion, latency_ms, tokens_used (modelo status)
- Com filtros: status (active/idle/error), text search
- Histórico: últimas 100 medições de latência (line chart)
- Summary: active count, avg latency, total tokens
- Dados fluem via novo WebSocket message type: 'metrics'
```

### 1.2 Componentes a Criar/Modificar

#### Components React (Frontend)

1. **`ModelMetricsCard.jsx` (NEW)**
   ```jsx
   // Exibe 3 métricas em tempo real
   export default function ModelMetricsCard({ metrics }) {
     return (
       <div>
         <div>Emotion: <span style={{color: emotionColor}}>{metrics.emotion}</span></div>
         <div>Latency: <span>{metrics.latency_ms}ms</span></div>
         <div>Tokens: <span>{metrics.tokens_used}</span></div>
       </div>
     )
   }
   
   // Props esperadas:
   // - metrics: { emotion, latency_ms, tokens_used }
   ```

2. **`FilterPanel.jsx` (NEW)**
   ```jsx
   // Filtros para métricas
   export default function FilterPanel({ onFilterChange }) {
     return (
       <div>
         <select onChange={(e) => onFilterChange('status', e.target.value)}>
           <option value="all">All</option>
           <option value="active">Active</option>
           <option value="idle">Idle</option>
           <option value="error">Error</option>
         </select>
         
         <input type="text" placeholder="Search..." 
           onChange={(e) => onFilterChange('text', e.target.value)} />
       </div>
     )
   }
   ```

3. **`LatencyChart.jsx` (NEW)**
   ```jsx
   // Line chart com últimas 100 amostras
   import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts'
   
   export default function LatencyChart({ samples }) {
     // samples = [{ timestamp, latency_ms }, ...]
     return <LineChart data={samples} width={400} height={200}>...</LineChart>
   }
   ```

4. **`SummaryStats.jsx` (NEW)**
   ```jsx
   // Resumo de métricas
   export default function SummaryStats({ stats }) {
     return (
       <div>
         <div>Active: {stats.active_count}</div>
         <div>Avg Latency: {stats.avg_latency_ms}ms</div>
         <div>Total Tokens: {stats.total_tokens}</div>
       </div>
     )
   }
   ```

5. **`DebugPanel.jsx` (MODIFY)**
   ```jsx
   // Integrar 4 novos componentes
   export default function DebugPanel({ wsClient }) {
     const [metrics, setMetrics] = useState(null)
     const [latencySamples, setLatencySamples] = useState([])
     const [filters, setFilters] = useState({ status: 'all', text: '' })
     
     useEffect(() => {
       // Subscribe to 'metrics' message type
       wsClient.onMessage((msg) => {
         if (msg.type === 'metrics') {
           // Update metrics + latency samples
         }
       })
     }, [wsClient])
     
     return (
       <div>
         <ModelMetricsCard metrics={metrics} />
         <FilterPanel onFilterChange={setFilters} />
         <LatencyChart samples={latencySamples} />
         <SummaryStats stats={computeStats(latencySamples)} />
       </div>
     )
   }
   ```

#### Backend (Python) - Publishing Metrics

1. **`agent/brains/output_brain.py` (MODIFY)**
   ```python
   # After inference, publish metrics
   async def process(self):
       # ... existing code ...
       
       # NOVO: Publish metrics event
       await self.publish_event(EventType.METRICS, {
           'emotion': current_emotion,
           'latency_ms': inference_time_ms,
           'tokens_used': token_count,
           'timestamp': time.time()
       })
   ```

2. **`agent/core/messaging/event_bus.py` (MODIFY)**
   ```python
   class EventType(str, Enum):
       # ... existing types ...
       METRICS = "metrics"  # NOVO
   ```

#### Node.js Server - Forwarding Metrics

1. **`web_avatar/server.js` (MODIFY)**
   ```javascript
   // In the WebSocket message handler:
   ws.on('message', (msg) => {
       const parsed = JSON.parse(msg)
       
       if (parsed.type === 'metrics') {
           // Broadcast to all connected clients
           broadcastMetrics(parsed.data)
       }
   })
   
   function broadcastMetrics(data) {
       wss.clients.forEach((client) => {
           if (client.readyState === WebSocket.OPEN) {
               client.send(JSON.stringify({
                   type: 'metrics',
                   data: data
               }))
           }
       })
   }
   ```

### 1.3 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ Agent Backend (Python)                                      │
│                                                             │
│  OutputBrain (inference complete)                           │
│    ├── latency_ms = 245                                     │
│    ├── tokens_used = 156                                    │
│    ├── emotion = 'happy'                                    │
│    └── publish_event(METRICS, {...})                        │
│                                                             │
└─────────────────────────┬───────────────────────────────────┘
                          │ AgentEvent
                          │ type=METRICS
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ EventBus (pub/sub)                                          │
│  - Publishes METRICS event to all subscribers               │
│  - Includes timestamp, emotion, latency, tokens             │
└─────────────────────────┬───────────────────────────────────┘
                          │ (Python → Node.js via WebSocket)
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Node.js Server (web_avatar/server.js)                       │
│  - Receives metrics via Python WebSocket connection         │
│  - Broadcasts to all connected React clients:              │
│    { type: 'metrics', data: { emotion, latency_ms, ... } } │
└─────────────────────────┬───────────────────────────────────┘
                          │ JSON via WebSocket
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ React Frontend                                              │
│                                                             │
│  DebugPanel.jsx                                             │
│    ├── ModelMetricsCard (displays emotion, latency, tokens) │
│    ├── FilterPanel (status + text filters)                  │
│    ├── LatencyChart (line chart, 100 samples)               │
│    └── SummaryStats (active count, avg latency, total)      │
│                                                             │
│  State:                                                     │
│    - metrics = { emotion, latency_ms, tokens_used }         │
│    - latencySamples = [100 most recent]                    │
│    - filters = { status, text }                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.4 Checklist de Implementação

**Backend (Python)**
- [ ] Adicionar `EventType.METRICS` em `event_bus.py`
- [ ] Modificar `output_brain.py` para publicar metrics após cada inference
- [ ] Métricas incluem: emotion, latency_ms, tokens_used, timestamp
- [ ] Testar: publicação de eventos funciona corretamente

**Node.js Server**
- [ ] Adicionar handler para tipo 'metrics' em `server.js`
- [ ] Implementar `broadcastMetrics()` função
- [ ] Testar: métricas chegam nos clientes React

**Frontend (React)**
- [ ] Criar `ModelMetricsCard.jsx` (exibe 3 métricas)
- [ ] Criar `FilterPanel.jsx` (status + text filter)
- [ ] Criar `LatencyChart.jsx` (line chart com recharts)
- [ ] Criar `SummaryStats.jsx` (active count, avg latency, total tokens)
- [ ] Modificar `DebugPanel.jsx` para integrar 4 componentes
- [ ] Implementar useState para guardar últimas 100 amostras de latência
- [ ] Testar: métricas aparecem no painel, filtros funcionam

**Testing**
- [ ] E2E: Inference → Métrica publicada → Frontend recebe → UI atualiza
- [ ] Verificar latency chart mostra últimas 100 amostras
- [ ] Verificar filtros funcionam (status=active/idle/error)
- [ ] Verificar text search filtra métricas

### 1.5 Estimativa de Esforço

| Task | Tempo |
|------|-------|
| Backend (metrics publishing) | 2-3h |
| Node.js server integration | 1-2h |
| React components (4 novos) | 3-4h |
| Integration testing | 2-3h |
| **Total Fase 1** | **8-12h** |

---

## 🌐 FASE 2: Browser Control Layer (1 semana)

### 2.1 Objetivos Específicos

```
NOVO - Browser Automation Service:
- Puppeteer + Chrome DevTools Protocol
- BrowserController service em Node.js
- Comandos: navigate, click, type, screenshot, execute_script, wait
- Timeout enforcement (30s default)
- Screenshot caching (max 10, LRU eviction)
- Error recovery + reconnection
```

### 2.2 Arquitetura High-Level

```
Python Agent                      Node.js Server              Browser (Chromium)
    │                                  │                           │
    │  browser_command                │                           │
    │  (WebSocket JSON)               │                           │
    ├─────────────────────────────────>                           │
    │                          BrowserController                 │
    │                            (service)                        │
    │                                  ├──► Puppeteer             │
    │                                  │        ├──► navigate     │
    │                                  │        ├──► click        │
    │                                  │        ├──► type         │
    │                                  │        ├──► screenshot   │
    │                                  │        └──► execute_script
    │                                  │                           │
    │         browser_command_result   │                           │
    │         (success/error/screenshot) <────────────────────────┤
    │  <────────────────────────────────────                       │
    │                                                              │
    └─► agent/tools/browser_control.py (Tool wrapper)
        └─► calls BrowserController via WebSocket
```

### 2.3 Componentes a Criar

#### Node.js Services

1. **`web_avatar/services/BrowserController.js` (NEW)**
   ```javascript
   const puppeteer = require('puppeteer')
   const EventEmitter = require('events')
   
   class BrowserController extends EventEmitter {
     constructor(options = {}) {
       super()
       this.browser = null
       this.page = null
       this.commandQueue = []
       this.isProcessing = false
       this.screenshotCache = new ScreenshotCache(10)
       this.DEFAULT_TIMEOUT = 30000 // 30s
     }
     
     async initialize() {
       this.browser = await puppeteer.launch({
         headless: true,
         args: ['--no-sandbox', '--disable-setuid-sandbox']
       })
       this.page = await this.browser.newPage()
     }
     
     async executeCommand(cmd) {
       // cmd = { type: 'navigate'|'click'|etc, params: {...} }
       
       try {
         const start = Date.now()
         
         switch(cmd.type) {
           case 'navigate':
             await this.page.goto(cmd.params.url, { timeout: this.DEFAULT_TIMEOUT })
             break
           case 'click':
             await this.page.click(cmd.params.selector, { timeout: this.DEFAULT_TIMEOUT })
             break
           case 'type':
             await this.page.type(cmd.params.selector, cmd.params.text)
             break
           case 'screenshot':
             const buffer = await this.page.screenshot()
             this.screenshotCache.add(buffer)
             return { screenshot: buffer.toString('base64') }
           case 'execute_script':
             return await this.page.evaluate(cmd.params.script)
           case 'wait':
             await this.page.waitForSelector(cmd.params.selector, { timeout: this.DEFAULT_TIMEOUT })
             break
         }
         
         const duration = Date.now() - start
         return { success: true, duration, result: null }
         
       } catch (err) {
         return { success: false, error: err.message }
       }
     }
   }
   
   module.exports = BrowserController
   ```

2. **`web_avatar/services/ScreenshotCache.js` (NEW)**
   ```javascript
   class ScreenshotCache {
     constructor(maxSize = 10) {
       this.maxSize = maxSize
       this.cache = []  // FIFO
     }
     
     add(buffer) {
       if (this.cache.length >= this.maxSize) {
         this.cache.shift()  // Remove oldest
       }
       this.cache.push({
         buffer,
         timestamp: Date.now(),
         base64: buffer.toString('base64')
       })
     }
     
     getAll() {
       return this.cache.map(item => ({
         timestamp: item.timestamp,
         base64: item.base64
       }))
     }
     
     clear() {
       this.cache = []
     }
   }
   
   module.exports = ScreenshotCache
   ```

#### Python Tools

1. **`agent/tools/browser_control.py` (NEW)**
   ```python
   from agent.tools.base import BaseTool
   import asyncio
   import json
   
   class BrowserControlTool(BaseTool):
       """Tool para controlar browser via Puppeteer."""
       
       def __init__(self, ws_client):
           super().__init__(
               name="browser_control",
               description="Control browser: navigate, click, type, screenshot, etc.",
               version="1.0"
           )
           self.ws_client = ws_client
           self.command_id_counter = 0
       
       async def navigate(self, url: str) -> dict:
           """Navigate to URL."""
           return await self._execute_command('navigate', {'url': url})
       
       async def click(self, selector: str) -> dict:
           """Click element."""
           return await self._execute_command('click', {'selector': selector})
       
       async def type(self, selector: str, text: str) -> dict:
           """Type text into element."""
           return await self._execute_command('type', {'selector': selector, 'text': text})
       
       async def screenshot(self) -> dict:
           """Take screenshot."""
           return await self._execute_command('screenshot', {})
       
       async def execute_script(self, script: str) -> dict:
           """Execute JavaScript."""
           return await self._execute_command('execute_script', {'script': script})
       
       async def wait(self, selector: str, timeout: int = 30000) -> dict:
           """Wait for element."""
           return await self._execute_command('wait', {'selector': selector, 'timeout': timeout})
       
       async def _execute_command(self, cmd_type: str, params: dict) -> dict:
           """Send command to BrowserController via WebSocket."""
           
           self.command_id_counter += 1
           cmd_id = f"cmd_{self.command_id_counter}"
           
           # Send command
           command = {
               'type': 'browser_command',
               'command_id': cmd_id,
               'command_type': cmd_type,
               'params': params
           }
           
           self.ws_client.send(json.dumps(command))
           
           # Wait for result (with timeout)
           result = await self._wait_for_result(cmd_id, timeout=35)  # 5s buffer
           
           return result
       
       async def _wait_for_result(self, cmd_id: str, timeout: int) -> dict:
           """Wait for browser_command_result with given cmd_id."""
           # TODO: Implement with asyncio.wait_for + event
           pass
   ```

2. **`agent/tools/registry.py` (MODIFY)**
   ```python
   # Add to registry:
   from agent.tools.browser_control import BrowserControlTool
   
   def register_tools(ws_client):
       registry = {
           # ... existing tools ...
           'browser_control': BrowserControlTool(ws_client)
       }
       return registry
   ```

#### Node.js Integration

1. **`web_avatar/server.js` (MODIFY)**
   ```javascript
   const BrowserController = require('./services/BrowserController')
   
   // Initialize browser controller at startup
   const browserController = new BrowserController()
   await browserController.initialize()
   
   // Handle browser_command from Python agent
   ws.on('message', async (msg) => {
       const parsed = JSON.parse(msg)
       
       if (parsed.type === 'browser_command') {
           const { command_id, command_type, params } = parsed
           
           // Execute command (with timeout)
           const result = await Promise.race([
               browserController.executeCommand({ type: command_type, params }),
               new Promise((_, rej) => setTimeout(() => rej('Timeout'), 30000))
           ])
           
           // Send result back to Python
           ws.send(JSON.stringify({
               type: 'browser_command_result',
               command_id,
               success: result.success,
               result: result.result,
               error: result.error,
               duration_ms: result.duration
           }))
       }
   })
   ```

### 2.4 Checklist de Implementação

**Node.js Services**
- [ ] Criar `BrowserController.js` com Puppeteer wrapper
- [ ] Criar `ScreenshotCache.js` com LRU eviction
- [ ] Implementar comandos: navigate, click, type, screenshot, execute_script, wait
- [ ] Adicionar timeout enforcement (30s default)
- [ ] Adicionar error handling + retry logic
- [ ] Testar: cada comando funciona isoladamente

**Node.js Server Integration**
- [ ] Modificar `server.js` para inicializar BrowserController
- [ ] Adicionar handler para `browser_command` messages
- [ ] Implementar response `browser_command_result`
- [ ] Testar: Python envia comando, servidor responde corretamente

**Python Tool**
- [ ] Criar `browser_control.py` (extends BaseTool)
- [ ] Implementar métodos: navigate, click, type, screenshot, execute_script, wait
- [ ] Adicionar WebSocket client para comunicação
- [ ] Modificar `registry.py` para registrar nova tool
- [ ] Testar: tool pode ser chamada de agente

**Testing**
- [ ] E2E: Python → navigate("google.com") → Browser abre Google
- [ ] E2E: Python → click("#search") → Elemento é clicado
- [ ] E2E: Python → screenshot() → Screenshot retorna em base64
- [ ] Timeout test: Comando que leva > 30s falha gracefully
- [ ] Error test: Click em selector inexistente retorna erro

### 2.5 Estimativa de Esforço

| Task | Tempo |
|------|-------|
| BrowserController.js | 3-4h |
| ScreenshotCache.js | 1h |
| browser_control.py (Tool) | 2-3h |
| Node.js integration | 2-3h |
| Integration testing | 2-3h |
| **Total Fase 2** | **10-14h** |

---

## 🤖 FASE 3: Autonomous Agent Integration (1 semana)

### 3.1 Objetivos Específicos

```
NOVO - Autonomous Browser Brain:
- BrowserBrain: novo 8º brain que planeja/executa tarefas browser
- LLM-based task planning (ex: "pesquisar IA no Google")
- BrowserCommandTracker: audit trail completo
- Real-time browser state streaming
- Exemplo flow: agent decide → plano multi-step → executa sequencialmente
```

### 3.2 Componentes a Criar

#### Python Backend

1. **`agent/brains/browser_brain.py` (NEW)**
   ```python
   from agent.core.messaging import Brain, EventType, AgentEvent
   import asyncio
   import json
   
   class BrowserBrain(Brain):
       """Brain autônomo para controlar browser."""
       
       def __init__(self, *args, **kwargs):
           super().__init__(*args, **kwargs)
           self.browser_state = {
               'current_url': None,
               'page_title': None,
               'elements_found': []
           }
           self.active_command = None
       
       async def initialize(self):
           await super().initialize()
           # Subscribe to tool results
           await self.event_bus.subscribe(EventType.TOOL_RESULT, self._on_tool_result)
       
       async def process(self):
           # Listen for browser tasks
           await asyncio.sleep(0.1)
       
       async def handle_browser_task(self, task: dict) -> None:
           """
           Recebe tarefa browser (ex: { type: 'search', params: { query: 'IA' } })
           Gera plano multi-step
           Executa sequencialmente
           """
           
           # 1. Generate plan using LLM
           plan = await self._generate_plan(task)
           # plan = [
           #   { type: 'navigate', params: { url: 'https://google.com' } },
           #   { type: 'click', params: { selector: '#search' } },
           #   { type: 'type', params: { selector: '#search', text: task['params']['query'] } },
           #   { type: 'screenshot', params: {} }
           # ]
           
           # 2. Execute plan sequentially
           for step in plan:
               await self._execute_step(step)
       
       async def _generate_plan(self, task: dict) -> list:
           """Use LLM to generate multi-step plan."""
           # Ex: LLM Input: "pesquisar IA no Google"
           # Ex: LLM Output: "[step1, step2, step3, step4]"
           
           prompt = f"""
           Você é um especialista em automação web. 
           Tarefa: {task['description']}
           
           Gere um plano JSON com passos (cada passo tem 'type' e 'params'):
           - navigate: ir para URL
           - click: clicar em selector
           - type: escrever texto
           - wait: esperar elemento
           - screenshot: capturar tela
           - execute_script: rodar JS
           
           Retorne apenas JSON válido, sem markdown.
           """
           
           # TODO: Call ReasoningBrain LLM
           # For now, return hardcoded example
           return [
               { 'type': 'navigate', 'params': { 'url': 'https://google.com' } },
               { 'type': 'click', 'params': { 'selector': '[aria-label="Search"]' } },
               { 'type': 'type', 'params': { 'selector': '[aria-label="Search"]', 'text': task.get('query', '') } },
               { 'type': 'screenshot', 'params': {} }
           ]
       
       async def _execute_step(self, step: dict) -> None:
           """Execute single step and track result."""
           
           self.active_command = step
           
           # Publish BROWSER_COMMAND event
           await self.publish_event(EventType.BROWSER_COMMAND, step)
           
           # TODO: Wait for BROWSER_COMMAND_RESULT
           # For now, assume success
           
           # Publish state change
           await self.publish_event(EventType.BROWSER_STATE_CHANGED, {
               'current_command': step,
               'state': self.browser_state
           })
       
       async def _on_tool_result(self, event: AgentEvent):
           """Handler for TOOL_RESULT events."""
           if event.payload.get('tool_name') == 'browser_control':
               # Update browser state
               if event.payload.get('success'):
                   result = event.payload.get('result', {})
                   if 'current_url' in result:
                       self.browser_state['current_url'] = result['current_url']
                   if 'page_title' in result:
                       self.browser_state['page_title'] = result['page_title']
   ```

2. **`agent/core/messaging/browser_tracker.py` (NEW)**
   ```python
   from dataclasses import dataclass, field
   from typing import Dict, Any, List
   from datetime import datetime
   import time
   
   @dataclass
   class BrowserCommand:
       """Comando executado no browser."""
       command_id: str
       timestamp: float = field(default_factory=time.time)
       command_type: str = ""  # navigate, click, type, etc
       params: Dict[str, Any] = field(default_factory=dict)
       result: Dict[str, Any] = field(default_factory=dict)
       duration_ms: float = 0.0
       success: bool = False
       error: str = ""
   
   class BrowserCommandTracker:
       """Tracker de audit trail para browser commands."""
       
       MAX_COMMANDS = 1000
       
       def __init__(self):
           self.commands: List[BrowserCommand] = []
       
       def add_command(self, cmd: BrowserCommand) -> None:
           """Add command to tracker (circular buffer)."""
           if len(self.commands) >= self.MAX_COMMANDS:
               self.commands.pop(0)  # Remove oldest
           self.commands.append(cmd)
       
       def get_recent(self, limit: int = 50) -> List[BrowserCommand]:
           """Get most recent commands."""
           return self.commands[-limit:]
       
       def get_by_type(self, cmd_type: str) -> List[BrowserCommand]:
           """Filter by command type."""
           return [cmd for cmd in self.commands if cmd.command_type == cmd_type]
       
       def get_all(self) -> List[BrowserCommand]:
           """Get all commands."""
           return self.commands
   ```

3. **`agent/core/messaging/shared_state.py` (MODIFY)**
   ```python
   from agent.core.messaging.browser_tracker import BrowserCommandTracker
   
   class SharedAgentState:
       def __init__(self):
           # ... existing fields ...
           self.browser_tracker = BrowserCommandTracker()
       
       async def track_browser_command(self, cmd):
           """Track browser command."""
           self.browser_tracker.add_command(cmd)
   ```

4. **`agent/core/messaging/event_bus.py` (MODIFY)**
   ```python
   class EventType(str, Enum):
       # ... existing types ...
       BROWSER_COMMAND = "browser_command"
       BROWSER_COMMAND_RESULT = "browser_command_result"
       BROWSER_STATE_CHANGED = "browser_state_changed"
   ```

5. **`agent/orchestrator.py` (MODIFY)**
   ```python
   from agent.brains import BrowserBrain
   
   class AgentOrchestrator:
       def __init__(self, ...):
           # ... existing 7 brains ...
           self.browser_brain = BrowserBrain("browser_brain", self.event_bus, self.shared_state)
           
           self.brains: List[Brain] = [
               self.input_brain,
               self.reasoning_brain,
               self.planning_brain,
               self.execution_brain,
               self.sentiment_brain,
               self.avatar_brain,
               self.output_brain,
               self.browser_brain,  # NEW: 8º brain
           ]
   ```

### 3.3 Data Flow

```
User asks: "pesquisar IA no Google"
    ↓
ReasoningBrain detects intent: { type: 'browser_search', query: 'IA' }
    ↓
PlanningBrain creates task for BrowserBrain
    ↓
ExecutionBrain dispatches to BrowserBrain
    ↓
BrowserBrain.handle_browser_task():
  1. Call LLM: Generate multi-step plan
  2. Execute plan step-by-step:
     - navigate(google.com)
     - click(search_box)
     - type("IA")
     - screenshot()
  3. Each step:
     - Publish BROWSER_COMMAND
     - Wait for BROWSER_COMMAND_RESULT
     - Track in BrowserCommandTracker
     - Publish BROWSER_STATE_CHANGED
    ↓
Frontend receives BROWSER_STATE_CHANGED:
  - Update BrowserPanel with state
  - Show latest screenshot
  - Add command to history table
```

### 3.4 Checklist de Implementação

**Python Backend**
- [ ] Criar `browser_brain.py` (autonomous brain)
- [ ] Criar `browser_tracker.py` (audit trail)
- [ ] Modificar `shared_state.py` para incluir tracker
- [ ] Adicionar event types em `event_bus.py`
- [ ] Modificar `orchestrator.py` para registrar 8º brain
- [ ] Testar: BrowserBrain recebe tarefas e executa

**Integration**
- [ ] BrowserBrain comunica com browser_control tool
- [ ] browser_control tool envia commands para BrowserController
- [ ] BrowserController executa e retorna resultados
- [ ] Resultados fluem de volta para BrowserBrain
- [ ] BrowserCommandTracker captura todas as transações

**Testing**
- [ ] E2E: "pesquisar IA no Google" completa end-to-end
- [ ] Verificar BrowserCommandTracker tem 4 comandos (navigate, click, type, screenshot)
- [ ] Verificar cada comando tem duration_ms e success status
- [ ] Verificar error handling: comando que falha não quebra pipeline

### 3.5 Estimativa de Esforço

| Task | Tempo |
|------|-------|
| BrowserBrain.py | 4-5h |
| BrowserTracker.py | 1-2h |
| Event types + orchestrator updates | 1h |
| Integration testing | 2-3h |
| LLM-based planning | 1-2h (optional MVP: hardcoded plans) |
| **Total Fase 3** | **9-13h** |

---

## 📋 RESUMO DE ARQUIVOS

### Criar (NEW)
```
web_avatar/services/BrowserController.js
web_avatar/services/ScreenshotCache.js
web_avatar/src/components/ModelMetricsCard.jsx
web_avatar/src/components/FilterPanel.jsx
web_avatar/src/components/LatencyChart.jsx
web_avatar/src/components/SummaryStats.jsx
web_avatar/src/components/BrowserPanel.jsx (Phase 4)
agent/tools/browser_control.py
agent/brains/browser_brain.py
agent/core/messaging/browser_tracker.py
```

### Modificar (MODIFY)
```
web_avatar/src/components/DebugPanel.jsx
web_avatar/server.js
agent/brains/output_brain.py
agent/core/messaging/event_bus.py
agent/core/messaging/shared_state.py
agent/tools/registry.py
agent/orchestrator.py
```

### Não Modificar (Stable)
```
web_avatar/src/logic/WebSocketClient.js
web_avatar/src/App.jsx
agent/orchestrator.py (existing 7 brains)
```

---

## 🔐 Considerações de Segurança

### Phase 1
- ✅ Métricas são apenas leitura (nenhuma execução)
- ✅ Dados vêm do backend confiável
- ⚠️ TODO: Validar estrutura JSON (message validation)

### Phase 2
- ⚠️ TODO: Whitelist de domínios (domain allowlist)
- ⚠️ TODO: Timeout enforcement (30s default)
- ⚠️ TODO: Screenshot cache memory limit
- ⚠️ TODO: Sanitizar seletores CSS

### Phase 3
- ⚠️ TODO: LLM prompt injection (sempre sanitizar user input)
- ⚠️ TODO: Audit trail para compliance
- ✅ BrowserCommandTracker registra tudo

### Phase 4+
- ⚠️ TODO: WSS (TLS para WebSocket)
- ⚠️ TODO: Role-based permissions (who can trigger browser)
- ⚠️ TODO: Rate limiting (max commands/sec)

---

## 📊 Métricas de Sucesso

**Phase 1**: DebugPanel mostra metrics com filtros
- [ ] ModelMetricsCard renderiza emotion, latency, tokens
- [ ] FilterPanel filtra por status (active/idle/error) + text search
- [ ] LatencyChart mostra últimas 100 amostras
- [ ] SummaryStats mostra active count, avg latency, total tokens
- [ ] Dados atualizam em tempo real (< 100ms latência)

**Phase 2**: Browser automation funciona
- [ ] BrowserController inicia Puppeteer sem erros
- [ ] Comando navigate() vai para URL corretamente
- [ ] Comando click() clica em elementos
- [ ] Comando screenshot() retorna base64 válido
- [ ] Timeout de 30s é enforcement (comando > 30s falha)
- [ ] Error handling: comando inválido retorna erro gracefully

**Phase 3**: Autonomous execution
- [ ] BrowserBrain gera plano multi-step correto
- [ ] Plano é executado sequencialmente sem erros
- [ ] BrowserCommandTracker tem N comandos com timestamps
- [ ] Cada comando tem duration_ms e success/error status
- [ ] "pesquisar IA no Google" completa end-to-end

---

## ⏱️ Timeline Total

| Phase | Duration | Start | End | Status |
|-------|----------|-------|-----|--------|
| Analysis | 3h | Day 1 | Day 1 | ✅ DONE |
| **Phase 1** | 1 week | Day 2 | Day 8 | 🔜 NEXT |
| Phase 2 | 1 week | Day 9 | Day 15 | ⏳ |
| Phase 3 | 1 week | Day 16 | Day 22 | ⏳ |
| Phase 4 | 1 week | Day 23 | Day 29 | ⏳ |
| **Total** | **4 weeks** | | | |

---

## ❓ Próximos Passos

1. **Aprovação**: Review desta arquitetura com stakeholders
2. **Phase 1 Start**: Começar com DebugPanel improvements (menos risco)
3. **Puppeteer Research**: Aguardar resultado bg_e30d1df3 para refinar Fase 2
4. **Staging Environment**: Setup teste isolado para Puppeteer
5. **CI/CD**: Considerar como testar automação browser (pode ser slow)

---

**Documento preparado por**: Sisyphus Analysis Mode
**Confidencial**: Este plano é detalhado e pronto para implementação
