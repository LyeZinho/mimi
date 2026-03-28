"""
ResponseBuffer: Ring buffer for accumulating TTS audio chunks per response.

Stores audio bytes + phoneme metadata. Supports progressive retrieval
for streaming to frontend. Thread-safe async operations.
"""

import time
import asyncio
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class BufferChunk:
    """Single chunk of audio with phoneme data."""
    audio_bytes: bytes
    phonemes: List[str]
    sample_rate: int = 22050
    timestamp: float = None
    chunk_index: int = 0
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
    
    def sample_count(self) -> int:
        """Calculate number of samples (16-bit PCM)."""
        return len(self.audio_bytes) // 2


class ResponseBuffer:
    """Ring buffer for TTS response audio chunks."""
    
    def __init__(
        self,
        sample_rate: int = 22050,
        buffer_duration_sec: float = 10.0,
    ) -> None:
        """Initialize response buffer.
        
        Args:
            sample_rate: Sample rate in Hz (default 22050)
            buffer_duration_sec: Max buffer duration in seconds (default 10)
        """
        self.sample_rate = sample_rate
        self.buffer_duration_sec = buffer_duration_sec
        self._chunks: List[BufferChunk] = []
        self._lock = asyncio.Lock()
        self._complete = False
        self._total_bytes = 0
        
    async def add_chunk(
        self,
        audio_bytes: bytes,
        phonemes: List[str],
    ) -> None:
        """Add audio chunk to buffer.
        
        Args:
            audio_bytes: Audio data (16-bit PCM bytes)
            phonemes: List of phonemes in this chunk
        """
        async with self._lock:
            chunk = BufferChunk(
                audio_bytes=audio_bytes,
                phonemes=phonemes,
                sample_rate=self.sample_rate,
                chunk_index=len(self._chunks),
            )
            self._chunks.append(chunk)
            self._total_bytes += len(audio_bytes)
    
    def get_chunks(self, start_index: int = 0) -> List[dict]:
        """Retrieve chunks starting from index.
        
        Args:
            start_index: Starting chunk index (0-based)
            
        Returns:
            List of chunk dicts with audio_bytes, phonemes, etc.
        """
        result = []
        for chunk in self._chunks[start_index:]:
            result.append({
                'audio_bytes': chunk.audio_bytes,
                'phonemes': chunk.phonemes,
                'sample_rate': chunk.sample_rate,
                'timestamp': chunk.timestamp,
                'chunk_index': chunk.chunk_index,
            })
        return result
    
    def mark_complete(self) -> None:
        """Mark buffer as complete (no more chunks incoming)."""
        self._complete = True
    
    def is_complete(self) -> bool:
        """Check if buffer is marked complete."""
        return self._complete
    
    def clear(self) -> None:
        """Clear buffer for next response."""
        self._chunks.clear()
        self._complete = False
        self._total_bytes = 0
    
    @property
    def total_chunks(self) -> int:
        """Total chunks accumulated."""
        return len(self._chunks)
    
    @property
    def total_bytes(self) -> int:
        """Total audio bytes accumulated."""
        return self._total_bytes
    
    def duration_seconds(self) -> float:
        """Calculate total audio duration in seconds."""
        if self._total_bytes == 0:
            return 0.0
        samples = self._total_bytes // 2
        return samples / self.sample_rate
