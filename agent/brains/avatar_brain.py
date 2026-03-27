"""
Brain 6: Avatar Brain (3D Model Control)

Responsável por:
- Controlar animações do modelo 3D
- Aplicar gestos e expressões faciais
- Sincronizar com TTS (lip-sync)
- NÃO usa LLM — usa mappings de regras
"""

import asyncio
import logging

from agent.core.messaging import Brain, EventType

logger = logging.getLogger(__name__)


class AvatarBrain(Brain):
    """Avatar Brain: controla modelo 3D (sem LLM)."""
    
    async def initialize(self) -> None:
        await super().initialize()
        
        bus = self.event_bus
        bus.subscribe(EventType.EMOTION_DETECTED)(self._on_emotion)
        bus.subscribe(EventType.TTS_STARTED)(self._on_tts_start)
        bus.subscribe(EventType.TTS_COMPLETE)(self._on_tts_end)
    
    async def process(self) -> None:
        await asyncio.sleep(0.1)
    
    async def _on_emotion(self, event) -> None:
        """Quando emoção é detectada, muda expressão do avatar."""
        sentiment = event.payload.get("sentiment", "neutral")
        
        animation = self._emotion_to_animation(sentiment)
        
        await self.publish_event(EventType.ANIMATION_QUEUED, {
            "animation": animation,
            "sentiment": sentiment,
        })
    
    async def _on_tts_start(self, event) -> None:
        """Quando TTS começa, inicia lip-sync."""
        await self.publish_event(EventType.GESTURE_QUEUED, {
            "gesture": "speaking",
            "intensity": 0.5,
        })
    
    async def _on_tts_end(self, event) -> None:
        """Quando TTS termina, para lip-sync."""
        await self.publish_event(EventType.GESTURE_QUEUED, {
            "gesture": "idle",
            "intensity": 0.0,
        })
    
    def _emotion_to_animation(self, sentiment: str) -> str:
        """Mapeia sentimento a animação de expressão."""
        emotion_map = {
            "happy": "smile",
            "sad": "frown",
            "neutral": "neutral",
            "angry": "angry_face",
            "surprised": "surprised_face",
        }
        return emotion_map.get(sentiment, "neutral")

    async def health_check(self) -> dict:
        """Verify AvatarBrain is operational."""
        try:
            if not hasattr(self, "avatar") or self.avatar is None:
                return {
                    "name": "AvatarBrain",
                    "status": "failed",
                    "details": "Avatar interface not attached",
                }

            if not hasattr(self, "bus") or self.bus is None:
                return {
                    "name": "AvatarBrain",
                    "status": "failed",
                    "details": "EventBus not attached",
                }

            return {
                "name": "AvatarBrain",
                "status": "operational",
                "details": "All components initialized",
            }
        except Exception as e:
            return {"name": "AvatarBrain", "status": "failed", "details": str(e)}
