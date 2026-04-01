import logging
import httpx
from typing import Any

log = logging.getLogger(__name__)

Message = dict[str, str]  # {"role": "user"|"assistant"|"system", "content": str}


class OllamaClient:
    def __init__(
        self,
        host: str,
        model: str,
        system_prompt: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._host = host.rstrip("/")
        self._model = model
        self._system_prompt = system_prompt
        self._timeout = timeout

    async def generate(self, messages: list[Message]) -> str:
        all_messages: list[Message] = []
        if self._system_prompt:
            all_messages.append({"role": "system", "content": self._system_prompt})
        all_messages.extend(messages)

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": all_messages,
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(f"{self._host}/api/chat", json=payload)
            resp.raise_for_status()
            data = await resp.json()

        text: str = data["message"]["content"]
        log.debug("Ollama [%s]: %d chars", self._model, len(text))
        return text
