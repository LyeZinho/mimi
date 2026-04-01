import json
import logging
from agent.brains.base import BrainBase
from agent.llm.ollama_client import OllamaClient
from agent.schemas import AgentContext, SentimentResult
from agent.config import settings

log = logging.getLogger(__name__)

_SYSTEM = """Analyze the emotion in the user's message.
Respond ONLY with valid JSON: {"emotion": "<one of: neutral,happy,sad,angry,surprised,curious>", "intensity": <0.0-1.0>}
No other text."""


class SentimentBrain(BrainBase):
    name = "sentiment"

    def __init__(self) -> None:
        self._client = OllamaClient(
            host=settings.ollama_host,
            model=settings.ollama_sentiment_model,
            system_prompt=_SYSTEM,
        )

    async def run(self, context: dict) -> dict:
        ctx: AgentContext = context["context"]
        try:
            raw = await self._client.generate(
                messages=[{"role": "user", "content": ctx.transcript.text}]
            )
            data = json.loads(raw.strip())
            ctx.sentiment = SentimentResult(**data)
        except Exception:
            log.warning("SentimentBrain fallback to neutral")
            ctx.sentiment = SentimentResult(emotion="neutral", intensity=0.0)
        return context
