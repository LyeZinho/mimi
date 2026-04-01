"""Real-time audio capture from microphone using sounddevice."""

import sounddevice as sd
import numpy as np
import asyncio
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class AudioCapture:
    """Real-time microphone audio capture with async callbacks."""
    
    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 1024,
        callback: Optional[Callable[[bytes], None]] = None
    ):
        """
        Initialize audio capture.
        
        Args:
            sample_rate: Sample rate in Hz (default 16000)
            channels: Number of audio channels (default 1 = mono)
            chunk_size: Number of samples per chunk (default 1024)
            callback: Function to call on each audio chunk
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.callback = callback
        self.stream = None
        self.is_running = False
    
    def set_callback(self, callback: Callable[[bytes], None]):
        """Set or update the audio callback function."""
        self.callback = callback
    
    async def start(self):
        """Start microphone capture."""
        if self.is_running:
            logger.warning("Audio capture already running")
            return
        
        def audio_callback(indata, frames, time_info, status):
            if status:
                logger.warning(f"Audio status: {status}")
            
            if self.callback:
                audio_bytes = indata.tobytes()
                asyncio.create_task(self._handle_chunk(audio_bytes))
        
        try:
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                blocksize=self.chunk_size,
                callback=audio_callback,
                dtype=np.int16,
                latency='low'
            )
            self.stream.start()
            self.is_running = True
            logger.info(f"Audio capture started: {self.sample_rate}Hz, {self.channels}ch")
        except Exception as e:
            logger.error(f"Failed to start audio capture: {e}")
            raise
    
    async def stop(self):
        """Stop microphone capture."""
        if not self.is_running:
            return
        
        try:
            if self.stream:
                self.stream.stop()
                self.stream.close()
            self.is_running = False
            logger.info("Audio capture stopped")
        except Exception as e:
            logger.error(f"Error stopping audio capture: {e}")
    
    async def _handle_chunk(self, audio_bytes: bytes):
        """Handle audio chunk (for async callback support)."""
        try:
            if self.callback and callable(self.callback):
                result = self.callback(audio_bytes)
                if hasattr(result, '__await__'):
                    await result
        except Exception as e:
            logger.error(f"Error in audio callback: {e}")
