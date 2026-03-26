"""Orquestrador principal do agente."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Union

from .memory import Memory
from .state import AgentState
from .response_cache import ResponseCache

if TYPE_CHECKING:
    from agent.avatar.interface import AvatarInterface
    from agent.llm.client import LLMClient
    from agent.output.actions import ActionRouter

logger = logging.getLogger(__name__)


class AgentCore:
    """Núcleo cognitivo: gerencia estado, memória e fluxo de decisão."""

    def __init__(
        self,
        memory: Union[Memory, None] = None,
        state: Union[AgentState, None] = None,
        llm: Union["LLMClient", None] = None,
        router: Union["ActionRouter", None] = None,
        registry: Any = None,
        avatar: Union["AvatarInterface", None] = None,
        cache: Union[ResponseCache, None] = None,
    ) -> None:
        self.memory = memory if memory is not None else Memory()
        self.state = state if state is not None else AgentState()
        self.llm = llm or LLMClient()
        self.router = router or ActionRouter()
        self.registry = registry
        self.avatar = avatar
        self.cache = cache or ResponseCache()
        self._running = False

    # ─────────────────────────── Ciclo principal ──────────────────────────
    async def handle_input(self, text: str, source: str = "text") -> dict[str, Any]:
        """Processa entrada do usuário e gera resposta (com suporte a loops de ferramentas e cache)."""
        logger.info("Entrada recebida [%s]: %s", source, text)
        self.memory.add(content=text, role="user", metadata={"source": source})

        cache_key = ResponseCache.get_cache_key(text)
        
        if cached_response := self.cache.get(cache_key):
            logger.info("Cache hit para: %s", text[:50])
            self.memory.add(content=cached_response.get("text", ""), role="assistant")
            return cached_response

        MAX_TURNS = 3
        current_turn = 0
        
        while current_turn < MAX_TURNS:
            current_turn += 1
            
            history = [m.to_dict() for m in self.memory.recent(10)]
            state_summary = self.state.summary()
            
            relevant_memories = [m.to_dict() for m in self.memory.search_long_term(text, limit=3)]
            if relevant_memories:
                logger.info("Memórias relevantes encontradas: %d", len(relevant_memories))

            tools_list = self.registry.list_tools() if self.registry else None

            try:
                intent = await self.llm.get_intent(
                    user_message=text if current_turn == 1 else "(continuando pensamento...)",
                    history=history,
                    state=state_summary,
                    context=relevant_memories,
                    tools=tools_list,
                )
                logger.info(f"[AGENT] Intent received: {intent}")
            except Exception as e:
                logger.error(f"[AGENT] LLM error on turn {current_turn}: {e}", exc_info=True)
                return {"status": "error", "error": str(e)}
            
            logger.debug("Intenção recebida: %s", intent)

            if intent.get("intent") == "use_tool" and self.registry:
                tool_name = intent.get("tool", "")
                tool_input = intent.get("tool_input", "")
                
                if tool_name and tool_input:
                    result_text = await self.router.execute_tool(tool_name, tool_input, self.registry)
                    
                    self.memory.add(content=f"Resultado da ferramenta {tool_name}: {result_text}", role="system")
                continue
            
            result = await self.router.execute(intent, agent=self)
            
            if "text" in intent:
                self.memory.add(content=intent["text"], role="assistant")
            
            self.cache.set(cache_key, result)
            self.cache.flush()
            
            return result
        
        return {"status": "loop_limit_reached"}

    # ─────────────────────────── Helpers ──────────────────────────────────
    def update_state(self, key: str, value: Any) -> None:
        self.state.set(key, value)

    async def run_loop(self, input_queue: asyncio.Queue[str]) -> None:
        """Loop contínuo para processar entradas de uma fila async."""
        self._running = True
        while self._running:
            text = await input_queue.get()
            if text.lower() in {"sair", "exit", "quit"}:
                self._running = False
                break
            await self.handle_input(text)

    async def shutdown(self) -> None:
        """Encerra componentes e libera recursos."""
        self._running = False
        if hasattr(self.llm, "close"):
            await self.llm.close()

    def stop(self) -> None:
        self._running = False
