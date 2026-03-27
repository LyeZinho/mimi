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
from agent.core.messaging import Brain, EventType, get_shared_state

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
        logger.info(f"[{self.brain_id}] VAD and STT initialized")

    async def process(self) -> None:
        """Processa áudio: captura via sounddevice, VAD, STT."""
        try:
            import sounddevice as sd
        except ImportError:
            logger.warning(
                f"[{self.brain_id}] sounddevice not available, audio capture disabled"
            )
            while self._running:
                await asyncio.sleep(1.0)
            return

        logger.info(f"[{self.brain_id}] Starting audio capture loop")
        sample_rate = 16000
        frame_size = int(sample_rate * 0.02)  # 20ms frames

        try:
            stream = sd.InputStream(
                samplerate=sample_rate,
                channels=1,
                dtype="int16",
                blocksize=frame_size,
            )
            stream.start()

            while self._running:
                data, overflowed = stream.read(frame_size)
                if overflowed:
                    logger.warning("Audio buffer overflow")

                audio_bytes = data.tobytes()
                await self.handle_audio_frame(audio_bytes)

            stream.stop()
            stream.close()
        except Exception as e:
            logger.error(f"[{self.brain_id}] Audio capture error: {e}")
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
                await self.publish_event(
                    EventType.VAD_START, {"timestamp": time.time()}
                )
                await get_shared_state().set_state("listening")

            elif not vad_result and self.is_listening:
                # Fim de fala detectado
                self.is_listening = False
                await self.publish_event(EventType.VAD_END, {"timestamp": time.time()})

                # Inicia STT
                if self.current_transcript:
                    await self._run_stt(ring_snapshot)

            latency = (time.time() - start_time) * 1000
            await self.record_event(success=True, latency_ms=latency)

        except Exception as e:
            logger.error(f"Error in handle_audio_frame: {e}", exc_info=True)
            await self.record_event(success=False, latency_ms=0)

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
