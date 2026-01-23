"""Entrada de texto (stdin ou API)."""

from __future__ import annotations

import asyncio
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .manager import InputManager


class TextInput:
    """Captura texto do terminal de forma assíncrona."""

    def __init__(self, manager: "InputManager") -> None:
        self.manager = manager
        self._running = False

    async def run(self, prompt: str = "> ") -> None:
        """Loop de leitura do stdin."""
        self._running = True
        loop = asyncio.get_event_loop()
        while self._running:
            try:
                line = await loop.run_in_executor(None, lambda: input(prompt))
            except EOFError:
                break
            if line.strip():
                await self.manager.push(line.strip(), source="text")
            if line.lower() in {"sair", "exit", "quit"}:
                self._running = False

    def stop(self) -> None:
        self._running = False
