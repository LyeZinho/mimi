"""
Brain 3: Planning Brain (Action Schema + Constraint Validation)

Responsável por:
- Validar intenção detectada
- Selecionar ações a executar
- Validar constraints
- Desambiguar se necessário
- NÃO usa LLM — usa regras eficientes
"""

import asyncio
import time
import logging

from agent.core.messaging import Brain, EventType

logger = logging.getLogger(__name__)


class PlanningBrain(Brain):
    """Planning Brain: valida intent, seleciona ações (sem LLM)."""
    
    async def initialize(self) -> None:
        await super().initialize()
        
        bus = self.event_bus
        bus.subscribe(EventType.INTENT_DETECTED)(self._on_intent_detected)
    
    async def process(self) -> None:
        await asyncio.sleep(0.1)
    
    async def _on_intent_detected(self, event) -> None:
        """Quando intenção é detectada, planeja ações."""
        intent = event.payload.get("intent", {})
        
        start_time = time.time()
        
        try:
            # Valida intent
            if not self._validate_intent(intent):
                logger.warning(f"Invalid intent: {intent}")
                return
            
            # Seleciona ações (regras, não LLM)
            actions = self._select_actions(intent)
            
            await self.publish_event(EventType.TOOLS_QUEUED, {
                "actions": actions,
                "intent": intent,
            })
            
            latency = (time.time() - start_time) * 1000
            await self.record_event(success=True, latency_ms=latency)
        
        except Exception as e:
            logger.error(f"Error in _on_intent_detected: {e}", exc_info=True)
            await self.record_event(success=False, latency_ms=0)
    
    def _validate_intent(self, intent: dict) -> bool:
        """Valida estrutura de intent (sem LLM)."""
        required_fields = ["action"]
        return all(field in intent for field in required_fields)
    
    def _select_actions(self, intent: dict) -> list:
        """Seleciona ações baseado em regras (sem LLM)."""
        action = intent.get("action", "chat")
        
        # Regras simples
        if action == "chat":
            return [{"type": "speak", "target": "tts"}]
        elif action == "set_state":
            return [{"type": "state_update", "target": "avatar"}]
        else:
            return [{"type": "speak", "target": "tts"}]
