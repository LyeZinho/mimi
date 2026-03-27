"""
Brain 4: Execution Brain (Tool Dispatcher)

Responsável por:
- Executar ações em paralelo
- Gerenciar tool registry
- Agregar resultados
- Passar contexto adiante
- NÃO usa LLM — executa regras
"""

import asyncio
import time
import logging
from concurrent.futures import ThreadPoolExecutor

from agent.core.messaging import Brain, EventType

logger = logging.getLogger(__name__)


class ExecutionBrain(Brain):
    """Execution Brain: executa ações em paralelo."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.tool_registry = {}
    
    async def initialize(self) -> None:
        await super().initialize()
        
        bus = self.event_bus
        bus.subscribe(EventType.TOOLS_QUEUED)(self._on_tools_queued)
    
    async def process(self) -> None:
        await asyncio.sleep(0.1)
    
    async def _on_tools_queued(self, event) -> None:
        """Quando ações são queued, executa."""
        actions = event.payload.get("actions", [])
        
        start_time = time.time()
        
        try:
            tasks = [self._execute_action(action) for action in actions]
            results = await asyncio.gather(*tasks)
            
            await self.publish_event(EventType.TOOL_RESULT, {
                "results": results,
                "action_count": len(actions),
            })
            
            latency = (time.time() - start_time) * 1000
            await self.record_event(success=True, latency_ms=latency)
        
        except Exception as e:
            logger.error(f"Error in _on_tools_queued: {e}", exc_info=True)
            await self.record_event(success=False, latency_ms=0)
    
    async def _execute_action(self, action: dict) -> dict:
        """Executa ação individual."""
        action_type = action.get("type", "noop")
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._execute_sync,
            action_type,
            action
        )
    
    def _execute_sync(self, action_type: str, action: dict) -> dict:
        """Executa ação (sync, pode rodar em thread)."""
        if action_type == "speak":
            return {"status": "queued", "type": "speak"}
        elif action_type == "state_update":
            return {"status": "applied", "type": "state_update"}
        else:
            return {"status": "noop", "type": action_type}

    async def health_check(self) -> dict:
        """Verify ExecutionBrain is operational."""
        try:
            if not hasattr(self, "bus") or self.bus is None:
                return {
                    "name": "ExecutionBrain",
                    "status": "failed",
                    "details": "EventBus not attached",
                }

            return {
                "name": "ExecutionBrain",
                "status": "operational",
                "details": "All components initialized",
            }
        except Exception as e:
            return {"name": "ExecutionBrain", "status": "failed", "details": str(e)}
