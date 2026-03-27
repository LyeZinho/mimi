"""
Brain 2: Reasoning Brain (LLM Inference)

Responsável por:
- Processar texto transcrito
- Invocar LLM para gerar intenção
- Construir contexto
- Streaming de resposta
"""

import asyncio
import time
import logging
import json
from typing import Optional

from agent.core.messaging import Brain, EventType, get_event_bus, get_shared_state
from agent.llm.provider import LLMProvider
from agent.llm.errors import LLMProviderError
from agent.llm.prompt_templates import PromptTemplates

logger = logging.getLogger(__name__)


class ReasoningBrain(Brain):
    """Reasoning Brain: LLM inference, contexto, intenção."""
    
    def __init__(self, llm_provider: Optional[LLMProvider] = None, **kwargs):
        super().__init__(**kwargs)
        self.llm_provider = llm_provider
    
    async def initialize(self) -> None:
        await super().initialize()
        
        if self.llm_provider:
            logger.info(f"[{self.brain_id}] Initialized with LLM provider: {self.llm_provider.__class__.__name__}")
        else:
            logger.info(f"[{self.brain_id}] No LLM provider configured, using fallback responses")
        
        # Subscribe a text chunks
        bus = get_event_bus()
        bus.subscribe(EventType.TRANSCRIPTION_COMPLETE)(self._on_transcription_complete)
    
    async def process(self) -> None:
        """Processa eventos de contexto e intenção."""
        await asyncio.sleep(0.1)
    
    async def _on_transcription_complete(self, event) -> None:
        """Quando transcrição termina, inicia LLM."""
        transcript = event.payload.get("transcript", "")
        
        if not transcript:
            return
        
        start_time = time.time()
        
        try:
            state = get_shared_state()
            context_snapshot = await state.get_context_snapshot()
            
            # TODO: invocar LLM com transcript + contexto
            # TODO: fazer streaming da resposta
            intent = await self._infer_intent(transcript, context_snapshot)
            
            await self.publish_event(EventType.INTENT_DETECTED, {
                "intent": intent,
                "transcript": transcript,
                "confidence": 0.92,
            })
            
            # Emit RESPONSE_READY with the generated response text
            response_text = intent.get("response", f"Echo: {transcript}")
            await self.publish_event(EventType.RESPONSE_READY, {
                "response": response_text,
                "intent": intent,
            })
            
            latency = (time.time() - start_time) * 1000
            await self.record_event(success=True, latency_ms=latency)
        
        except Exception as e:
            logger.error(f"Error in _on_transcription_complete: {e}", exc_info=True)
            await self.record_event(success=False, latency_ms=0)
    
    async def _infer_intent(self, transcript: str, context) -> dict:
        """Invoca LLM para extrair intenção ou usa fallback."""
        if not self.llm_provider:
            return {
                "action": "chat",
                "response": f"Echo: {transcript}",
                "sentiment": "neutral",
            }
        
        try:
            prompt = PromptTemplates.intent_extraction(transcript, context)
            response = await self.llm_provider.generate(prompt, stream=False)
            
            parsed = json.loads(response)
            return {
                "action": "chat",
                "response": f"Intent: {parsed.get('intent', 'unknown')}",
                "sentiment": parsed.get("sentiment", "neutral"),
                "confidence": parsed.get("confidence", 0.0),
                "intent": parsed.get("intent"),
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}", exc_info=True)
            return {
                "action": "chat",
                "response": f"Echo: {transcript}",
                "sentiment": "neutral",
            }
        except LLMProviderError as e:
            logger.error(f"LLM provider error: {e}", exc_info=True)
            raise

    async def health_check(self) -> dict:
        """Verify ReasoningBrain is operational."""
        try:
            if self.llm_provider is None:
                return {
                    "name": "ReasoningBrain",
                    "status": "failed",
                    "details": "LLM provider not initialized",
                }

            if not hasattr(self, "event_bus") or self.event_bus is None:
                return {
                    "name": "ReasoningBrain",
                    "status": "failed",
                    "details": "EventBus not attached",
                }

            return {
                "name": "ReasoningBrain",
                "status": "operational",
                "details": "LLM provider initialized",
            }
        except Exception as e:
            return {"name": "ReasoningBrain", "status": "failed", "details": str(e)}
