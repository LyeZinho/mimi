"""
Event Bus (pub/sub) para comunicação entre Brains.

Não-bloqueante, tipado, com suporte a async handlers.
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Tipos de eventos no sistema."""
    
    # Input Brain
    AUDIO_CHUNK = "audio_chunk"
    VAD_START = "vad_start"
    VAD_END = "vad_end"
    TRANSCRIPTION_START = "transcription_start"
    TRANSCRIPTION_COMPLETE = "transcription_complete"
    TEXT_CHUNK = "text_chunk"
    
    # Reasoning Brain
    CONTEXT_UPDATED = "context_updated"
    INTENT_DETECTED = "intent_detected"
    INTENT_STREAMING = "intent_streaming"
    
    # Planning Brain
    TOOLS_QUEUED = "tools_queued"
    PLAN_CREATED = "plan_created"
    
    # Execution Brain
    TOOL_STARTED = "tool_started"
    TOOL_RESULT = "tool_result"
    TOOL_ERROR = "tool_error"
    
    # Sentiment Brain
    SENTIMENT_UPDATED = "sentiment_updated"
    EMOTION_DETECTED = "emotion_detected"
    
    # Avatar Brain
    ANIMATION_QUEUED = "animation_queued"
    GESTURE_QUEUED = "gesture_queued"
    AVATAR_STATE_CHANGED = "avatar_state_changed"
    
    # ML Pose Playback
    POSE_PLAYBACK = "pose_playback"
    
    # Output Brain
    RESPONSE_READY = "response_ready"
    AUDIO_COMPLETE = "audio_complete"
    PHONEME_DATA = "phoneme_data"
    TTS_STARTED = "tts_started"
    TTS_CHUNK = "tts_chunk"
    TTS_COMPLETE = "tts_complete"
    
    # System
    BRAIN_HEALTH = "brain_health"
    SYSTEM_ERROR = "system_error"
    ORCHESTRATOR_TICK = "orchestrator_tick"


@dataclass
class AgentEvent:
    """Evento no bus."""
    
    type: EventType
    source_brain: str  # ex: "input_brain", "reasoning_brain"
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    
    # Metadados
    event_id: str = field(default_factory=lambda: f"evt_{int(time.time()*1000)}")
    trace_id: Optional[str] = None  # para rastreamento end-to-end
    priority: int = 0  # 0=normal, 1=high, -1=low
    
    def __post_init__(self):
        if self.trace_id is None:
            self.trace_id = self.event_id


class EventHandler:
    """Handler tipado para eventos."""
    
    def __init__(self, 
                 handler_func: Callable,
                 event_type: EventType,
                 source_brain: Optional[str] = None):
        self.handler_func = handler_func
        self.event_type = event_type
        self.source_brain = source_brain  # None = qualquer source
        self.call_count = 0
        self.errors = 0
    
    async def call(self, event: AgentEvent):
        """Executa handler com error tracking."""
        try:
            self.call_count += 1
            if asyncio.iscoroutinefunction(self.handler_func):
                await self.handler_func(event)
            else:
                self.handler_func(event)
        except Exception as e:
            self.errors += 1
            logger.error(f"Handler error: {e}", exc_info=True)
            raise


class EventBus:
    """
    Bus de eventos async, pub/sub.
    
    Uso:
        bus = EventBus()
        
        @bus.subscribe(EventType.TEXT_CHUNK)
        async def on_text(event):
            print(event.payload)
        
        await bus.publish(AgentEvent(
            type=EventType.TEXT_CHUNK,
            source_brain="input_brain",
            payload={"text": "hello"}
        ))
    """
    
    def __init__(self, max_queue_size: int = 1000):
        self._subscribers: Dict[EventType, List[EventHandler]] = {}
        self._wildcard_subscribers: List[EventHandler] = []  # subscrevem a TODOS
        self._event_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._running = False
        self._processor_task: Optional[asyncio.Task] = None
        
        # Metrics
        self._events_published = 0
        self._events_processed = 0
        self._event_history: List[AgentEvent] = []
        self._max_history = 1000
    
    def subscribe(self, event_type: Optional[EventType] = None, 
                  source_brain: Optional[str] = None):
        """
        Decorator para subscrever a eventos.
        
        Uso:
            @bus.subscribe(EventType.TEXT_CHUNK)
            async def handler(event):
                pass
            
            @bus.subscribe()  # Todos os eventos
            async def universal_handler(event):
                pass
        """
        def decorator(handler_func: Callable):
            handler = EventHandler(handler_func, event_type, source_brain)
            
            if event_type is None:
                # Wildcard subscription
                self._wildcard_subscribers.append(handler)
            else:
                if event_type not in self._subscribers:
                    self._subscribers[event_type] = []
                self._subscribers[event_type].append(handler)
            
            logger.info(f"Handler subscribed: {handler_func.__name__} "
                       f"(event_type={event_type}, source={source_brain})")
            return handler_func
        
        return decorator
    
    async def publish(self, event: AgentEvent) -> None:
        """Publica evento no bus (non-blocking)."""
        try:
            await asyncio.wait_for(self._event_queue.put(event), timeout=1.0)
            self._events_published += 1
        except asyncio.TimeoutError:
            logger.warning(f"Event queue full, dropping event: {event.type}")
    
    async def start(self) -> None:
        """Inicia processor do bus."""
        if self._running:
            return
        
        self._running = True
        self._processor_task = asyncio.create_task(self._process_events())
        logger.info("EventBus started")
    
    async def stop(self) -> None:
        """Para o bus."""
        self._running = False
        if self._processor_task:
            await self._processor_task
        logger.info("EventBus stopped")
    
    async def _process_events(self) -> None:
        """Processa eventos continuamente."""
        while self._running:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(), timeout=1.0
                )
                
                # Record em histórico
                self._event_history.append(event)
                if len(self._event_history) > self._max_history:
                    self._event_history.pop(0)
                
                # Dispatch para handlers
                await self._dispatch_event(event)
                self._events_processed += 1
                
            except asyncio.TimeoutError:
                pass  # Timeout normal
            except Exception as e:
                logger.error(f"Error processing event: {e}", exc_info=True)
    
    async def _dispatch_event(self, event: AgentEvent) -> None:
        """Dispatch evento para todos handlers relevantes."""
        handlers_to_call = []
        
        # Wildcard handlers (todos os eventos)
        handlers_to_call.extend(self._wildcard_subscribers)
        
        # Handlers específicos por tipo
        if event.type in self._subscribers:
            for handler in self._subscribers[event.type]:
                # Filtra por source_brain se especificado
                if handler.source_brain is None or handler.source_brain == event.source_brain:
                    handlers_to_call.append(handler)
        
        # Executa handlers em paralelo
        tasks = [handler.call(event) for handler in handlers_to_call]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Retorna métricas do bus."""
        return {
            "events_published": self._events_published,
            "events_processed": self._events_processed,
            "queue_size": self._event_queue.qsize(),
            "queue_max": self._event_queue.maxsize,
            "subscribers": {
                str(k): len(v) 
                for k, v in self._subscribers.items()
            },
            "wildcard_subscribers": len(self._wildcard_subscribers),
            "history_size": len(self._event_history),
        }
    
    def get_history(self, event_type: Optional[EventType] = None, 
                    limit: int = 100) -> List[AgentEvent]:
        """Retorna histórico de eventos."""
        history = self._event_history
        
        if event_type:
            history = [e for e in history if e.type == event_type]
        
        return history[-limit:]


# Singleton global (opcional)
_global_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Retorna instância global do bus."""
    global _global_bus
    if _global_bus is None:
        _global_bus = EventBus()
    return _global_bus
