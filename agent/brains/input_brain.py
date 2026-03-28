"""
Brain 1: Input Brain (VAD + STT)

Responsável por:
- Capturar áudio do microfone
- Detecção de atividade de voz (VAD)
- Conversão de voz para texto (STT)
- Enfileirar chunks para processamento
"""

import asyncio
import logging
import time

from agent.audio import STTEngine, VADEngine
from agent.buffers import AudioChunk, BufferManager
from agent.core.messaging import Brain, EventType, get_event_bus, get_shared_state
from agent.core.messaging.shared_state import UserContextState

logger = logging.getLogger(__name__)


class InputBrain(Brain):
    """Input Brain: captura áudio, VAD, STT."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.buffer_manager = BufferManager()
        self.vad_engine = VADEngine(aggressiveness=2, sample_rate=16000)
        self.stt_engine = STTEngine(model_size="tiny", device="cpu", language="pt")
        self.is_listening = False
        self.current_transcript = ""
        self.silence_frames = 0
        self.silence_threshold = 10

    async def initialize(self) -> None:
        await super().initialize()
        await self.stt_engine.initialize()
        
        bus = get_event_bus()
        bus.subscribe(EventType.AUDIO_CHUNK)(self._on_audio_chunk_received)
        
        logger.info(f"[{self.brain_id}] VAD and STT initialized, subscribed to AUDIO_CHUNK events")

    async def process(self) -> None:
        """Voice-only architecture: audio comes via WebSocket, not sounddevice."""
        logger.info(f"[{self.brain_id}] Voice-only mode: listening for AUDIO_CHUNK events from WebSocket")
        while self._running:
            await asyncio.sleep(1.0)

    async def handle_audio_frame(self, data: bytes) -> None:
        """
        Callback: novo frame de áudio chegou.

        Fluxo:
        1. Escreve ao ring buffer
        2. VAD: detecta se há voz
        3. STT: converte voz a texto
        4. Publica event
        """
        await self.buffer_manager.write_audio(data)

        # Publish audio chunk event
        chunk = AudioChunk(data=data, sample_rate=16000)
        await self.publish_event(
            EventType.AUDIO_CHUNK,
            {
                "chunk_duration_ms": chunk.duration_ms(),
                "buffer_size_ms": self.buffer_manager.ring_buffer.get_duration_ms(),
            },
        )

        start_time = time.time()

        try:
            # VAD: detecta inicio/fim de voz
            ring_snapshot = await self.buffer_manager.get_ring_snapshot()
            vad_result = self._run_vad(ring_snapshot)

            if vad_result and not self.is_listening:
                # Início de fala detectado
                self.is_listening = True
                logger.info(f"[{self.brain_id}] VAD: Speech detected, starting recording")
                await self.publish_event(
                    EventType.VAD_START, {"timestamp": time.time()}
                )
                await get_shared_state().set_state(UserContextState.LISTENING)

            elif not vad_result and self.is_listening:
                # Fim de fala detectado
                self.is_listening = False
                logger.info(f"[{self.brain_id}] VAD: Speech ended, running STT")
                await self.publish_event(EventType.VAD_END, {"timestamp": time.time()})

                await self._run_stt(ring_snapshot)

            latency = (time.time() - start_time) * 1000
            await self.record_event(success=True, latency_ms=latency)

        except Exception as e:
            logger.error(f"Error in handle_audio_frame: {e}", exc_info=True)
            await self.record_event(success=False, latency_ms=0)

    async def _on_audio_chunk_received(self, event) -> None:
        """Handler for AUDIO_CHUNK events from WebSocket bridge (browser microphone)."""
        try:
            audio_bytes = event.payload.get("audio_bytes", b"")
            sample_rate = event.payload.get("sample_rate", 16000)
            
            if not audio_bytes:
                return
            
            logger.debug(f"[{self.brain_id}] Received audio chunk: {len(audio_bytes)} bytes @ {sample_rate}Hz")
            await self.handle_audio_frame(audio_bytes)
        except Exception as e:
            logger.error(f"Error processing audio chunk from bridge: {e}", exc_info=True)

    def _run_vad(self, audio_data: bytes) -> bool:
        """Executa VAD com webrtcvad."""
        is_speech = self.vad_engine.is_speech(audio_data)

        if is_speech:
            self.silence_frames = 0
        else:
            self.silence_frames += 1

        return self.silence_frames < self.silence_threshold

    async def _run_stt(self, audio_data: bytes) -> None:
        """Executa STT com faster-whisper."""
        await self.publish_event(
            EventType.TRANSCRIPTION_START, {"audio_size": len(audio_data)}
        )

        try:
            result = await self.stt_engine.transcribe(audio_data, sample_rate=16000)
            self.current_transcript = result["text"]
            confidence = result["confidence"]

            await self.publish_event(
                EventType.TRANSCRIPTION_COMPLETE,
                {
                    "transcript": self.current_transcript,
                    "confidence": confidence,
                    "language": result["language"],
                },
            )
        except Exception as e:
            logger.error(f"STT error: {e}")
            await self.publish_event(
                EventType.TRANSCRIPTION_COMPLETE,
                {"transcript": "", "confidence": 0.0, "error": str(e)},
            )
        finally:
            self.current_transcript = ""

    async def health_check(self) -> dict:
        """Verify InputBrain is operational."""
        try:
            if self.vad_engine is None:
                return {
                    "name": "InputBrain",
                    "status": "failed",
                    "details": "VAD engine not initialized",
                }

            if self.stt_engine is None:
                return {
                    "name": "InputBrain",
                    "status": "failed",
                    "details": "STT engine not initialized",
                }

            if self.buffer_manager is None:
                return {
                    "name": "InputBrain",
                    "status": "failed",
                    "details": "Buffer manager not initialized",
                }

            if not hasattr(self, "event_bus") or self.event_bus is None:
                return {
                    "name": "InputBrain",
                    "status": "failed",
                    "details": "EventBus not attached",
                }

            return {
                "name": "InputBrain",
                "status": "operational",
                "details": "All components initialized",
            }
        except Exception as e:
            return {"name": "InputBrain", "status": "failed", "details": str(e)}
