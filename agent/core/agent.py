"""Orquestrador principal do agente."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from .memory import Memory
from .state import AgentState

if TYPE_CHECKING:
    from agent.avatar.interface import AvatarInterface
    from agent.llm.client import LLMClient
    from agent.output.actions import ActionRouter

logger = logging.getLogger(__name__)


class AgentCore:
    """Núcleo cognitivo: gerencia estado, memória e fluxo de decisão."""

    def __init__(
        self,
        memory: Memory | None = None,
        state: AgentState | None = None,
        llm: "LLMClient" | None = None,
        router: "ActionRouter" | None = None,
        registry: "ToolRegistry" | None = None,  # ToolRegistry
        avatar: "AvatarInterface" | None = None,
    ) -> None:
        self.memory = memory if memory is not None else Memory()
        self.state = state if state is not None else AgentState()
        # Assuming LLMClient and ActionRouter can be instantiated without args if None
        # If they require args, this needs adjustment or they must be provided.
        self.llm = llm or LLMClient()
        self.router = router or ActionRouter()
        self.registry = registry
        self.avatar = avatar
        self._running = False

    # ─────────────────────────── Ciclo principal ──────────────────────────
    async def handle_input(self, text: str, source: str = "text") -> dict[str, Any]:
        """Processa entrada do usuário e gera resposta (com suporte a loops de ferramentas)."""
        logger.info("Entrada recebida [%s]: %s", source, text)
        self.memory.add(content=text, role="user", metadata={"source": source})

        # Limite de segurança para evitar loops infinitos
        MAX_TURNS = 3
        current_turn = 0
        
        while current_turn < MAX_TURNS:
            current_turn += 1
            
            # 1. Recupera contexto e monta input
            history = [m.to_dict() for m in self.memory.recent(10)]
            state_summary = self.state.summary()
            
            relevant_memories = [m.to_dict() for m in self.memory.search_long_term(text, limit=3)]
            if relevant_memories:
                logger.info("Memórias relevantes encontradas: %d", len(relevant_memories))

            tools_list = self.registry.list_tools() if self.registry else None

            # 2. Chama LLM
            try:
                intent = await self.llm.get_intent(
                    user_message=text if current_turn == 1 else "(continuando pensamento...)", # No loop, o prompt é reconstruído com histórico atualizado
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

            # 3. Verifica se é uso de ferramenta
            if intent.get("intent") == "use_tool" and self.registry:
                tool_name = intent.get("tool")
                tool_input = intent.get("tool_input")
                
                # Registra intenção de usar ferramenta (opcional, ou apenas o resultado)
                # self.memory.add(content=f"Vou usar {tool_name} para buscar '{tool_input}'", role="assistant")

                result_text = await self.router.execute_tool(tool_name, tool_input, self.registry)
                
                # Adiciona resultado ao histórico como 'system' para o LLM processar na próxima iteração
                self.memory.add(content=f"Resultado da ferramenta {tool_name}: {result_text}", role="system")
                continue # Volta para o início do loop para gerar a resposta final com o novo contexto
            
            # 4. Se não for ferramenta, executa ação final (speak/action)
            result = await self.router.execute(intent, agent=self)
            
            if "text" in intent:
                self.memory.add(content=intent["text"], role="assistant")
            
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
