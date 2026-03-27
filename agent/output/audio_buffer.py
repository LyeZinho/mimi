"""
AudioBuffer: Ring buffer for real-time audio processing.

Implements a circular buffer with configurable capacity, handling wraparound,
fill level tracking, and playback readiness detection for streaming audio.
"""

import numpy as np
from typing import Optional


class AudioBuffer:
    """Ring buffer for real-time audio with wraparound and fill tracking."""
    
    def __init__(
        self,
        sample_rate: int = 22050,
        channels: int = 1,
        duration_sec: float = 5.0,
    ) -> None:
        """Initialize ring buffer for audio.
        
        Args:
            sample_rate: Samples per second (default 22050 Hz).
            channels: Number of channels (default 1 for mono).
            duration_sec: Buffer duration in seconds (default 5.0).
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.duration_sec = duration_sec
        
        self._buffer_size = int(sample_rate * duration_sec)
        self._buffer = np.zeros(
            (self._buffer_size, channels),
            dtype=np.float32,
        )
        self._write_pos = 0
        self._read_pos = 0
        self._total_written = 0
        self._total_read = 0
        
    async def write(self, audio_chunk: bytes) -> None:
        """Write audio chunk to ring buffer with wraparound.
        
        Converts bytes to float32 numpy array and writes to buffer,
        handling circular wraparound when write position exceeds capacity.
        
        Args:
            audio_chunk: Audio data as bytes (float32 samples).
        """
        audio_array = np.frombuffer(audio_chunk, dtype=np.float32)
        
        if len(audio_array) == 0:
            return
        
        samples_to_write = len(audio_array)
        
        space_before_wrap = self._buffer_size - self._write_pos
        
        if samples_to_write <= space_before_wrap:
            self._buffer[self._write_pos:self._write_pos + samples_to_write, 0] = audio_array
            self._write_pos = (self._write_pos + samples_to_write) % self._buffer_size
        else:
            samples_before_wrap = space_before_wrap
            samples_after_wrap = samples_to_write - samples_before_wrap
            
            self._buffer[self._write_pos:, 0] = audio_array[:samples_before_wrap]
            self._buffer[:samples_after_wrap, 0] = audio_array[samples_before_wrap:]
            
            self._write_pos = samples_after_wrap
        
        self._total_written += samples_to_write
            
    async def read(self, num_samples: int) -> np.ndarray:
        """Read audio samples from ring buffer.
        
        Reads from current read position with wraparound support.
        Updates read position after reading.
        
        Args:
            num_samples: Number of samples to read.
            
        Returns:
            Numpy array of float32 samples.
        """
        if num_samples <= 0:
            return np.array([], dtype=np.float32)
        
        result = np.zeros(num_samples, dtype=np.float32)
        
        space_before_wrap = self._buffer_size - self._read_pos
        
        if num_samples <= space_before_wrap:
            result = self._buffer[self._read_pos:self._read_pos + num_samples, 0].copy()
            self._read_pos = (self._read_pos + num_samples) % self._buffer_size
        else:
            samples_before_wrap = space_before_wrap
            samples_after_wrap = num_samples - samples_before_wrap
            
            result[:samples_before_wrap] = self._buffer[self._read_pos:, 0]
            result[samples_before_wrap:] = self._buffer[:samples_after_wrap, 0]
            
            self._read_pos = samples_after_wrap
        
        self._total_read += num_samples
        return result
        
    def get_fill_level(self) -> float:
        """Calculate current buffer fill level.
        
        Returns:
            Float between 0.0 (empty) and 1.0 (full) representing
            proportion of buffer currently containing data.
        """
        filled = self._total_written - self._total_read
        
        if filled >= self._buffer_size:
            return 1.0
        return filled / self._buffer_size
        
    def is_ready_for_playback(self, threshold: float = 0.1) -> bool:
        """Check if buffer has sufficient data for playback.
        
        Args:
            threshold: Minimum fill level (0.0-1.0) to consider ready
                      (default 0.1 = 10%).
                      
        Returns:
            True if fill level >= threshold, False otherwise.
        """
        return self.get_fill_level() >= threshold
