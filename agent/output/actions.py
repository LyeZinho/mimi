"""Roteador de ações baseado em intenções."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable, Coroutine

from .tts import DummyTTS, TTSEngine

if TYPE_CHECKING:
    from agent.avatar.interface import AvatarInterface
    from agent.core.agent import AgentCore

logger = logging.getLogger(__name__)

ActionHandler = Callable[
    [dict[str, Any], "AgentCore"],
    Coroutine[Any, Any, dict[str, Any]],
]


class ActionRouter:
    """Mapeia intenções para ações concretas."""

    def __init__(self, tts: TTSEngine | None = None, avatar: "AvatarInterface" | None = None) -> None:
        self.tts = tts or DummyTTS()
        self.avatar = avatar
        self._handlers: dict[str, ActionHandler] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register("speak", self._handle_speak)
        self.register("change_state", self._handle_change_state)
        # Handler para ferramentas será chamado explicitamente, mas podemos registrar

    # ... (métodos existentes)

    async def execute_tool(
        self, tool_name: str, tool_input: str, registry: Any
    ) -> str:
        tool = registry.get_tool(tool_name)
        if not tool:
            return f"Ferramenta '{tool_name}' não disponível."
        
        logger.info("Executando ferramenta: %s com entrada: %s", tool_name, tool_input)
        try:
            return await tool.execute(tool_input)
        except Exception as e:
            logger.error("Falha na ferramenta %s: %s", tool_name, e)
            return f"Erro ao executar ferramenta: {e}"

    def register(self, intent: str, handler: ActionHandler) -> None:
        self._handlers[intent] = handler

    async def execute(
        self, intent: dict[str, Any], agent: "AgentCore"
    ) -> dict[str, Any]:
        """Executa a ação correspondente à intenção."""
        intent_type = intent.get("intent", "speak")
        handler = self._handlers.get(intent_type, self._handle_unknown)
        return await handler(intent, agent)

    # ───────────────────────── Handlers padrão ────────────────────────────
    async def _handle_speak(
        self, intent: dict[str, Any], agent: "AgentCore"
    ) -> dict[str, Any]:
        text = intent.get("text", "")
        emotion = intent.get("emotion", "neutral")
        agent.state.speaking = True
        
        # Controla avatar se disponível
        if self.avatar:
            await self.avatar.set_expression(emotion)
            await self.avatar.speak_start()
        
        await self.tts.speak(text, emotion)
        
        if self.avatar:
            await self.avatar.speak_end()
        
        agent.state.speaking = False
        return {"status": "spoken", "text": text}

    async def _handle_change_state(
        self, intent: dict[str, Any], agent: "AgentCore"
    ) -> dict[str, Any]:
        target = intent.get("target")
        value = intent.get("value")
        if target:
            agent.update_state(target, value)
            logger.info("Estado atualizado: %s = %s", target, value)
        return {"status": "state_changed", "target": target, "value": value}

    async def _handle_unknown(
        self, intent: dict[str, Any], agent: "AgentCore"
    ) -> dict[str, Any]:
        logger.warning(f"[ACTIONS] Unknown intent type: {intent.get('intent')}. Falling back to speak.")
        # Gracefully handle unknown intents by treating them as "speak" with the text content
        text = intent.get("text", str(intent))
        emotion = intent.get("emotion", "neutral")
        
        # Fall back to speak handler
        speak_intent = {
            "intent": "speak",
            "text": text,
            "emotion": emotion
        }
        return await self._handle_speak(speak_intent, agent)
