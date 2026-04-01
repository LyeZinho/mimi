from __future__ import annotations

from .base import BaseTool
import httpx
import logging

logger = logging.getLogger(__name__)


class HTTPTool(BaseTool):
    name = "http"
    description = "Busca uma URL via GET e retorna texto (trimmed). Uso: 'GET http(s)://...'."

    async def execute(self, input_data: str) -> str:
        url = (input_data or "").strip()
        if not url:
            return "Forneça uma URL (ex: https://example.com)."
        if not (url.startswith("http://") or url.startswith("https://")):
            return "URL inválida: deve começar com http:// ou https://"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                text = resp.text
                # Limitar retorno para evitar payloads enormes
                if len(text) > 2000:
                    return text[:2000] + "\n...[truncated]"
                return text
        except Exception as e:
            logger.debug("HTTPTool error", exc_info=True)
            return f"Erro HTTP: {e}"
