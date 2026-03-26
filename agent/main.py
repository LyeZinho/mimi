"""Entry point do agente Mimi."""

from __future__ import annotations

import asyncio
import logging
import sys

from agent.avatar.interface import DummyAvatar, WebAvatar
from agent.core.agent import AgentCore
from agent.core.memory import Memory
from agent.core.state import AgentState
from agent.llm.client import LLMClient
from agent.output.actions import ActionRouter
from agent.output.tts import DummyTTS
from agent.tools.registry import ToolRegistry

from agent.config import AVATAR_TYPE, DB_PATH, LLM_MODEL, WEBSOCKET_HOST, WEBSOCKET_PORT

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def create_avatar() -> DummyAvatar | WebAvatar:
    """Cria instância do avatar baseado na configuração."""
    if AVATAR_TYPE == "web":
        return WebAvatar(host=WEBSOCKET_HOST, port=WEBSOCKET_PORT)
    else:
        return DummyAvatar()


async def main() -> None:
    """Inicializa e executa o agente como daemon WebSocket."""
    print("=" * 50)
    print("  Mimi – Agente de IA Interativo Multimodal (Daemon Mode)")
    print("=" * 50)
    logger.info("Iniciando agente em modo daemon...")

    # Componentes
    # NOTE: Disabling DB persistence due to SQLite readonly issues in containerized env
    # Use in-memory memory only (short_term) for now
    memory = Memory(short_term_limit=30, db_path=None)
    state = AgentState(mood="neutral")
    llm = LLMClient(model=LLM_MODEL)
    tts = DummyTTS()
    avatar = create_avatar()
    router = ActionRouter(tts=tts, avatar=avatar)
    registry = ToolRegistry()

    agent = AgentCore(
        memory=memory,
        state=state,
        llm=llm,
        router=router,
        registry=registry,
        avatar=avatar
    )

    if isinstance(avatar, WebAvatar):
        avatar.set_agent(agent)
        logger.info("Agent configurado para WebAvatar")

    try:
        # Conecta avatar (inicia listen_loop)
        await avatar.connect()
        logger.info("Avatar conectado. Esperando mensagens...")

        # Loop infinito para manter o daemon ativo
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Interrupção recebida")
    except Exception as e:
        logger.error(f"Erro no daemon: {e}")
    finally:
        # Desconecta avatar
        await avatar.disconnect()
        await agent.shutdown()
        logger.info("Daemon encerrado")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
