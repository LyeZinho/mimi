from __future__ import annotations

from .base import BaseTool
import datetime


class TimeTool(BaseTool):
    name = "time"
    description = "Retorna a data e hora atual. Use 'utc' para hora UTC."

    async def execute(self, input_data: str) -> str:
        mode = (input_data or "").strip().lower()
        try:
            if mode == "utc":
                now = datetime.datetime.utcnow()
                return now.replace(tzinfo=datetime.timezone.utc).isoformat(sep=" ", timespec="seconds")
            # default: local
            now = datetime.datetime.now()
            return now.isoformat(sep=" ", timespec="seconds")
        except Exception as e:
            return f"Erro ao obter hora: {e}"
