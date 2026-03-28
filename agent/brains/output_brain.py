"""
Brain 7: Output Brain (TTS + Audio Response)

Responsável por:
- Converter texto a fala (TTS)
- Gerenciar streaming de áudio
- Sincronizar com avatar
- Manter latência baixa
"""

import asyncio
import logging
import time

from agent.core.messaging import Brain, EventType
from agent.output.tts_provider import TTSProvider

logger = logging.getLogger(__name__)


class OutputBrain(Brain):
    """Output Brain: TTS, áudio streaming."""
    
    def __init__(self, brain_id: str, event_bus, shared_state, tts_provider: TTSProvider | None):
        super().__init__(brain_id, event_bus, shared_state)
        self.tts_provider = tts_provider
        self.synthesis_latencies = []
    
    async def initialize(self) -> None:
        await super().initialize()
        self.event_bus.subscribe(EventType.RESPONSE_READY)(self._on_response_ready)
        logger.info(f"[{self.brain_id}] TTS initialized and subscribed to RESPONSE_READY")
    
    async def process(self) -> None:
        await asyncio.sleep(0.1)
    
    async def _on_response_ready(self, event) -> None:
        """Quando resposta está pronta, converte para áudio."""
        response_text = event.payload.get("response", "")
        
        if not response_text or not response_text.strip():
            logger.warning("Empty response text received")
            return
        
        start_time = time.time()
        
        try:
            await self._synthesize_and_stream(response_text)
            
            latency = (time.time() - start_time) * 1000
            self.synthesis_latencies.append(latency)
            await self.record_event(success=True, latency_ms=latency)
        
        except Exception as e:
            logger.error(f"Error in _on_response_ready: {e}", exc_info=True)
            await self.record_event(success=False, latency_ms=0)
    
    async def _synthesize_and_stream(self, text: str) -> None:
        """Síntese de voz com streaming."""
        if not self.tts_provider:
            logger.warning("TTS provider not available")
            return
        
        logger.info(f"[{self.brain_id}] Starting TTS synthesis for: {text[:50]}...")
            
        await self.publish_event(EventType.TTS_STARTED, {
            "text": text,
            "timestamp": time.time(),
        })
        
        start_synthesis = time.time()
        
        try:
            audio_chunks = []
            chunk_index = 0
            
            logger.info(f"[{self.brain_id}] Calling synthesize(stream=True)...")
            synthesize_result = self.tts_provider.synthesize(text, stream=True)
            logger.info(f"[{self.brain_id}] Got synthesize_result: {type(synthesize_result)}")
            
            async for chunk in synthesize_result:  # type: ignore
                audio_chunks.append(chunk)
                logger.debug(f"[{self.brain_id}] Got audio chunk {chunk_index}: {len(chunk)} bytes")
                
                await self.publish_event(EventType.AUDIO_CHUNK, {
                    "chunk_index": chunk_index,
                    "data": chunk,
                    "chunk_size": len(chunk),
                })
                
                chunk_index += 1
            
            logger.info(f"[{self.brain_id}] Synthesis complete: {chunk_index} chunks")
            
            # Publish phoneme data for avatar sync
            if hasattr(self.tts_provider, '_last_phonemes'):
                phonemes = self.tts_provider._last_phonemes
                sample_positions = getattr(self.tts_provider, '_last_phoneme_samples', [])
                
                if phonemes:
                    await self.publish_event(EventType.PHONEME_DATA, {
                        "text": text,
                        "phonemes": phonemes,
                        "sample_positions": sample_positions,
                        "timestamp": time.time(),
                        "sample_rate": 22050,
                    })
            
            synthesis_duration_ms = (time.time() - start_synthesis) * 1000
            full_audio = b"".join(audio_chunks)
            
            await self.publish_event(EventType.AUDIO_COMPLETE, {
                "audio": full_audio,
                "full_audio": full_audio,
                "duration_ms": synthesis_duration_ms,
                "chunk_count": chunk_index,
            })
            
            logger.info(f"Synthesized {chunk_index} chunks in {synthesis_duration_ms:.1f}ms")
        
        except Exception as e:
            logger.error(f"TTS error: {e}", exc_info=True)
            await self.publish_event(EventType.AUDIO_COMPLETE, {
                "audio": b"",
                "full_audio": b"",
                "duration_ms": 0,
                "error": str(e),
            })

    async def health_check(self) -> dict:
        """Verify OutputBrain is operational."""
        try:
            if not hasattr(self, "event_bus") or self.event_bus is None:
                return {
                    "name": "OutputBrain",
                    "status": "failed",
                    "details": "EventBus not attached",
                }

            return {
                "name": "OutputBrain",
                "status": "operational",
                "details": "All components initialized",
            }
        except Exception as e:
            return {"name": "OutputBrain", "status": "failed", "details": str(e)}
