import logging
from agent.brains.base import BrainBase
from agent.memory.short_term import ShortTermMemory
from agent.memory.long_term import LongTermMemory
from agent.schemas import AgentContext, MemoryEntry, ResponsePlan

log = logging.getLogger(__name__)


class InteractionBrain(BrainBase):
    name = "interaction_read"

    def __init__(self, short: ShortTermMemory, long: LongTermMemory) -> None:
        self._short = short
        self._long = long

    async def run(self, context: dict) -> dict:
        return await self.run_read(context)

    async def run_read(self, context: dict) -> dict:
        ctx: AgentContext = context["context"]
        recent = await self._short.get_history(ctx.session_id, limit=10)
        if not recent:
            recent = await self._long.load(ctx.session_id, limit=5)
        ctx.memory = recent
        log.debug("InteractionBrain: loaded %d memory entries", len(recent))
        return context

    async def run_write(self, context: dict) -> None:
        ctx: AgentContext = context["context"]
        plan: ResponsePlan | None = context.get("response_plan")
        if plan is None:
            return

        user_entry = MemoryEntry(role="user", content=ctx.transcript.text)
        assistant_entry = MemoryEntry(role="assistant", content=plan.text)

        for entry in (user_entry, assistant_entry):
            await self._short.add(ctx.session_id, entry)
            await self._long.save(ctx.session_id, entry)


class InteractionWriteBrain(BrainBase):
    name = "interaction_write"

    def __init__(self, interaction: "InteractionBrain") -> None:
        self._interaction = interaction

    async def run(self, context: dict) -> dict:
        await self._interaction.run_write(context)
        return context
