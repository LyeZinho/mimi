"""
Brain 5: Sentiment Brain (Emotion Detection)

Responsável por:
- Analisar sentimento do utilizador (input)
- Analisar sentimento da resposta (output)
- NÃO usa LLM — usa análise léxica simples
- Eficiente: economiza tokens
"""

import asyncio
import logging

from agent.core.messaging import Brain, EventType

logger = logging.getLogger(__name__)


class SentimentBrain(Brain):
    """Sentiment Brain: detecção de emoção (sem LLM)."""
    
    async def initialize(self) -> None:
        await super().initialize()
        
        bus = self.event_bus
        bus.subscribe(EventType.TRANSCRIPTION_COMPLETE)(self._on_user_text)
        bus.subscribe(EventType.INTENT_DETECTED)(self._on_agent_response)
    
    async def process(self) -> None:
        await asyncio.sleep(0.1)
    
    async def _on_user_text(self, event) -> None:
        """Detecta sentimento do utilizador."""
        transcript = event.payload.get("transcript", "")
        
        sentiment = self._analyze_sentiment(transcript)
        
        await self.publish_event(EventType.SENTIMENT_UPDATED, {
            "source": "user",
            "sentiment": sentiment,
            "text": transcript,
        })
    
    async def _on_agent_response(self, event) -> None:
        """Detecta sentimento da resposta do agente."""
        intent = event.payload.get("intent", {})
        response = intent.get("response", "")
        
        sentiment = self._analyze_sentiment(response)
        
        await self.publish_event(EventType.EMOTION_DETECTED, {
            "source": "agent",
            "sentiment": sentiment,
            "text": response,
        })
    
    def _analyze_sentiment(self, text: str) -> str:
        """Análise léxica simples de sentimento."""
        text_lower = text.lower()
        
        positive_words = ["bom", "ótimo", "feliz", "adorar", "amar", "sim", "legal"]
        negative_words = ["ruim", "péssimo", "triste", "odiar", "não", "nunca"]
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return "happy"
        elif negative_count > positive_count:
            return "sad"
        else:
            return "neutral"
