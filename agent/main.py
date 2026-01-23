"""Entry point do agente Mimi."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from agent.avatar.interface import DummyAvatar, WebAvatar
from agent.core.agent import AgentCore
from agent.core.memory import Memory
from agent.core.state import AgentState
from agent.input.manager import InputManager
from agent.input.text import TextInput
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
    """Inicializa e executa o agente."""
    print("=" * 50)
    print("  Mimi – Agente de IA Interativo Multimodal")
    print("=" * 50)
    print("Digite sua mensagem (ou 'sair' para encerrar).\n")

    # Componentes
    memory = Memory(short_term_limit=30, db_path=DB_PATH)
    state = AgentState(mood="neutral")
    llm = LLMClient(model=LLM_MODEL)
    tts = DummyTTS()
    avatar = create_avatar()
    router = ActionRouter(tts=tts, avatar=avatar)
    registry = ToolRegistry() # Nova dependência
    
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

    # Input via texto
    input_manager = InputManager()
    text_input = TextInput(input_manager)

    # Handler para processar eventos
    async def on_input(event):
        await agent.handle_input(event.content, source=event.source)

    input_manager.register_handler(on_input)

    # Conecta avatar
    await avatar.connect()

    # Loop principal
    try:
        await text_input.run(prompt="Você: ")
    except KeyboardInterrupt:
        pass
    finally:
        # Desconecta avatar
        await avatar.disconnect()
        await agent.shutdown()
        print("\nAté logo! 👋")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
