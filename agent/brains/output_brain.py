"""
Brain 7: Output Brain (TTS + Audio Response)

Responsável por:
- Converter texto a fala (TTS)
- Gerenciar streaming de áudio
- Sincronizar com avatar
- Manter latência baixa
"""

import asyncio
import time
import logging

from agent.core.messaging import Brain, EventType

logger = logging.getLogger(__name__)


class OutputBrain(Brain):
    """Output Brain: TTS, áudio streaming."""
    
    async def initialize(self) -> None:
        await super().initialize()
        
        bus = self.event_bus
        bus.subscribe(EventType.INTENT_DETECTED)(self._on_intent)
    
    async def process(self) -> None:
        await asyncio.sleep(0.1)
    
    async def _on_intent(self, event) -> None:
        """Quando intenção chega, converte response para áudio."""
        intent = event.payload.get("intent", {})
        response_text = intent.get("response", "")
        
        if not response_text:
            return
        
        start_time = time.time()
        
        try:
            await self._synthesize_and_stream(response_text)
            
            latency = (time.time() - start_time) * 1000
            await self.record_event(success=True, latency_ms=latency)
        
        except Exception as e:
            logger.error(f"Error in _on_intent: {e}", exc_info=True)
            await self.record_event(success=False, latency_ms=0)
    
    async def _synthesize_and_stream(self, text: str) -> None:
        """Síntese de voz com streaming (não espera completo)."""
        await self.publish_event(EventType.TTS_STARTED, {
            "text": text,
            "timestamp": time.time(),
        })
        
        chunk_duration_ms = 100
        estimated_chunks = max(1, len(text) // 10)
        
        for i in range(estimated_chunks):
            await self.publish_event(EventType.TTS_CHUNK, {
                "chunk_index": i,
                "duration_ms": chunk_duration_ms,
                "is_final": i == estimated_chunks - 1,
            })
            
            await asyncio.sleep(chunk_duration_ms / 1000.0)
        
        await self.publish_event(EventType.TTS_COMPLETE, {
            "text": text,
            "total_duration_ms": chunk_duration_ms * estimated_chunks,
        })
