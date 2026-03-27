# 🧠 Multi-Brain Architecture Guide

Mimi agora usa uma arquitetura **7-brain** com audio streaming em tempo real, comunicação via event bus, e gerenciamento de estado compartilhado.

## Quick Start

### 1. Estrutura de Diretórios

```
agent/
├── core/
│   ├── messaging/
│   │   ├── event_bus.py           # Bus pub/sub async
│   │   ├── shared_state.py        # State com locks
│   │   └── brain_base.py          # Base abstrata para brains
│   └── ...
│
├── brains/
│   ├── input_brain.py             # Brain 1: VAD + STT
│   ├── reasoning_brain.py         # Brain 2: LLM inference
│   ├── planning_brain.py          # Brain 3: Ação (sem LLM)
│   ├── execution_brain.py         # Brain 4: Execução (sem LLM)
│   ├── sentiment_brain.py         # Brain 5: Emoção (sem LLM)
│   ├── avatar_brain.py            # Brain 6: Avatar 3D (sem LLM)
│   └── output_brain.py            # Brain 7: TTS
│
├── buffers/
│   └── audio_buffers.py           # Ring buffer + Chunk queue
│
├── orchestrator.py                 # Coordenador central
└── ...
```

### 2. Inicializar e Executar

```python
from agent.orchestrator import AgentOrchestrator
import asyncio

async def main():
    # Criar orchestrator
    orchestrator = AgentOrchestrator(user_id="user_1")
    
    # Inicializar todos os brains
    await orchestrator.initialize()
    
    # Começar processamento
    await orchestrator.start()
    
    # Enviar input
    await orchestrator.process_text_input("Olá Mimi!")
    
    # Aguardar processamento
    await asyncio.sleep(2.0)
    
    # Ver métricas
    metrics = await orchestrator.get_metrics()
    print(metrics)
    
    # Parar
    await orchestrator.stop()

asyncio.run(main())
```

## Os 7 Brains

### 🎤 Brain 1: Input Brain (VAD + STT)
- **Responsabilidade**: Capturar áudio, detectar fala, converter a texto
- **Entrada**: Frames de áudio do microfone
- **Saída**: `TRANSCRIPTION_COMPLETE` event
- **Sem LLM**: Usa `faster-whisper` e `webrtcvad` (locais)
- **Buffers**: Ring buffer para VAD, chunk queue para STT

### 🧠 Brain 2: Reasoning Brain (LLM)
- **Responsabilidade**: Inferir intenção, gerar resposta
- **Entrada**: `TRANSCRIPTION_COMPLETE` event
- **Saída**: `INTENT_DETECTED` event
- **Com LLM**: Invoca Ollama/Mistral
- **Streaming**: Não espera a resposta completa

### 📋 Brain 3: Planning Brain (Schema Validation)
- **Responsabilidade**: Validar intenção, selecionar ações
- **Entrada**: `INTENT_DETECTED` event
- **Saída**: `TOOLS_QUEUED` event
- **Sem LLM**: Regras eficientes
- **Token Economy**: 0% custo!

### ⚙️ Brain 4: Execution Brain (Tool Dispatcher)
- **Responsabilidade**: Executar ações em paralelo
- **Entrada**: `TOOLS_QUEUED` event
- **Saída**: `TOOL_RESULT` event
- **Sem LLM**: Puro executor
- **Concorrência**: ThreadPoolExecutor para I/O

### 😊 Brain 5: Sentiment Brain (Emotion Detection)
- **Responsabilidade**: Detectar emoção do utilizador e agente
- **Entrada**: `TRANSCRIPTION_COMPLETE` + `INTENT_DETECTED`
- **Saída**: `SENTIMENT_UPDATED`, `EMOTION_DETECTED`
- **Sem LLM**: Análise léxica simples
- **Token Economy**: 0% custo!

### 🎭 Brain 6: Avatar Brain (3D Model Control)
- **Responsabilidade**: Controlar animações e expressões do avatar
- **Entrada**: `EMOTION_DETECTED`, `TTS_STARTED`, `TTS_COMPLETE`
- **Saída**: `ANIMATION_QUEUED`, `GESTURE_QUEUED`
- **Sem LLM**: Mappings determinísticos
- **Síncrono**: Coordena com TTS para lip-sync

### 🔊 Brain 7: Output Brain (TTS)
- **Responsabilidade**: Converter texto a fala (streaming)
- **Entrada**: `INTENT_DETECTED` event
- **Saída**: `TTS_STARTED`, `TTS_CHUNK`, `TTS_COMPLETE`
- **Sem LLM**: Usa Piper TTS ou Coqui
- **Streaming**: Não espera síntese completa

---

## Event Bus (Pub/Sub)

Todos os brains comunicam via **event bus async**, non-blocking:

```python
from agent.core.messaging import get_event_bus, EventType

bus = get_event_bus()

# Subscribe a eventos
@bus.subscribe(EventType.INTENT_DETECTED)
async def on_intent(event):
    print(f"Intent: {event.payload}")

# Publish eventos
await bus.publish(AgentEvent(
    type=EventType.INTENT_DETECTED,
    source_brain="reasoning_brain",
    payload={"intent": "chat", "response": "Hello"}
))
```

### Tipos de Eventos

- `AUDIO_CHUNK`, `VAD_START`, `VAD_END`, `TRANSCRIPTION_*`
- `INTENT_*`, `TOOLS_QUEUED`, `TOOL_*`
- `SENTIMENT_*`, `EMOTION_DETECTED`
- `ANIMATION_QUEUED`, `GESTURE_QUEUED`, `AVATAR_STATE_*`
- `TTS_*`
- `BRAIN_HEALTH`, `SYSTEM_ERROR`

---

## Shared State (Locking)

**Lock-free reads**, **serialized writes**:

```python
from agent.core.messaging import get_shared_state

state = get_shared_state()

# Ler (lock-free)
snapshot = await state.get_context_snapshot()
print(snapshot.user_id, snapshot.state)

# Escrever (com lock)
await state.update_context("my_brain", {
    "state": "processing",
    "last_detected_emotion": "happy"
})

# Health
health = await state.get_brain_health("input_brain")
print(f"Healthy: {health.is_healthy()}")
```

---

## Audio Buffers (Hybrid)

### Ring Buffer
- Mantém 3 segundos de história
- Snapshots para VAD
- Auto-recicla

```python
from agent.buffers import RingBuffer

ring = RingBuffer(capacity_bytes=96000)

await ring.write(audio_frame)
snapshot = await ring.snapshot()
```

### Chunk Queue
- FIFO com TTL
- Para STT, TTS chunks

```python
from agent.buffers import ChunkQueue, AudioChunk

queue = ChunkQueue(ttl_ms=5000)

chunk = AudioChunk(data=b'...', sample_rate=16000)
await queue.put(chunk)

retrieved = await queue.get()
```

---

## Orchestrator API

```python
orchestrator = AgentOrchestrator()

# Lifecycle
await orchestrator.initialize()
await orchestrator.start()
await orchestrator.stop()

# Input
await orchestrator.process_text_input("Olá!")

# Observability
metrics = await orchestrator.get_metrics()
state = await orchestrator.get_state_snapshot()
history = await orchestrator.get_event_history(event_type="INTENT_DETECTED", limit=10)
```

---

## Design Principles

### 1. Token Economy
- **Reasoning Brain**: LLM (custo)
- **Planning Brain**: Regras (free)
- **Sentiment Brain**: Léxica (free)
- **Avatar Brain**: Mappings (free)

→ Economiza ~70% de tokens comparado a monolithic LLM

### 2. Real-Time Performance
- Ring buffer: eficiente
- Streaming TTS: não espera completo
- Async everywhere: non-blocking
- Latência alvo: < 300ms

### 3. Modularity
- Cada brain é independente
- Event bus desacoplado
- Fácil substituir modelos ou implementações
- Suporta pausa/resume individual

### 4. Observability
- Event history com timestamps
- Health per brain (heartbeats, latencies)
- Métricas por brain
- State snapshots para debug

---

## Exemplo: Fluxo Completo

```
User: "Qual é a temperatura em Lisboa?"

[0ms]   Input Brain: STT
        → publish(TRANSCRIPTION_COMPLETE, "Qual é a...")

[100ms] Reasoning Brain: LLM
        → publish(INTENT_DETECTED, {action: "fetch_weather"})

[110ms] Planning Brain: valida + seleciona ações
        → publish(TOOLS_QUEUED, [{type: "call_api"}])

[120ms] Sentiment Brain: analisa
        → publish(EMOTION_DETECTED, "neutral")

[120ms] Execution Brain: executa
        → publish(TOOL_RESULT, {temperature: 23})

[130ms] Avatar Brain: atualiza expressão
        → publish(ANIMATION_QUEUED, "neutral_face")

[140ms] Output Brain: TTS começa
        → publish(TTS_STARTED)
        → publish(TTS_CHUNK, ...)

[200ms] Avatar: começa falar (lip-sync)

[300ms] Resposta completa
```

---

## Integração com Código Existente

### Migrando de `agent/main.py`

Antes:
```python
agent = Agent()
response = agent.process(user_input)
```

Depois:
```python
orchestrator = AgentOrchestrator()
await orchestrator.initialize()
await orchestrator.start()
await orchestrator.process_text_input(user_input)
metrics = await orchestrator.get_metrics()
```

---

## Next Steps

1. ✅ Estrutura de brains criada
2. ✅ Event bus + shared state implementados
3. ⏳ Integrar Input Brain com `sounddevice` + `faster-whisper` + `webrtcvad`
4. ⏳ Integrar Reasoning Brain com Ollama
5. ⏳ Integrar Output Brain com Piper TTS
6. ⏳ Integrar Avatar Brain com web_avatar/WebSocket
7. ⏳ Testes end-to-end
8. ⏳ Performance tuning

---

## Troubleshooting

### "Brain not responding"
```python
health = await state.get_brain_health("brain_id")
if not health.is_healthy():
    print(f"Last heartbeat: {health.last_heartbeat}")
```

### "Event bus queue full"
Aumentar `max_queue_size` em `EventBus(max_queue_size=5000)`

### "Ring buffer overflow"
Aumentar `ring_buffer_duration_sec` em `BufferManager()`

---

Para documentação completa, veja: `docs/ARCHITECTURE.md`
