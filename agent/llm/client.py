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
        from agent.config import OLLAMA_API_KEY
        
        url = f"{self.base_url}/api/chat"
        headers = {}
        if OLLAMA_API_KEY:
            headers["Authorization"] = f"Bearer {OLLAMA_API_KEY}"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        
        logger.info(f"[LLM] Sending to {url} with model={self.model}")
        resp = await self._client.post(url, json=payload, headers=headers if headers else None)
        resp.raise_for_status()
        data = resp.json()
        content = data.get("message", {}).get("content", "")
        logger.info(f"[LLM] Response (first 300 chars): {content[:300]}")
        return content

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

        try:
            raw = await self._chat(messages)
            logger.info(f"[GET_INTENT] Got raw response from LLM")
        except Exception as e:
            logger.warning(f"[GET_INTENT] Falha ao conectar ao LLM: {e}. Usando fallback.")
            raw = f"Entendi. Você disse: {user_message}"

        # Tenta extrair JSON da resposta
        logger.info(f"[GET_INTENT] Parsing intent from response")
        intent = self._parse_intent(raw)
        logger.info(f"[GET_INTENT] Final intent: {intent.get('intent')}")
        return intent

    def _parse_intent(self, raw: str) -> dict[str, Any]:
        """Extrai JSON da resposta do LLM (com fallback)."""
        logger.info(f"[PARSE] Raw response (first 200 chars): {raw[:200]}")

        # 1. Tenta remover blocos de código markdown
        clean_text = re.sub(r"```json\s*(.*?)\s*```", r"\1", raw, flags=re.DOTALL)
        clean_text = re.sub(r"```\s*(.*?)\s*```", r"\1", clean_text, flags=re.DOTALL)
        
        if clean_text != raw:
            logger.info(f"[PARSE] After markdown removal: {clean_text[:200]}")
        
        # 2. Tenta encontrar o PRIMEIRO objeto JSON válido
        # Procura por chaves balanceadas (simplificado)
        matches = list(re.finditer(r"\{.*?\}", clean_text, re.DOTALL))
        logger.info(f"[PARSE] Found {len(matches)} JSON candidates")
        
        for i, match in enumerate(matches):
            candidate = match.group()
            logger.info(f"[PARSE] Trying candidate {i}: {candidate[:100]}")
            try:
                data = json.loads(candidate)
                logger.info(f"[PARSE] Valid JSON: {data}")
                # Verifica se parece um intent válido
                if "intent" in data:
                    logger.info(f"[PARSE] ✓ Intent found: {data.get('intent')}")
                    return data
                else:
                    logger.info(f"[PARSE] No 'intent' key in parsed JSON")
            except json.JSONDecodeError as e:
                logger.info(f"[PARSE] Candidate {i} failed: {e}")
                continue

        # 3. Fallback: resposta como fala simples
        # Se não achou JSON, usa o texto todo, limpando possíveis sobras
        logger.warning(f"[PARSE] Failed to extract JSON. Using fallback. Raw={raw[:150]}")
        return {
            "intent": "speak",
            "text": clean_text.strip(),
            "emotion": "neutral",
        }
