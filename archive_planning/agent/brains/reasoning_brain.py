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
    
    def __init__(self, llm_provider: Optional[LLMProvider] = None, context_brain=None, user_profile_brain=None, **kwargs):
        super().__init__(**kwargs)
        self.llm_provider = llm_provider
        self.context_brain = context_brain
        self.user_profile_brain = user_profile_brain
    
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
            
            intent = await self._extract_intent(transcript)
            logger.info(f"[{self.brain_id}] Extracted intent: {intent}")
            
            await self.publish_event(EventType.INTENT_DETECTED, {
                "intent": intent,
                "transcript": transcript,
                "confidence": intent.get("confidence", 0.5),
            })
            
            response_text = await self._generate_response(transcript, intent)
            logger.info(f"[{self.brain_id}] Generated response: {response_text[:100]}")
            
            await self.publish_event(EventType.RESPONSE_READY, {
                "response": response_text,
                "intent": intent,
            })
            
            latency = (time.time() - start_time) * 1000
            await self.record_event(success=True, latency_ms=latency)
        
        except Exception as e:
            logger.error(f"Error in _on_transcription_complete: {e}", exc_info=True)
            await self.record_event(success=False, latency_ms=0)
    
    async def _extract_intent(self, transcript: str) -> dict:
        """Extract intent from transcript."""
        if not self.llm_provider:
            return {
                "intent": "greeting" if any(w in transcript.lower() for w in ["olá", "oi", "ola"]) else "chat",
                "confidence": 0.5,
            }
        
        try:
            prompt = PromptTemplates.intent_extraction(transcript)
            response = await self.llm_provider.generate(prompt, stream=False)
            
            if not response:
                return {"intent": "chat", "confidence": 0.3}
            
            parsed = json.loads(response)
            return {
                "intent": parsed.get("intent", "chat"),
                "confidence": float(parsed.get("confidence", 0.5)),
                "sentiment": parsed.get("sentiment", "neutral"),
            }
        except (json.JSONDecodeError, LLMProviderError) as e:
            logger.warning(f"Failed to extract intent: {e}, using fallback")
            return {"intent": "chat", "confidence": 0.3}
    
    async def _generate_response(self, transcript: str, intent: dict) -> str:
        """Generate response based on transcript and intent."""
        if not self.llm_provider:
            return f"Echo: {transcript}"
        
        try:
            context_data = None
            if self.context_brain:
                context_str = self.context_brain.build_llm_context()
                if context_str:
                    context_data = {"conversation_history": context_str}
            
            user_profile_summary = None
            if self.user_profile_brain:
                try:
                    profile = self.user_profile_brain.get_profile()
                    if profile and profile.confidence > 0.3:
                        user_profile_summary = f"""
[User Profile]
- Dominant mood: {profile.personality.dominant_mood}
- Interests: {', '.join([t[0] for t in profile.interests.primary_topics[:3]])}
- Communication style: {profile.communication.primary_intent}
- Preferred support: {profile.support_needs.validation_preference.value}
"""
                except Exception as e:
                    logger.debug(f"Could not include user profile: {e}")
            
            prompt = PromptTemplates.response_generation_simple(
                transcript,
                intent.get("intent", "chat"),
                context=context_data,
                user_profile=user_profile_summary,
            )
            response = await self.llm_provider.generate(prompt, stream=False)
            
            if not response:
                return f"Echo: {transcript}"
            
            return response.strip()
        except LLMProviderError as e:
            logger.warning(f"Failed to generate response: {e}, using fallback")
            return f"Echo: {transcript}"

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
