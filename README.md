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

Use o script de inicialização:

```bash
# Linux/Mac
./start_dev.sh

# Windows
start_dev.bat
```

Isso mostrará os 3 comandos para abrir em terminais separados.

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
