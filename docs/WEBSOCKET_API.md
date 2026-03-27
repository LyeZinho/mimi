# WebSocket API Reference

**Data:** 27 de Março de 2026  
**Status:** Documentação completa das mensagens WebSocket

---

## Visão Geral

O sistema Mimi usa WebSocket para comunicação em tempo real entre:
- **Frontend React** (web_avatar/src)
- **Node.js Server** (web_avatar/server.js)
- **Backend Python Agent** (agent/main.py)

---

## Connection

### Conectar ao WebSocket

**URL:** `ws://localhost:8765`

**Client JavaScript:**
```javascript
const ws = new WebSocket('ws://localhost:8765');

ws.onopen = () => console.log('Connected');
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  console.log('Received:', msg.type);
};
ws.onerror = (error) => console.error('Error:', error);
ws.onclose = () => console.log('Disconnected');
```

**Client Python:**
```python
import asyncio
import websockets
import json

async def connect():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as ws:
        # Send message
        await ws.send(json.dumps({
            "type": "text_input",
            "message": "Olá Mimi"
        }))
        
        # Receive message
        response = await ws.recv()
        print(json.loads(response))

asyncio.run(connect())
```

---

## Message Types

### 1️⃣ INPUT MESSAGES (Frontend → Backend)

#### `text_input` - Enviar mensagem de texto

```json
{
  "type": "text_input",
  "message": "Olá Mimi, como você está?"
}
```

**Handler:** `agent/input/text_input.py`  
**Processamento:** Input Brain → Reasoning Brain

---

#### `voice_input` - Enviar áudio (experimental)

```json
{
  "type": "voice_input",
  "data": "base64_encoded_audio_chunk",
  "sample_rate": 16000
}
```

**Handler:** `agent/input/voice_input.py`  
**Processamento:** Input Brain (VAD) → STT

---

#### `control` - Controlar avatar diretamente

```json
{
  "type": "control",
  "action": "happy",
  "gesture": "wave",
  "speaking": false
}
```

**Actions disponíveis:**
- `happy`, `sad`, `angry`, `surprised`, `confused`, `neutral`, `thinking`

**Gestures:** `wave`, `nod`, `shake`, `point`, `bow`

---

#### `browser_command` - Comando do navegador (Phase 2)

```json
{
  "type": "browser_command",
  "action": "navigate",
  "url": "https://wikipedia.org"
}
```

**Actions disponíveis:**
- `launch` - Iniciar navegador
- `navigate(url)` - Navegar para URL
- `click(selector)` - Clicar elemento
- `type(selector, text)` - Digitar texto
- `screenshot()` - Capturar tela
- `extractText()` - Extrair texto da página
- `executeScript(code)` - Executar JavaScript
- `wait(ms)` - Aguardar N milissegundos
- `goBack()` - Voltar na história
- `goForward()` - Avançar na história
- `shutdown()` - Fechar navegador

---

### 2️⃣ STATE MESSAGES (Server → Frontend)

#### `state` - Estado do avatar atualizado

```json
{
  "type": "state",
  "state": {
    "model": "Mimi.vrm",
    "expression": "happy",
    "animation": "wave",
    "speaking": true,
    "camera": {
      "position": {"x": 0, "y": 1.4, "z": 2},
      "target": {"x": 0, "y": 1.2, "z": 0}
    },
    "background": "#1a1a2e",
    "lastUpdate": 1711518942123
  }
}
```

**Broadcast:** Enviado para todos os clientes quando qualquer cliente atualiza

---

#### `avatar_control` - Comando de controle do avatar

```json
{
  "type": "avatar_control",
  "emotion": "happy",
  "gesture": "wave",
  "speak": true,
  "animation": "talk",
  "latency": 245
}
```

**Fonte:** Python Agent (via ActionRouter)  
**Destino:** Frontend (AvatarCanvas)

---

#### `agent_status` - Métricas do agente (Phase 1)

```json
{
  "type": "agent_status",
  "latency": 245,
  "tokens": 150,
  "emotion": "happy",
  "timestamp": 1711518942123
}
```

**Frequência:** A cada resposta do agente  
**Uso:** Debug Panel (ModelStatusCard, LatencyChart)

---

### 3️⃣ BROWSER MESSAGES (Server → Frontend)

#### `browser_command_result` - Resultado de comando

```json
{
  "type": "browser_command_result",
  "action": "navigate",
  "success": true,
  "data": {
    "url": "https://wikipedia.org",
    "title": "Wikipedia"
  }
}
```

---

#### `browser_action` - Ação de navegador (broadcast)

```json
{
  "type": "browser_action",
  "action": "screenshot",
  "data": "data:image/png;base64,iVBORw0KGgo...",
  "timestamp": 1711518942123
}
```

---

#### `browser_history` - Histórico de comandos

```json
{
  "type": "browser_history",
  "history": [
    {
      "command": {"action": "navigate", "url": "https://google.com"},
      "result": {"success": true},
      "timestamp": 1711518942000
    },
    {
      "command": {"action": "type", "selector": "input[name=q]", "text": "linux"},
      "result": {"success": true},
      "timestamp": 1711518942100
    }
  ]
}
```

---

### 4️⃣ CONFIG MESSAGES

#### `llm_config` - Configuração do LLM

```json
{
  "type": "llm_config",
  "config": {
    "model": "phi3:mini",
    "temperature": 0.7,
    "max_tokens": 1024,
    "top_p": 0.9,
    "top_k": 40
  }
}
```

---

### 5️⃣ DEBUG MESSAGES

#### `debug_info` - Informações de debug

```json
{
  "type": "debug_info",
  "memory_usage": "45.2 MB",
  "connections": 3,
  "event_queue": 12,
  "active_brains": 7,
  "fps": 60
}
```

---

## Event Flow Examples

### Exemplo 1: Usuário Envia Mensagem de Texto

```
User Types: "Olá Mimi"
     ↓
Frontend sends:
{
  "type": "text_input",
  "message": "Olá Mimi"
}
     ↓
Server receives → relays to Python Agent
     ↓
Agent processes:
  Input Brain → receives text
  Reasoning Brain → calls LLM (streaming)
  Sentiment Brain → detects emotion
  Avatar Brain → queues animation
  Output Brain → generates TTS
     ↓
Agent sends multiple messages:
{
  "type": "avatar_control",
  "emotion": "happy",
  "speak": true,
  "animation": "talk"
}
{
  "type": "agent_status",
  "latency": 245,
  "tokens": 150
}
     ↓
Frontend receives → updates avatar
```

---

### Exemplo 2: Browser Command (Phase 2)

```
User requests: "Pesquisa sobre Linux"
     ↓
BrowserBrain decides → navigate + search
     ↓
Agent sends:
{
  "type": "browser_command",
  "action": "navigate",
  "url": "https://google.com"
}
     ↓
Server receives → BrowserController.navigate()
     ↓
Server sends back:
{
  "type": "browser_command_result",
  "action": "navigate",
  "success": true,
  "data": {"url": "https://google.com"}
}
     ↓
Server broadcasts screenshot:
{
  "type": "browser_action",
  "action": "screenshot",
  "data": "data:image/png;base64,..."
}
     ↓
Frontend receives → displays in BrowserPanel
```

---

## Broadcasting Rules

### Quem Recebe Mensagens?

| Mensagem | Sender | Recipients |
|----------|--------|------------|
| `avatar_control` | Agent (Python) | Todos clientes React |
| `agent_status` | Agent (Python) | Todos clientes React |
| `browser_action` | Server | Todos clientes React (exceto sender) |
| `state` | Qualquer client | Todos clientes (exceto sender) |
| `browser_command_result` | Server | Client que enviou o comando |

### Exemplo de Broadcast

```javascript
// server.js - Broadcast avatar_control
function broadcastAvatarControl(msg, exceptWs = null) {
  wss.clients.forEach((client) => {
    if (client.readyState === WebSocket.OPEN && client !== exceptWs) {
      client.send(JSON.stringify(msg));
    }
  });
}
```

---

## Latency & Performance

### Métricas Monitoradas

```json
{
  "type": "agent_status",
  "latency": 245,          // ms desde input até response
  "tokens": 150,           // tokens gerados pelo LLM
  "timestamp": 1711518942123
}
```

### Targets

| Métrica | Target | Current |
|---------|--------|---------|
| Input → Response | <2s | 1-3s |
| WebSocket Latency | <50ms | 10-30ms |
| Avatar Animation | 60 FPS | 60 FPS |
| TTS Streaming | Real-time | <100ms chunks |

---

## Error Handling

### Erro No Servidor

```json
{
  "type": "error",
  "code": "BROWSER_LAUNCH_FAILED",
  "message": "Failed to launch Chrome: timeout",
  "timestamp": 1711518942123
}
```

### Erro No Agente

```python
# agent/avatar/interface.py
async def handle_message(msg):
    try:
        # process
    except Exception as e:
        await ws.send(json.dumps({
            "type": "error",
            "error": str(e),
            "source": "agent"
        }))
```

---

## Versionamento

### Mudanças Futuras

**Phase 1 (Atual):**
- ✅ `text_input`, `voice_input`, `control`
- ✅ `state`, `avatar_control`
- ✅ `agent_status` (NEW)

**Phase 2:**
- 🔄 `browser_command`, `browser_command_result`
- 🔄 `browser_action`, `browser_history`

**Phase 3:**
- 🔮 `browser_brain_status` (autonomous decisions)
- 🔮 `screenshot_cache` (caching)

**Phase 4:**
- 🔮 `browser_panel_update` (full dashboard)

---

## Testing WebSocket Messages

### Manual Testing com wscat

```bash
# Install
npm install -g wscat

# Connect
wscat -c ws://localhost:8765

# Send message
> {"type":"text_input","message":"Olá"}

# Receive (watch output)
```

### Python Test Script

```python
import asyncio
import websockets
import json

async def test():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as ws:
        # Send
        await ws.send(json.dumps({
            "type": "text_input",
            "message": "Test message"
        }))
        
        # Receive (timeout after 5s)
        try:
            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            print("Response:", json.loads(response))
        except asyncio.TimeoutError:
            print("No response received")

asyncio.run(test())
```

---

## Documentação Relacionada

- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - Estrutura do projeto
- [ARCHITECTURE.md](ARCHITECTURE.md) - Arquitetura dos 7 brains
- [plans/2026-03-27-browser-control-debug-panel-implementation.md](plans/2026-03-27-browser-control-debug-panel-implementation.md) - Plano Phase 1

---

**Mantido por:** Sistema de Documentação Sisyphus  
**Última Atualização:** 27 de Março de 2026
