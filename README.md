# Mimi – Agente de IA Interativo Multimodal

Agente cognitivo leve, offline-first, com foco em voz e modularidade.

## � Pré-requisitos

Antes de começar, certifique-se de ter instalado:

- **Python 3.10** ou superior
- **[Ollama](https://ollama.ai/)** (para o motor de IA local)
- **Git** (para clonar o repositório)

### Opcionais (para voz/áudio)
- **FFmpeg** (geralmente necessário para processamento de áudio)
- Drivers de áudio configurados (para `sounddevice`)

## 🚀 Início rápido

```bash
# 1. Clone e entre no diretório
cd Mimi

# 2. Crie ambiente virtual e instale dependências
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# 3. Inicie o sistema (Agente + Web Avatar)
python start.py
```

O sistema iniciará:
- **Interface Web**: http://localhost:5173
- **OBS Streaming**: http://localhost:5173/obs.html
- **WebSocket Server**: ws://localhost:8765

## 🎭 Avatar 3D (Web)

O projeto agora utiliza uma solução 100% Web (Three.js + VRM), eliminando a necessidade do Unity.

1. **Abra o navegador** em http://localhost:5173
2. **Selecione um modelo VRM** (Mimi.vrm já incluso ou faça upload)
3. **Chat**: Use o microfone ou texto para conversar com o agente.

### OBS Studio Integration

1. **No OBS**, adicione uma fonte **Browser**
2. **URL**: `http://localhost:5173/obs.html`
3. **Resolução**: 1920x1080
4. **Fundo**: Transparente (já configurado, não requer Chroma Key se o browser suportar alpha, caso contrário use Color Key)

## 🛠️ Configuração

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `OLLAMA_HOST` | URL do servidor Ollama | `http://localhost:11434` |
| `LLM_MODEL` | Modelo a usar | `phi3:mini` |
| `AVATAR_TYPE` | Tipo de avatar | `web` |
| `WEBSOCKET_PORT`| Porta do WebSocket | `8765` |

## 📝 Licença

MIT
