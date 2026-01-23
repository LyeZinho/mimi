from __future__ import annotations

from .base import BaseTool
from typing import ClassVar, List


class NotesTool(BaseTool):
    name = "notes"
    description = "Gerencia notas simples. Comandos: 'add: texto', 'list', 'get:idx', 'clear'."

    _notes: ClassVar[List[str]] = []

    async def execute(self, input_data: str) -> str:
        cmd = (input_data or "").strip()
        if not cmd:
            return "Comandos: add:, list, get:, clear"

        lower = cmd.lower()
        if lower.startswith("add:"):
            note = cmd[4:].strip()
            if not note:
                return "Nota vazia. Use 'add: seu texto'."
            self._notes.append(note)
            return f"Nota adicionada (#{len(self._notes)-1})."

        if lower in ("list", "show"):
            if not self._notes:
                return "Sem notas."
            return "\n".join(f"{i}: {n}" for i, n in enumerate(self._notes))

        if lower.startswith("get:"):
            try:
                idx = int(cmd.split(":", 1)[1].strip())
                return self._notes[idx]
            except Exception:
                return "Índice inválido ou nota inexistente."

        if lower in ("clear", "delete all"):
            count = len(self._notes)
            self._notes.clear()
            return f"Apagadas {count} notas."

        return "Comando desconhecido. Use 'add:', 'list', 'get:' ou 'clear'."
