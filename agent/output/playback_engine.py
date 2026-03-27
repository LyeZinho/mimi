"""
PlaybackEngine: Real-time audio playback with sounddevice.

Handles playback of complete audio arrays and streaming from AudioBuffer,
with state management, latency tracking, and error handling.
"""

import asyncio
import time
import numpy as np
from dataclasses import dataclass
from typing import Optional

try:
    import sounddevice as sd
except ImportError:
    sd = None

from agent.output.audio_buffer import AudioBuffer


@dataclass
class PlaybackConfig:
    """Configuration for PlaybackEngine."""
    sample_rate: int = 44100
    channels: int = 1
    dtype: str = "float32"


class PlaybackEngine:
    """Real-time audio playback engine using sounddevice."""
    
    def __init__(self, config: PlaybackConfig) -> None:
        """Initialize PlaybackEngine with configuration.
        
        Args:
            config: PlaybackConfig with sample_rate, channels, dtype.
        """
        self.config = config
        self._playback_state = "idle"
        self._playback_latency_ms = 0.0
        self._current_playback_start = 0.0
    
    async def play_async(self, audio_data: np.ndarray) -> None:
        """Play complete audio array, blocking until done.
        
        Args:
            audio_data: Numpy array of float32 audio samples (mono or stereo).
            
        Raises:
            ValueError: If audio_data is empty or wrong dtype.
            RuntimeError: If sounddevice error occurs.
        """
        if len(audio_data) == 0:
            raise ValueError("Audio data cannot be empty")
        
        if audio_data.dtype != np.float32:
            raise ValueError("Audio data must be float32")
        
        if sd is None:
            raise RuntimeError("sounddevice module not available")
        
        try:
            self._playback_state = "playing"
            self._current_playback_start = time.time()
            
            sd.play(audio_data, samplerate=self.config.sample_rate)
            sd.wait()
            
            self._playback_latency_ms = (time.time() - self._current_playback_start) * 1000
            self._playback_state = "idle"
            
        except Exception as e:
            self._playback_state = "idle"
            raise RuntimeError(f"Playback error: {e}") from e
    
    async def play_streaming(
        self,
        audio_buffer: AudioBuffer,
        chunk_size: int = 4410,
    ) -> None:
        """Stream audio from AudioBuffer at playback rate.
        
        Args:
            audio_buffer: AudioBuffer to stream from.
            chunk_size: Number of samples per chunk (default 4410 = 0.1s at 44100Hz).
        """
        if sd is None:
            raise RuntimeError("sounddevice module not available")
        
        if audio_buffer.get_fill_level() == 0:
            return
        
        try:
            self._playback_state = "playing"
            self._current_playback_start = time.time()
            
            while audio_buffer.get_fill_level() > 0 and self._playback_state == "playing":
                chunk = await audio_buffer.read(chunk_size)
                
                if len(chunk) == 0:
                    break
                
                sd.play(chunk, samplerate=self.config.sample_rate)
                sd.wait()
                
                await asyncio.sleep(0.001)
            
            if self._playback_state == "playing":
                self._playback_latency_ms = (time.time() - self._current_playback_start) * 1000
                self._playback_state = "idle"
                
        except Exception as e:
            self._playback_state = "idle"
            raise RuntimeError(f"Streaming playback error: {e}") from e
    
    def pause(self) -> None:
        """Pause playback.
        
        Raises:
            RuntimeError: If not currently playing.
        """
        if self._playback_state == "idle":
            raise RuntimeError("Cannot pause from idle state")
        
        if sd is not None:
            sd.stop()
        
        self._playback_state = "paused"
    
    def resume(self) -> None:
        """Resume playback from paused state.
        
        Raises:
            RuntimeError: If not in paused state.
        """
        if self._playback_state == "idle":
            raise RuntimeError("Cannot resume from idle state")
        
        self._playback_state = "playing"
    
    def stop(self) -> None:
        """Stop playback and reset to idle state."""
        if sd is not None:
            sd.stop()
        
        self._playback_state = "idle"
    
    async def wait_until_done(self) -> None:
        """Block until current playback completes.
        
        Polls playback state and returns immediately if idle.
        """
        while self._playback_state != "idle":
            await asyncio.sleep(0.01)
    
    def get_playback_latency_ms(self) -> float:
        """Get last measured playback latency in milliseconds.
        
        Returns:
            Latency in milliseconds (0.0 if no playback yet).
        """
        return self._playback_latency_ms
