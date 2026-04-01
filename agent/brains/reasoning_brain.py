import logging
from agent.brains.base import BrainBase
from agent.llm.ollama_client import OllamaClient
from agent.schemas import AgentContext, ResponsePlan
from agent.config import settings

log = logging.getLogger(__name__)

_SYSTEM = """You are Mimi, a helpful AI companion.
You speak naturally and concisely.
Respond only with your spoken reply — no stage directions, no markdown."""


class ReasoningBrain(BrainBase):
    name = "reasoning"

    def __init__(self) -> None:
        self._client = OllamaClient(
            host=settings.ollama_host,
            model=settings.ollama_model,
            system_prompt=_SYSTEM,
        )

    async def run(self, context: dict) -> dict:
        ctx: AgentContext = context["context"]
        messages = [
            {"role": e.role, "content": e.content}
            for e in ctx.memory
        ]
        messages.append({"role": "user", "content": ctx.transcript.text})

        text = await self._client.generate(messages=messages)
        context["response_plan"] = ResponsePlan(text=text, action="speak")
        log.debug("ReasoningBrain: %d chars", len(text))
        return context
