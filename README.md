# Mimi – Agente de IA Interativo Multimodal

Agente cognitivo leve, offline-first, com foco em voz e modularidade.

## ⚙️ Setup Completo (Primeiro Uso)

### Pré-requisitos
- **Python 3.10+**
- **Node.js 18+**
- **API key Ollama** (fornecida)

### 1. Configuração de Ambiente

```bash
# Clone e entre no diretório
git clone <repo-url>
cd Mimi

# Crie arquivo .env com credenciais
cp .env.example .env
# Edite .env e adicione: OLLAMA_API_KEY=<sua_chave>
```

### 2. Setup Python

```bash
# Crie venv e instale dependências
python3 -m venv .venv
source .venv/bin/activate  # ou .venv\Scripts\activate no Windows

# Instale dependências
pip install -r requirements.txt

# Opcional: instale voz e TTS
pip install sounddevice webrtcvad faster-whisper piper-tts
```

### 3. Setup Node.js

```bash
# Instale dependências do servidor WebSocket
npm install

# Instale dependências do frontend
cd web_avatar && npm install && cd ..
```

### 4. Teste Conectividade Ollama

```bash
pytest tests/test_ollama_connectivity.py -v
```

Expected: ✓ Testes passam (ou skip se rede indisponível)

### 5. Inicie o Sistema

Abra **3 terminais** no diretório raiz:

**Terminal 1 - WebSocket Server:**
```bash
cd web_avatar && node server.js
```
Esperado: `WebSocket/HTTP server rodando em ws://localhost:8765`

**Terminal 2 - Agent Python:**
```bash
source .venv/bin/activate
python agent/main.py
```
Esperado: `Conectando ao backend em ws://localhost:8765...`

**Terminal 3 - React Frontend:**
```bash
cd web_avatar && npm run dev
```
Esperado: `Local: http://localhost:5173/`

### 6. Acesse a Interface

- **Web**: http://localhost:5173
- **OBS Stream**: http://localhost:5173/obs.html
- **Chat**: Digite mensagens ou use microfone (STT em implementação)

---

## 🚀 Quick Start (Após Setup)

### For Bash/Zsh:
```bash
./start_dev.sh
```

### For Fish Shell:
```fish
source start_dev.fish
```

Both scripts show the 3 commands needed to run in separate terminals.

---

## 🎭 Avatar 3D (Web)

O projeto utiliza solução 100% Web (Three.js + VRM).

1. **Abra o navegador** em http://localhost:5173
2. **Selecione um modelo VRM** (Mimi.vrm incluído ou faça upload)
3. **Chat**: Digite mensagens para conversar com o agente

### OBS Studio Integration

1. **No OBS**, adicione uma fonte **Browser**
2. **URL**: `http://localhost:5173/obs.html`
3. **Resolução**: 1920x1080
4. **Fundo**: Transparente (já configurado)

---

## 🎥 Mirror Stream & LLM Control

Mimi inclui um sistema completo de **WebRTC Mirror Stream** com **controle multimodal via LLM**, permitindo streaming do avatar 3D para OBS/Twitch e controle em tempo real de emoções, gestos e estado do agente.

### Recursos Principais

- **🎬 Mirror Stream**: Captura de canvas 3D a 10 FPS (100ms throttle) via WebSocket
- **🤖 Controle LLM**: Emoções, gestos e animações controlados pelo agente Python
- **🔍 DebugPanel**: Monitoramento em tempo real do estado multimodal do avatar
- **📺 OBS Ready**: Endpoint dedicado `/mirror.html` para integração com software de broadcast
- **🔄 Reconexão Automática**: Sistema resiliente com backoff exponencial

### Quick Start: Mirror Stream

**1. Inicie o sistema completo:**

```bash
# Terminal 1: WebSocket Server
cd web_avatar && node server.js

# Terminal 2: Agent Python
source .venv/bin/activate && python agent/main.py

# Terminal 3: React Frontend
cd web_avatar && npm run dev
```

**2. Configure OBS Studio:**

1. Adicione fonte **Browser**
2. URL: `http://localhost:5173/mirror.html`
3. Resolução: 1920x1080
4. O status "Live" aparecerá em verde quando conectado

**3. Teste o sistema:**

- Digite no chat: "olá Mimi"
- Observe o **DebugPanel** (sidebar direita) mostrando emoções em tempo real
- Avatar responderá com emoção e gesto apropriados

### Emoções do Agente

O agente LLM controla o avatar via mensagens WebSocket `avatar_control`:

| Emoção | Indicador | Uso |
|--------|-----------|-----|
| 🟢 **Happy** | Verde | Resposta positiva |
| 🔵 **Sad** | Azul | Resultado negativo |
| 🔴 **Angry** | Vermelho | Frustração |
| 🟠 **Surprised** | Laranja | Input inesperado |
| 🟣 **Confused** | Roxo | Pedido unclear |
| ⚪ **Neutral** | Cinza | Estado idle |
| ⚫ **Thinking** | Cinza escuro | Processando |

### DebugPanel

O componente **DebugPanel** (sidebar direita) exibe:

- **Emotion**: Estado emocional atual (color-coded)
- **Action/Gesture**: Gesto/animação em execução
- **Speaking**: Indicador 🔊/🔇 de fala ativa
- **Animation**: Nome da animação VRM atual
- **Mirror FPS**: Taxa de captura do stream (10 FPS ideal)
- **Frames**: Contador total de frames transmitidos
- **Last Update**: Timestamp da última atualização

### Performance

| Métrica | Valor | Notas |
|---------|-------|-------|
| Frame Rate | 10 FPS | Throttle de 100ms |
| Frame Size | ~80-150 KB | Compressão PNG |
| Bandwidth | ~0.8-1.5 Mbps | A 10 FPS |
| Latência | 150-300ms | Rede + decode |
| Max Frame Size | 2 MB | Frames maiores são ignorados |

### Documentação Completa

Para setup detalhado, troubleshooting e API reference:

📖 **[docs/MIRROR_AND_CONTROL.md](docs/MIRROR_AND_CONTROL.md)**

Inclui:
- Arquitetura do sistema e data flow
- Setup passo a passo (Docker incluído)
- Comandos de controle LLM (emotions, gestures, speaking)
- Integração avançada com OBS Studio
- Troubleshooting (conexão, FPS, frame size)
- Performance tuning (ajuste de FPS, compressão, otimizações)
- API reference completa (WebSocket messages, métodos)

---

## 🛠️ Configuração de Ambiente

Crie `.env` com as seguintes variáveis:

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `OLLAMA_HOST` | URL do servidor Ollama | `https://api.ollama.ai` |
| `OLLAMA_API_KEY` | Chave de API (fornecida) | `` |
| `LLM_MODEL` | Modelo LLM a usar | `phi3:mini` |
| `AVATAR_TYPE` | Tipo de avatar | `web` |
| `WEBSOCKET_HOST` | Host do WebSocket | `localhost` |
| `WEBSOCKET_PORT` | Porta do WebSocket | `8765` |
| `DB_PATH` | Caminho do banco de memória | `data/memory.db` |
| `PERSONA_PATH` | Caminho da persona JSON | `data/persona.json` |

### Exemplo .env

```
OLLAMA_HOST=https://api.ollama.ai
OLLAMA_API_KEY=7d5fefd71866442f848242162671602e.BscZ3cc5eQc6cx9d6-yhXhiC
LLM_MODEL=phi3:mini
AVATAR_TYPE=web
WEBSOCKET_HOST=localhost
WEBSOCKET_PORT=8765
DB_PATH=data/memory.db
PERSONA_PATH=data/persona.json
VITE_WS_URL=ws://localhost:8765
```

---

## 📁 Estrutura do Projeto

```
Mimi/
├── agent/               # Backend Python (LLM, ferramentas, estado)
│   ├── core/           # Agent core, memória, estado
│   ├── llm/            # Cliente Ollama, prompts
│   ├── tools/          # Registry de ferramentas (search, weather, etc.)
│   ├── input/          # Managers de entrada (texto, voz)
│   ├── output/         # Action router, TTS
│   └── avatar/         # Interface com avatar 3D
├── web_avatar/         # Frontend + WebSocket Server
│   ├── src/            # Componentes React + lógica
│   ├── server.js       # WebSocket hub
│   └── package.json    # Dependências Node.js
├── tests/              # Testes unitários/integração
├── docs/               # Documentação
├── .env                # Configuração (não commitado)
├── .env.example        # Template .env
└── requirements.txt    # Dependências Python
```

---

## 🔧 Desenvolvimento

### Rodar Testes

```bash
source .venv/bin/activate
pytest tests/ -v
```

### Lint & Format

```bash
ruff check agent/ --fix
ruff format agent/
```

### Build Frontend

```bash
cd web_avatar
npm run build
```

---

## 🐳 Docker (Opcional)

```bash
docker-compose up
```

Acessar em: http://localhost:5173

---

## 🚨 Troubleshooting

### "Cannot reach api.ollama.ai"
- Verifique conexão internet
- Ou configure `OLLAMA_HOST=http://localhost:11434` para instância local

### "WebSocket connection failed"
- Certifique-se que `node web_avatar/server.js` está rodando (Terminal 1)
- Verifique porta 8765 não está em uso: `lsof -i :8765`

### "Module not found: pydantic"
- Ative venv: `source .venv/bin/activate`
- Instale deps: `pip install -r requirements.txt`

---

## 📝 Licença

MIT
