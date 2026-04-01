import asyncio
import logging
import uuid
import yaml
from pathlib import Path
from agent.fsm.agent_fsm import AgentFSM
from agent.fsm.states import AgentStateEnum
from agent.brains.base import BrainRegistry
from agent.brains.reasoning_brain import ReasoningBrain
from agent.brains.sentiment_brain import SentimentBrain
from agent.brains.action_brain import ActionBrain
from agent.brains.interaction_brain import InteractionBrain, InteractionWriteBrain
from agent.memory.short_term import ShortTermMemory
from agent.memory.long_term import LongTermMemory
from agent.schemas import TranscriptEvent, AgentContext, AgentStateSnapshot
from agent.config import settings

log = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self) -> None:
        self._fsm = AgentFSM()
        self._registry = BrainRegistry()
        self._short_mem = ShortTermMemory(settings.redis_url)
        self._long_mem = LongTermMemory(settings.sqlite_path)
        self._state_snapshot = AgentStateSnapshot(
            fsm_state="idle", active_brain="none",
            last_emotion="unknown", last_transcript="",
            latency_ms=0,
        )
        self._pipeline_config: dict = {}

    async def setup(self) -> None:
        config_path = Path("config/pipeline.yaml")
        if config_path.exists():
            with open(config_path) as f:
                self._pipeline_config = yaml.safe_load(f)

        await self._short_mem.connect()
        await self._long_mem.connect()

        interaction = InteractionBrain(self._short_mem, self._long_mem)
        self._registry.register(interaction)
        self._registry.register(InteractionWriteBrain(interaction))
        self._registry.register(ReasoningBrain())
        self._registry.register(SentimentBrain())
        self._registry.register(ActionBrain())

        log.info("Orchestrator ready")

    async def teardown(self) -> None:
        await self._short_mem.disconnect()
        await self._long_mem.disconnect()

    def _get_pipeline(self, state: AgentStateEnum) -> list[str]:
        states = self._pipeline_config.get("states", {})
        return states.get(state.value, {}).get("pipeline", [])

    async def process_text(self, text: str, session_id: str | None = None) -> str:
        if session_id is None:
            session_id = str(uuid.uuid4())

        await self._fsm.transition(AgentStateEnum.LISTENING)
        await self._fsm.transition(AgentStateEnum.PROCESSING)

        context: dict = {
            "context": AgentContext(
                transcript=TranscriptEvent(text=text),
                memory=[],
                session_id=session_id,
            )
        }

        pipeline = self._get_pipeline(AgentStateEnum.PROCESSING)
        context = await self._registry.run_pipeline(pipeline, context)

        response_plan = context.get("response_plan")
        response_text = response_plan.text if response_plan else ""

        await self._fsm.transition(AgentStateEnum.SPEAKING)
        await self._fsm.transition(AgentStateEnum.IDLE)

        return response_text
