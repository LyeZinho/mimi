"""Configurações do agente."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env (se existir)
load_dotenv()

# Caminhos
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# LLM (Ollama)
LLM_MODEL = os.getenv("LLM_MODEL", "phi3:mini")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")  # For remote Ollama API

# Banco de dados
DB_PATH = DATA_DIR / "memory.db"
PERSONA_PATH = DATA_DIR / "persona.json"

# Avatar
# Avatar
AVATAR_TYPE = os.getenv("AVATAR_TYPE", "web")  # "dummy" or "web"

# Web Avatar
WEB_AVATAR_HOST = os.getenv("WEB_AVATAR_HOST", "localhost")
WEB_AVATAR_PORT = int(os.getenv("WEB_AVATAR_PORT", "8000"))
WEBSOCKET_CONNECT_HOST = os.getenv("WEBSOCKET_CONNECT_HOST", "localhost")
WEBSOCKET_PORT = int(os.getenv("WEBSOCKET_PORT", "8765"))
