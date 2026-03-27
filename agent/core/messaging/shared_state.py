"""
Shared State Store com locking para comunicação entre Brains.

Mantém contexto do agente, histórico de conversa e status dos brains.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List
from datetime import datetime
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class UserContextState(str, Enum):
    """Estados do contexto do utilizador."""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    ERROR = "error"


@dataclass
class UserContext:
    """Contexto do utilizador (imutável, versionado)."""
    
    user_id: str
    session_id: str
    language: str = "pt-PT"
    timezone: str = "Europe/Lisbon"
    
    # Histórico conversação (últimos N turnos)
    conversation_turns: List[Dict[str, str]] = field(default_factory=list)
    
    # Estado atual
    state: UserContextState = UserContextState.IDLE
    current_intent: Optional[str] = None
    last_detected_emotion: Optional[str] = None
    
    # Metadados
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    version: int = 0


@dataclass
class BrainHealth:
    """Health metrics de um Brain."""
    
    brain_id: str
    is_alive: bool = True
    last_heartbeat: float = field(default_factory=time.time)
    events_processed: int = 0
    errors: int = 0
    avg_latency_ms: float = 0.0
    
    def update_heartbeat(self):
        self.last_heartbeat = time.time()
    
    def is_healthy(self, timeout_sec: float = 5.0) -> bool:
        """Verifica se brain respondeu recentemente."""
        return (time.time() - self.last_heartbeat) < timeout_sec


@dataclass
class TaskStatus:
    """Status de uma task em execução."""
    
    task_id: str
    brain_id: str
    status: str  # "pending", "running", "done", "error"
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class LockAcquisition:
    """Context manager para lock acquisition."""
    
    def __init__(self, lock: asyncio.Lock, brain_id: str, duration_ms: int):
        self.lock = lock
        self.brain_id = brain_id
        self.duration_ms = duration_ms
        self.acquired_at: Optional[float] = None
    
    async def __aenter__(self):
        await self.lock.acquire()
        self.acquired_at = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.lock.release()
        duration = (time.time() - self.acquired_at) * 1000
        if duration > self.duration_ms * 1.5:
            logger.warning(
                f"Lock held longer than expected: "
                f"{duration:.1f}ms (expected {self.duration_ms}ms) by {self.brain_id}"
            )


class SharedAgentState:
    """
    Shared state store com thread-safe access.
    
    Usa asyncio.Lock para serializar updates críticos.
    Leitura é lock-free (snapshot).
    """
    
    def __init__(self):
        self._state_lock = asyncio.Lock()
        
        # User context (versionado para detect changes)
        self._user_context: Optional[UserContext] = None
        self._context_version = 0
        
        # Conversation history (thread-safe deque)
        self._conversation_history: List[Dict[str, Any]] = []
        self._max_history = 100
        
        # Active tasks
        self._active_tasks: Dict[str, TaskStatus] = {}
        
        # Brain health
        self._brain_health: Dict[str, BrainHealth] = {}
        
        # Configuration
        self._config: Dict[str, Any] = {}
    
    async def initialize(self, user_id: str, session_id: str) -> None:
        """Inicializa state."""
        async with self._state_lock:
            self._user_context = UserContext(
                user_id=user_id,
                session_id=session_id
            )
            self._context_version = 0
    
    # ===== CONTEXT MANAGEMENT =====
    
    async def get_context_snapshot(self) -> UserContext:
        """Retorna snapshot do contexto (lock-free read)."""
        if self._user_context is None:
            raise RuntimeError("State not initialized")
        return self._user_context
    
    async def update_context(self, 
                            brain_id: str,
                            delta: Dict[str, Any],
                            lock_duration_ms: int = 50) -> int:
        """
        Atualiza contexto com delta.
        
        Retorna nova versão do contexto.
        """
        async with LockAcquisition(self._state_lock, brain_id, lock_duration_ms):
            if self._user_context is None:
                raise RuntimeError("State not initialized")
            
            # Aplica delta
            for key, value in delta.items():
                if hasattr(self._user_context, key):
                    setattr(self._user_context, key, value)
            
            self._user_context.updated_at = time.time()
            self._context_version += 1
            
            logger.debug(f"Context updated by {brain_id}: v{self._context_version}")
            return self._context_version
    
    async def set_state(self, new_state: UserContextState) -> None:
        """Muda state do utilizador."""
        async with self._state_lock:
            if self._user_context:
                self._user_context.state = new_state
                self._user_context.updated_at = time.time()
    
    # ===== CONVERSATION HISTORY =====
    
    async def add_to_history(self, turn: Dict[str, str]) -> None:
        """Adiciona turno ao histórico."""
        async with self._state_lock:
            self._conversation_history.append({
                **turn,
                "timestamp": time.time()
            })
            
            if len(self._conversation_history) > self._max_history:
                self._conversation_history.pop(0)
    
    async def get_recent_history(self, n: int = 10) -> List[Dict[str, Any]]:
        """Retorna últimos N turnos (lock-free)."""
        return self._conversation_history[-n:]
    
    # ===== TASK MANAGEMENT =====
    
    async def create_task(self, task_id: str, brain_id: str) -> TaskStatus:
        """Cria nova task."""
        async with self._state_lock:
            task = TaskStatus(task_id=task_id, brain_id=brain_id, status="pending")
            self._active_tasks[task_id] = task
            return task
    
    async def update_task(self, task_id: str, status: str, 
                         result: Optional[Dict] = None,
                         error: Optional[str] = None) -> None:
        """Atualiza status de task."""
        async with self._state_lock:
            if task_id not in self._active_tasks:
                logger.warning(f"Task not found: {task_id}")
                return
            
            task = self._active_tasks[task_id]
            task.status = status
            task.result = result
            task.error = error
            
            if status == "running" and task.started_at is None:
                task.started_at = time.time()
            elif status in ["done", "error"]:
                task.completed_at = time.time()
    
    async def get_task(self, task_id: str) -> Optional[TaskStatus]:
        """Retorna task (lock-free)."""
        return self._active_tasks.get(task_id)
    
    async def cleanup_completed_tasks(self, max_age_sec: float = 300) -> int:
        """Remove tasks completadas com mais de max_age_sec."""
        async with self._state_lock:
            now = time.time()
            to_remove = [
                task_id for task_id, task in self._active_tasks.items()
                if task.status in ["done", "error"] 
                and (now - task.completed_at) > max_age_sec
            ]
            
            for task_id in to_remove:
                del self._active_tasks[task_id]
            
            return len(to_remove)
    
    # ===== BRAIN HEALTH =====
    
    async def register_brain(self, brain_id: str) -> None:
        """Registra novo brain."""
        async with self._state_lock:
            self._brain_health[brain_id] = BrainHealth(brain_id=brain_id)
    
    async def update_brain_heartbeat(self, brain_id: str) -> None:
        """Atualiza heartbeat de um brain."""
        if brain_id in self._brain_health:
            self._brain_health[brain_id].update_heartbeat()
    
    async def record_brain_event(self, brain_id: str, 
                                success: bool,
                                latency_ms: float) -> None:
        """Registra evento (processamento) em um brain."""
        async with self._state_lock:
            if brain_id not in self._brain_health:
                return
            
            health = self._brain_health[brain_id]
            health.events_processed += 1
            
            if success:
                health.avg_latency_ms = (
                    (health.avg_latency_ms * (health.events_processed - 1) + latency_ms)
                    / health.events_processed
                )
            else:
                health.errors += 1
    
    async def get_brain_health(self, brain_id: str) -> Optional[BrainHealth]:
        """Retorna health de um brain (lock-free)."""
        return self._brain_health.get(brain_id)
    
    async def get_all_brain_health(self) -> Dict[str, BrainHealth]:
        """Retorna saúde de todos os brains (lock-free)."""
        return dict(self._brain_health)
    
    # ===== CONFIGURATION =====
    
    async def set_config(self, key: str, value: Any) -> None:
        """Define configuração."""
        async with self._state_lock:
            self._config[key] = value
    
    async def get_config(self, key: str, default: Any = None) -> Any:
        """Retorna configuração (lock-free)."""
        return self._config.get(key, default)
    
    # ===== SNAPSHOT =====
    
    async def get_full_snapshot(self) -> Dict[str, Any]:
        """Retorna snapshot completo do state."""
        return {
            "context": self._user_context,
            "context_version": self._context_version,
            "conversation_history_size": len(self._conversation_history),
            "active_tasks": len(self._active_tasks),
            "brain_health": {
                brain_id: {
                    "is_alive": health.is_alive,
                    "is_healthy": health.is_healthy(),
                    "events_processed": health.events_processed,
                    "errors": health.errors,
                    "avg_latency_ms": health.avg_latency_ms,
                }
                for brain_id, health in self._brain_health.items()
            }
        }


# Singleton global
_global_state: Optional[SharedAgentState] = None


def get_shared_state() -> SharedAgentState:
    """Retorna instância global do state."""
    global _global_state
    if _global_state is None:
        _global_state = SharedAgentState()
    return _global_state
