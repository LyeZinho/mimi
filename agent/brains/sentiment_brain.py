"""
Brain 5: Sentiment Brain (Emotion Detection)

Responsável por:
- Analisar sentimento do utilizador (input)
- Analisar sentimento da resposta (output)
- Detectar intenção do utilizador
- NÃO usa LLM — usa análise léxica simples
- Eficiente: economiza tokens
- Opcionalmente integra com ContextBrain para análise contextual
"""

import asyncio
import logging
from typing import Optional

from agent.core.messaging import Brain, EventType

logger = logging.getLogger(__name__)


class SentimentBrain(Brain):
    """Sentiment Brain: detecção de emoção e intenção (sem LLM)."""
    
    # Intent patterns for Portuguese
    INTENT_PATTERNS = {
        "greeting": ["olá", "oi", "e aí", "como vai", "como está", "tudo bem", "opa", "e então", "opa"],
        "farewell": ["tchau", "adeus", "até logo", "até mais", "falou", "até breve", "xau"],
        "gratitude": ["obrigada", "obrigado", "valeu", "muito obrigado", "agradeço", "thanks"],
        "apology": ["desculpa", "desculpe", "me desculpe", "sorry", "foi mal"],
        "question": ["qual", "quando", "onde", "por quê", "como", "quanto", "quem"],
        "affirmation": ["sim", "claro", "com certeza", "tá bom", "ok", "ta ok", "beleza"],
        "negation": ["não", "nunca", "jamais", "de jeito nenhum", "nada a ver"],
        "request": ["pode", "poderia", "consegue", "dá pra", "tem como", "faz um favor", "me ajuda"],
        "complaint": ["problema", "ruim", "péssimo", "horrível", "não gosto", "que raiva", "odiei"],
        "appreciation": ["legal", "ótimo", "adorei", "amei", "muito bom", "sensacional", "maravilhoso"],
    }
    
    async def initialize(self) -> None:
        await super().initialize()
        
        bus = self.event_bus
        bus.subscribe(EventType.TRANSCRIPTION_COMPLETE)(self._on_user_text)
        bus.subscribe(EventType.RESPONSE_READY)(self._on_agent_response)
    
    async def process(self) -> None:
        await asyncio.sleep(0.1)
    
    async def _on_user_text(self, event) -> None:
        """Detecta sentimento do utilizador."""
        transcript = event.payload.get("transcript", "")
        
        sentiment = self._analyze_sentiment(transcript)
        intent = self._detect_intent(transcript)
        
        await self.publish_event(EventType.SENTIMENT_UPDATED, {
            "source": "user",
            "sentiment": sentiment,
            "intent": intent,
            "text": transcript,
        })
    
    async def _on_agent_response(self, event) -> None:
        """Detecta sentimento da resposta do agente."""
        response_text = event.payload.get("response", "")
        
        sentiment = self._analyze_sentiment(response_text)
        
        await self.publish_event(EventType.EMOTION_DETECTED, {
            "source": "agent",
            "sentiment": sentiment,
            "text": response_text,
        })
    
    def _detect_intent(self, text: str) -> str:
        """Detecta intenção do utilizador baseado em padrões léxicos."""
        text_lower = text.lower()
        
        scores: dict[str, int] = {}
        for intent_type, patterns in self.INTENT_PATTERNS.items():
            score = sum(1 for pattern in patterns if pattern in text_lower)
            if score > 0:
                scores[intent_type] = score
        
        if not scores:
            return "chat"
        
        best_intent = max(scores, key=lambda x: scores[x])
        return best_intent
    
    def _analyze_sentiment(self, text: str, context: Optional[str] = None) -> str:
        """Análise léxica simples de sentimento com suporte a contexto.
        
        Args:
            text: Current user input to analyze
            context: Previous conversation context (optional)
        
        Returns:
            Sentiment label (happy, sad, neutral)
        """
        text_lower = text.lower()
        
        positive_words = ["bom", "ótimo", "feliz", "adorar", "amar", "sim", "legal"]
        negative_words = ["ruim", "péssimo", "triste", "odiar", "não", "nunca"]
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            sentiment = "happy"
        elif negative_count > positive_count:
            sentiment = "sad"
        else:
            sentiment = "neutral"
        
        if context and "INTERESTED" in context and sentiment == "neutral":
            sentiment = "happy"
        
        return sentiment

    async def health_check(self) -> dict:
        """Verify SentimentBrain is operational."""
        try:
            if not hasattr(self, "event_bus") or self.event_bus is None:
                return {
                    "name": "SentimentBrain",
                    "status": "failed",
                    "details": "EventBus not attached",
                }

            return {
                "name": "SentimentBrain",
                "status": "operational",
                "details": "All components initialized",
            }
        except Exception as e:
            return {"name": "SentimentBrain", "status": "failed", "details": str(e)}
