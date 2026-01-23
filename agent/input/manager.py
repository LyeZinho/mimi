"""Gerenciador unificado de entradas."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine


@dataclass
class InputEvent:
    """Evento de entrada normalizado."""

    type: str = "user_message"
    content: str = ""
    source: str = "text"  # "voice" | "text"
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


InputHandler = Callable[[InputEvent], Coroutine[Any, Any, None]]


class InputManager:
    """Unifica múltiplas fontes de entrada em uma fila comum."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[InputEvent] = asyncio.Queue()
        self._handlers: list[InputHandler] = []

    def register_handler(self, handler: InputHandler) -> None:
        self._handlers.append(handler)

    async def push(self, content: str, source: str = "text", **meta: Any) -> None:
        """Adiciona evento à fila e notifica handlers."""
        event = InputEvent(content=content, source=source, metadata=meta)
        await self._queue.put(event)
        for handler in self._handlers:
            asyncio.create_task(handler(event))

    async def get(self) -> InputEvent:
        """Aguarda próximo evento da fila."""
        return await self._queue.get()

    def empty(self) -> bool:
        return self._queue.empty()
