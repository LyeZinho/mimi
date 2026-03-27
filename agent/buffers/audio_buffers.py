"""
Ring buffer e Chunk queue para gerenciamento de áudio em tempo real.

Ring buffer: contínuo para VAD
Chunk queue: FIFO com TTL para STT
"""

import asyncio
import time
import logging
from collections import deque
from dataclasses import dataclass
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)


@dataclass
class AudioChunk:
    """Chunk de áudio."""
    data: bytes
    sample_rate: int = 16000
    channels: int = 1
    bits_per_sample: int = 16
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
    
    def duration_ms(self) -> float:
        """Calcula duração do chunk em ms."""
        bytes_per_sample = (self.bits_per_sample // 8) * self.channels
        total_samples = len(self.data) // bytes_per_sample
        return (total_samples / self.sample_rate) * 1000


class RingBuffer:
    """
    Ring buffer para áudio contínuo.
    
    Capacidade fixa, recicla automaticamente.
    Suporta snapshot para processamento.
    """
    
    def __init__(self, capacity_bytes: int, sample_rate: int = 16000):
        self.capacity = capacity_bytes
        self.sample_rate = sample_rate
        self._buffer = bytearray(capacity_bytes)
        self._write_pos = 0
        self._read_pos = 0
        self._size = 0
        self._lock = asyncio.Lock()
    
    async def write(self, data: bytes) -> int:
        """Escreve dados ao buffer. Retorna bytes escritos."""
        async with self._lock:
            bytes_to_write = len(data)
            
            if bytes_to_write > self.capacity - self._size:
                logger.warning(
                    f"RingBuffer full: needed {bytes_to_write}, "
                    f"available {self.capacity - self._size}"
                )
                bytes_to_write = self.capacity - self._size
            
            if bytes_to_write == 0:
                return 0
            
            # Escreve em até 2 parts (wrap-around)
            part1_size = min(bytes_to_write, self.capacity - self._write_pos)
            self._buffer[self._write_pos:self._write_pos + part1_size] = data[:part1_size]
            
            if part1_size < bytes_to_write:
                part2_size = bytes_to_write - part1_size
                self._buffer[0:part2_size] = data[part1_size:]
                self._write_pos = part2_size
            else:
                self._write_pos = (self._write_pos + part1_size) % self.capacity
            
            self._size = min(self._size + bytes_to_write, self.capacity)
            return bytes_to_write
    
    async def read(self, n_bytes: int) -> bytes:
        """Lê n_bytes do buffer (destructivo)."""
        async with self._lock:
            n_bytes = min(n_bytes, self._size)
            
            if n_bytes == 0:
                return b''
            
            # Lê em até 2 parts
            part1_size = min(n_bytes, self.capacity - self._read_pos)
            data = bytes(self._buffer[self._read_pos:self._read_pos + part1_size])
            
            if part1_size < n_bytes:
                part2_size = n_bytes - part1_size
                data += bytes(self._buffer[0:part2_size])
                self._read_pos = part2_size
            else:
                self._read_pos = (self._read_pos + part1_size) % self.capacity
            
            self._size -= n_bytes
            return data
    
    async def peek(self, n_bytes: int, offset: int = 0) -> bytes:
        """Lê n_bytes sem remover (non-destructivo)."""
        async with self._lock:
            if offset + n_bytes > self._size:
                n_bytes = self._size - offset
            
            if n_bytes <= 0:
                return b''
            
            read_pos = (self._read_pos + offset) % self.capacity
            
            # Lê em até 2 parts
            part1_size = min(n_bytes, self.capacity - read_pos)
            data = bytes(self._buffer[read_pos:read_pos + part1_size])
            
            if part1_size < n_bytes:
                part2_size = n_bytes - part1_size
                data += bytes(self._buffer[0:part2_size])
            
            return data
    
    async def snapshot(self) -> bytes:
        """Retorna cópia completa do buffer."""
        async with self._lock:
            if self._size == 0:
                return b''
            
            # Copia em até 2 parts
            part1_size = self.capacity - self._read_pos
            if self._size <= part1_size:
                return bytes(self._buffer[self._read_pos:self._read_pos + self._size])
            else:
                part1 = bytes(self._buffer[self._read_pos:])
                part2 = bytes(self._buffer[0:self._size - part1_size])
                return part1 + part2
    
    async def clear(self) -> None:
        """Limpa o buffer."""
        async with self._lock:
            self._buffer = bytearray(self.capacity)
            self._write_pos = 0
            self._read_pos = 0
            self._size = 0
    
    async def get_size(self) -> int:
        """Retorna bytes no buffer."""
        async with self._lock:
            return self._size
    
    def get_duration_ms(self) -> float:
        """Retorna duração total de áudio no buffer."""
        bytes_per_sample = 2  # 16-bit mono
        total_samples = self._size / bytes_per_sample
        return (total_samples / self.sample_rate) * 1000


@dataclass
class ChunkQueueItem:
    """Item na fila de chunks."""
    chunk: AudioChunk
    created_at: float
    
    def age_ms(self) -> float:
        """Idade do item em ms."""
        return (time.time() - self.created_at) * 1000


class ChunkQueue:
    """
    Fila FIFO de chunks com TTL automático.
    
    Chunks expirados são descartados automaticamente.
    """
    
    def __init__(self, max_queue_size: int = 100, ttl_ms: float = 5000):
        self.max_size = max_queue_size
        self.ttl_ms = ttl_ms
        self._queue: deque = deque()
        self._lock = asyncio.Lock()
    
    async def put(self, chunk: AudioChunk) -> bool:
        """Adiciona chunk à fila. Retorna True se bem-sucedido."""
        async with self._lock:
            # Remove expirados
            await self._remove_expired()
            
            if len(self._queue) >= self.max_size:
                logger.warning(
                    f"ChunkQueue full ({self.max_size}), dropping oldest chunk"
                )
                self._queue.popleft()
            
            self._queue.append(ChunkQueueItem(
                chunk=chunk,
                created_at=time.time()
            ))
            return True
    
    async def get(self) -> Optional[AudioChunk]:
        """Remove e retorna primeiro chunk. Retorna None se vazio."""
        async with self._lock:
            await self._remove_expired()
            
            if len(self._queue) == 0:
                return None
            
            return self._queue.popleft().chunk
    
    async def peek(self) -> Optional[AudioChunk]:
        """Retorna primeiro chunk sem remover."""
        async with self._lock:
            await self._remove_expired()
            
            if len(self._queue) == 0:
                return None
            
            return self._queue[0].chunk
    
    async def size(self) -> int:
        """Retorna número de chunks na fila."""
        async with self._lock:
            await self._remove_expired()
            return len(self._queue)
    
    async def _remove_expired(self) -> int:
        """Remove itens expirados. Retorna quantidade removida."""
        removed = 0
        while len(self._queue) > 0:
            item = self._queue[0]
            if item.age_ms() > self.ttl_ms:
                self._queue.popleft()
                removed += 1
                logger.debug(f"Removed expired chunk (age: {item.age_ms():.0f}ms)")
            else:
                break
        return removed
    
    async def clear(self) -> None:
        """Limpa a fila."""
        async with self._lock:
            self._queue.clear()


class BufferManager:
    """
    Gerenciador que coordena RingBuffer + ChunkQueue.
    
    Fluxo:
    1. Microfone -> RingBuffer (contínuo)
    2. VAD -> snapshots do RingBuffer
    3. STT -> chunks do ChunkQueue
    """
    
    def __init__(self,
                 ring_buffer_duration_sec: float = 3.0,
                 chunk_queue_max_size: int = 100,
                 sample_rate: int = 16000):
        self.sample_rate = sample_rate
        
        # Ring buffer: 3 segundos de histórico
        bytes_per_sample = 2  # 16-bit mono
        ring_capacity = int(ring_buffer_duration_sec * sample_rate * bytes_per_sample)
        self.ring_buffer = RingBuffer(ring_capacity, sample_rate)
        
        # Chunk queue para STT
        self.chunk_queue = ChunkQueue(
            max_queue_size=chunk_queue_max_size,
            ttl_ms=5000
        )
    
    async def write_audio(self, data: bytes) -> int:
        """Escreve áudio ao ring buffer."""
        return await self.ring_buffer.write(data)
    
    async def get_ring_snapshot(self) -> bytes:
        """Retorna snapshot completo do ring buffer."""
        return await self.ring_buffer.snapshot()
    
    async def enqueue_chunk(self, chunk: AudioChunk) -> bool:
        """Enfileira chunk para STT."""
        return await self.chunk_queue.put(chunk)
    
    async def dequeue_chunk(self) -> Optional[AudioChunk]:
        """Remove e retorna chunk da fila."""
        return await self.chunk_queue.get()
    
    async def get_queue_size(self) -> int:
        """Tamanho da fila de chunks."""
        return await self.chunk_queue.size()
    
    async def get_metrics(self) -> dict:
        """Retorna métricas dos buffers."""
        return {
            "ring_buffer": {
                "capacity_bytes": self.ring_buffer.capacity,
                "used_bytes": await self.ring_buffer.get_size(),
                "duration_ms": self.ring_buffer.get_duration_ms(),
            },
            "chunk_queue": {
                "max_size": self.chunk_queue.max_size,
                "current_size": await self.chunk_queue.size(),
                "ttl_ms": self.chunk_queue.ttl_ms,
            }
        }
