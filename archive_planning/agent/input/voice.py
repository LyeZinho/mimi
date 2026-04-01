"""Pipeline de voz: VAD + STT."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from .manager import InputManager

logger = logging.getLogger(__name__)


class STTEngine(Protocol):
    """Interface para motores de Speech-to-Text."""

    def transcribe(self, audio: bytes) -> str:
        ...


class VoiceInput:
    """Captura de voz com VAD e transcrição STT.

    Nota: implementação simplificada; requer bibliotecas como
    sounddevice, webrtcvad e faster-whisper.
    """

    def __init__(
        self,
        manager: "InputManager",
        stt_engine: STTEngine | None = None,
        sample_rate: int = 16000,
        chunk_duration_ms: int = 30,
    ) -> None:
        self.manager = manager
        self.stt = stt_engine
        self.sample_rate = sample_rate
        self.chunk_duration_ms = chunk_duration_ms
        self._running = False

    async def run(self) -> None:
        """Loop principal de captura de áudio (placeholder)."""
        if self.stt is None:
            logger.warning("STT engine não configurado; VoiceInput desativado.")
            return

        self._running = True
        logger.info("VoiceInput iniciado (sample_rate=%d)", self.sample_rate)

        # Placeholder: integração real requer sounddevice + VAD
        while self._running:
            await asyncio.sleep(0.1)
            # Quando houver áudio:
            # audio_chunk = capture()
            # if vad.is_speech(audio_chunk):
            #     text = self.stt.transcribe(audio_chunk)
            #     await self.manager.push(text, source="voice")

    def stop(self) -> None:
        self._running = False
