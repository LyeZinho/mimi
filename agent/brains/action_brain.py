import logging
from agent.brains.base import BrainBase
from agent.schemas import ResponsePlan

log = logging.getLogger(__name__)


class ActionBrain(BrainBase):
    """Rule-based intent routing. Zero LLM calls."""
    name = "action"

    async def run(self, context: dict) -> dict:
        plan: ResponsePlan | None = context.get("response_plan")
        if plan is None:
            return context

        # Rule: empty response → silence
        if not plan.text.strip():
            plan.action = "silence"
            log.debug("ActionBrain: empty response → silence")

        context["response_plan"] = plan
        return context
