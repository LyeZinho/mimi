"""
Base class para todos os Brains.

Define interface comum, lifecycle, health monitoring.
"""

import asyncio
import time
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass

from .event_bus import EventBus, EventType, AgentEvent
from .shared_state import SharedAgentState, BrainHealth

logger = logging.getLogger(__name__)


class BrainState(str, Enum):
    """Estados do brain."""
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class BrainMetrics:
    """Métricas de um brain."""
    events_processed: int = 0
    events_failed: int = 0
    total_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    min_latency_ms: float = float('inf')


class Brain(ABC):
    """
    Base abstrata para todos os brains.
    
    Define lifecycle: init -> start -> run -> stop -> shutdown
    """
    
    def __init__(self,
                 brain_id: str,
                 event_bus: EventBus,
                 shared_state: SharedAgentState):
        self.brain_id = brain_id
        self.event_bus = event_bus
        self.shared_state = shared_state
        
        self.state = BrainState.INITIALIZING
        self.metrics = BrainMetrics()
        
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_heartbeat = time.time()
        self._heartbeat_interval = 1.0  # segundos
    
    # ===== LIFECYCLE =====
    
    async def initialize(self) -> None:
        """Inicializa o brain (setup de conexões, modelos, etc)."""
        logger.info(f"[{self.brain_id}] Initializing...")
        await self.shared_state.register_brain(self.brain_id)
        self.state = BrainState.READY
    
    async def start(self) -> None:
        """Inicia o processamento do brain."""
        if self._running:
            logger.warning(f"[{self.brain_id}] Already running")
            return
        
        logger.info(f"[{self.brain_id}] Starting...")
        self._running = True
        self.state = BrainState.RUNNING
        self._task = asyncio.create_task(self._run_loop())
    
    async def pause(self) -> None:
        """Pausa o brain temporariamente."""
        self.state = BrainState.PAUSED
        self._running = False
        logger.info(f"[{self.brain_id}] Paused")
    
    async def resume(self) -> None:
        """Resume o brain após pausa."""
        if self.state == BrainState.PAUSED:
            self._running = True
            self.state = BrainState.RUNNING
            logger.info(f"[{self.brain_id}] Resumed")
    
    async def shutdown(self) -> None:
        """Shutdown gracioso do brain."""
        logger.info(f"[{self.brain_id}] Shutting down...")
        self._running = False
        self.state = BrainState.SHUTDOWN
        
        if self._task:
            await self._task
        
        logger.info(f"[{self.brain_id}] Shutdown complete")
    
    # ===== MAIN LOOP =====
    
    async def _run_loop(self) -> None:
        """Loop principal do brain."""
        try:
            while self._running:
                # Heartbeat
                await self._send_heartbeat()
                
                # Brain-specific work
                try:
                    await self.process()
                except Exception as e:
                    logger.error(f"[{self.brain_id}] Error in process: {e}", 
                               exc_info=True)
                    self.state = BrainState.ERROR
                    self.metrics.events_failed += 1
                    await asyncio.sleep(1.0)  # backoff
                    continue
                
                # Yield control and prevent tight loop
                await asyncio.sleep(0.1)
        
        except asyncio.CancelledError:
            logger.info(f"[{self.brain_id}] Run loop cancelled")
    
    @abstractmethod
    async def process(self) -> None:
        """
        Processamento principal do brain.
        
        Implementado por subclasses.
        """
        pass
    
    # ===== HEARTBEAT & HEALTH =====
    
    async def _send_heartbeat(self) -> None:
        """Envia heartbeat periódicamente."""
        now = time.time()
        if (now - self._last_heartbeat) >= self._heartbeat_interval:
            await self.shared_state.update_brain_heartbeat(self.brain_id)
            self._last_heartbeat = now
    
    async def record_event(self, success: bool, latency_ms: float) -> None:
        """Registra processamento de evento."""
        self.metrics.events_processed += 1
        self.metrics.total_latency_ms += latency_ms
        self.metrics.max_latency_ms = max(self.metrics.max_latency_ms, latency_ms)
        self.metrics.min_latency_ms = min(self.metrics.min_latency_ms, latency_ms)
        
        if not success:
            self.metrics.events_failed += 1
        
        await self.shared_state.record_brain_event(
            self.brain_id, success, latency_ms
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Retorna métricas do brain."""
        avg_latency = (
            self.metrics.total_latency_ms / self.metrics.events_processed
            if self.metrics.events_processed > 0 else 0
        )
        
        return {
            "brain_id": self.brain_id,
            "state": self.state.value,
            "events_processed": self.metrics.events_processed,
            "events_failed": self.metrics.events_failed,
            "avg_latency_ms": avg_latency,
            "max_latency_ms": self.metrics.max_latency_ms,
            "min_latency_ms": self.metrics.min_latency_ms,
        }
    
    # ===== EVENT HELPERS =====
    
    async def publish_event(self, event_type: EventType, 
                           payload: Dict[str, Any]) -> None:
        """Helper para publicar eventos."""
        event = AgentEvent(
            type=event_type,
            source_brain=self.brain_id,
            payload=payload,
            trace_id=None
        )
        await self.event_bus.publish(event)
    
    async def subscribe_event(self, event_type: EventType, 
                             handler) -> None:
        """Helper para subscrever eventos."""
        # Usa decorator já implementado
        self.event_bus.subscribe(event_type, source_brain=None)(handler)
