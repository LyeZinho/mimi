import pytest
from unittest.mock import AsyncMock, MagicMock
from agent.brains.interaction_brain import InteractionBrain
from agent.schemas import TranscriptEvent, AgentContext, ResponsePlan, MemoryEntry

def make_context(text: str = "hello") -> dict:
    return {
        "context": AgentContext(
            transcript=TranscriptEvent(text=text),
            memory=[],
            session_id="sess1",
        )
    }

@pytest.mark.asyncio
async def test_read_loads_history(mocker):
    brain = InteractionBrain.__new__(InteractionBrain)
    brain._short = AsyncMock()
    brain._long = AsyncMock()
    brain._short.get_history = AsyncMock(return_value=[MemoryEntry(role="user", content="prev")])
    brain._long.load = AsyncMock(return_value=[])
    brain.name = "interaction_read"

    ctx = make_context()
    result = await brain.run_read(ctx)
    assert len(result["context"].memory) == 1

@pytest.mark.asyncio
async def test_write_saves_turn(mocker):
    brain = InteractionBrain.__new__(InteractionBrain)
    brain._short = AsyncMock()
    brain._long = AsyncMock()
    brain._short.add = AsyncMock()
    brain._long.save = AsyncMock()

    ctx = make_context("hi")
    ctx["response_plan"] = ResponsePlan(text="hello back", action="speak")
    await brain.run_write(ctx)

    assert brain._short.add.call_count == 2  # user + assistant
    assert brain._long.save.call_count == 2
