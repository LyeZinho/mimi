"""Cliente para LLM local (Ollama / llama.cpp)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from .prompts import build_system_prompt, build_user_prompt

from agent.config import LLM_MODEL, OLLAMA_HOST

logger = logging.getLogger(__name__)


class LLMClient:
    """Cliente assíncrono para Ollama API."""

    def __init__(
        self,
        model: str = LLM_MODEL,
        base_url: str = OLLAMA_HOST,
        timeout: float = 60.0,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        """Fecha a sessão HTTP."""
        await self._client.aclose()

    async def _chat(self, messages: list[dict[str, str]]) -> str:
        """Envia mensagens para a API de chat do Ollama."""
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        resp = await self._client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "")

    async def get_intent(
        self,
        user_message: str,
        history: list[dict[str, Any]],
        state: dict[str, Any],
        context: list[dict[str, Any]] | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Obtém intenção estruturada do LLM."""
        system_prompt = build_system_prompt(state, tools=tools)
        user_prompt = build_user_prompt(user_message, history, context=context)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        raw = await self._chat(messages)
        logger.debug("Resposta bruta do LLM: %s", raw)

        # Tenta extrair JSON da resposta
        intent = self._parse_intent(raw)
        return intent

    def _parse_intent(self, raw: str) -> dict[str, Any]:
        """Extrai JSON da resposta do LLM (com fallback)."""
        logger.debug("Tentando extrair JSON de: %s", raw)

        # 1. Tenta remover blocos de código markdown
        clean_text = re.sub(r"```json\s*(.*?)\s*```", r"\1", raw, flags=re.DOTALL)
        clean_text = re.sub(r"```\s*(.*?)\s*```", r"\1", clean_text, flags=re.DOTALL)
        
        # 2. Tenta encontrar o PRIMEIRO objeto JSON válido
        # Procura por chaves balanceadas (simplificado)
        matches = re.finditer(r"\{.*?\}", clean_text, re.DOTALL)
        
        for match in matches:
            candidate = match.group()
            try:
                data = json.loads(candidate)
                # Verifica se parece um intent válido
                if "intent" in data:
                    return data
            except json.JSONDecodeError:
                continue

        # 3. Fallback: resposta como fala simples
        # Se não achou JSON, usa o texto todo, limpando possíveis sobras
        logger.warning("Falha ao extrair JSON. Usando fallback.")
        return {
            "intent": "speak",
            "text": clean_text.strip(),
            "emotion": "neutral",
        }
