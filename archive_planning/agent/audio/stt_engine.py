"""STT (Speech-to-Text) engine using faster-whisper."""

import numpy as np
from faster_whisper import WhisperModel
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class STTEngine:
    """Speech-to-Text using OpenAI's Whisper (optimized faster-whisper)."""
    
    def __init__(self, model_size: str = "tiny", device: str = "cpu", language: str = "pt"):
        """
        Initialize STT engine.
        
        Args:
            model_size: "tiny", "base", "small", "medium", "large" (larger = slower but more accurate)
            device: "cpu" or "cuda" (GPU requires CUDA support)
            language: ISO-639-1 code (e.g., "pt" for Portuguese, "en" for English)
        """
        self.model_size = model_size
        self.device = device
        self.language = language
        self.model: Optional[WhisperModel] = None
        self.executor = ThreadPoolExecutor(max_workers=1)
    
    async def initialize(self):
        """Load the Whisper model (runs in thread pool to avoid blocking)."""
        def _load_model():
            logger.info(f"Loading Whisper {self.model_size} model on {self.device}...")
            return WhisperModel(self.model_size, device=self.device, compute_type="int8")
        
        self.model = await asyncio.get_event_loop().run_in_executor(
            self.executor, _load_model
        )
        logger.info("STT model loaded")
    
    async def transcribe(self, audio_bytes: bytes, sample_rate: int = 16000) -> Dict[str, Any]:
        """
        Transcribe audio to text.
        
        Args:
            audio_bytes: Raw audio bytes (16-bit PCM)
            sample_rate: Sample rate of audio (default 16000 Hz)
            
        Returns:
            {"text": str, "language": str, "confidence": float}
        """
        if not self.model:
            raise RuntimeError("STT model not initialized. Call initialize() first.")
        
        try:
            audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            
            def _transcribe():
                segments, info = self.model.transcribe(
                    audio,
                    language=self.language,
                    beam_size=5,
                    best_of=5,
                    temperature=0.0,
                    patience=1.0
                )
                text = " ".join(segment.text for segment in segments)
                confidence = getattr(info, "duration", 1.0)
                return text, info.language, confidence
            
            text, lang, conf = await asyncio.get_event_loop().run_in_executor(
                self.executor, _transcribe
            )
            
            return {
                "text": text,
                "language": lang,
                "confidence": conf
            }
        except Exception as e:
            logger.error(f"STT transcription error: {e}")
            return {"text": "", "language": self.language, "confidence": 0.0}
    
    def shutdown(self):
        """Cleanup thread pool."""
        self.executor.shutdown(wait=True)
