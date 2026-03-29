"""
Brain 1.5: Input Processing Brain

Sits between InputBrain (STT) and ReasoningBrain (LLM).

Responsibilities:
- Normalize STT output (strip hesitations, fix common artifacts)
- Load and inject agent persona/context
- Build enriched payload for ReasoningBrain
"""

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Optional

from agent.core.messaging import Brain, EventType, get_event_bus

logger = logging.getLogger(__name__)

_HESITATIONS = re.compile(
    r"\b(ã+|ãh+|uh+|uhm+|hmm+|hm+|eh+|ah+|aham|tá|né|então)\b",
    re.IGNORECASE,
)
_MULTI_SPACE = re.compile(r"\s{2,}")
_REPEATED_PUNCT = re.compile(r"([?.!,])\1+")


def _normalize(text: str) -> str:
    text = text.strip()
    text = _HESITATIONS.sub("", text)
    text = _REPEATED_PUNCT.sub(r"\1", text)
    text = _MULTI_SPACE.sub(" ", text)
    return text.strip()


class InputProcessingBrain(Brain):
    """Normalizes STT text and enriches it with persona context before LLM."""

    def __init__(self, persona_path: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self._persona_path = persona_path or os.getenv("PERSONA_PATH", "data/persona.json")
        self._persona: dict = {}

    async def initialize(self) -> None:
        await super().initialize()
        self._persona = self._load_persona()
        bus = get_event_bus()
        bus.subscribe(EventType.TRANSCRIPTION_COMPLETE)(self._on_transcription_complete)
        logger.info(f"[{self.brain_id}] Ready — persona: {self._persona.get('name', 'unknown')}")

    async def process(self) -> None:
        await __import__("asyncio").sleep(0.1)

    def _load_persona(self) -> dict:
        path = Path(self._persona_path)
        if not path.exists():
            logger.warning(f"[{self.brain_id}] persona.json not found at {path}, using defaults")
            return {"name": "Mimi", "instructions": [], "emotions": []}
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"[{self.brain_id}] Loaded persona: {data.get('name')}")
            return data
        except Exception as e:
            logger.error(f"[{self.brain_id}] Failed to load persona: {e}")
            return {"name": "Mimi", "instructions": [], "emotions": []}

    def _build_system_context(self) -> str:
        name = self._persona.get("name", "Mimi")
        description = self._persona.get("description", "assistente de IA")
        instructions = self._persona.get("instructions", [])
        emotions = self._persona.get("emotions", [])
        lore = self._persona.get("lore", [])
        music = self._persona.get("music", [])
        visual = self._persona.get("visual", "")

        lines = [f"Você é {name}, {description}."]

        if visual:
            lines.append(f"Visual: {visual}")
        if lore:
            lines.append(f"Lore/interesses: {', '.join(lore)}.")
        if music:
            lines.append(f"Gostos musicais: {', '.join(music)}.")
        if instructions:
            lines.append("Instruções:")
            for inst in instructions:
                lines.append(f"- {inst}")
        if emotions:
            lines.append(f"Estados emocionais disponíveis: {', '.join(emotions)}.")
        return "\n".join(lines)

    async def _on_transcription_complete(self, event) -> None:
        raw_transcript = event.payload.get("transcript", "")
        if not raw_transcript:
            return

        start = time.time()

        normalized = _normalize(raw_transcript)
        if not normalized:
            logger.debug(f"[{self.brain_id}] Transcript empty after normalization, skipping")
            return

        system_context = self._build_system_context()

        payload = {
            "normalized_text": normalized,
            "raw_text": raw_transcript,
            "system_context": system_context,
            "persona_name": self._persona.get("name", "Mimi"),
            "confidence": event.payload.get("confidence", 1.0),
            "trace_id": event.trace_id,
        }

        logger.info(
            f"[{self.brain_id}] raw={repr(raw_transcript)!r} → normalized={repr(normalized)!r}"
        )

        await self.publish_event(EventType.INPUT_PROCESSED, payload)

        latency = (time.time() - start) * 1000
        await self.record_event(success=True, latency_ms=latency)

    async def health_check(self) -> dict:
        try:
            persona_ok = bool(self._persona.get("name"))
            return {
                "name": "InputProcessingBrain",
                "status": "operational" if persona_ok else "degraded",
                "details": f"persona={self._persona.get('name', 'none')}",
            }
        except Exception as e:
            return {"name": "InputProcessingBrain", "status": "failed", "details": str(e)}
