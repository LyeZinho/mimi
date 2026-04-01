import pytest
from agent.brains.action_brain import ActionBrain
from agent.schemas import AgentContext, TranscriptEvent, ResponsePlan

def make_context(text: str, response: str = "ok") -> dict:
    return {
        "context": AgentContext(
            transcript=TranscriptEvent(text=text),
            memory=[],
            session_id="test",
        ),
        "response_plan": ResponsePlan(text=response, action="speak"),
    }

@pytest.mark.asyncio
async def test_action_brain_passes_through_default():
    brain = ActionBrain()
    ctx = make_context("hello")
    result = await brain.run(ctx)
    assert result["response_plan"].action == "speak"

@pytest.mark.asyncio
async def test_action_brain_detects_silence():
    brain = ActionBrain()
    ctx = make_context("ok")
    ctx["response_plan"] = ResponsePlan(text="", action="speak")
    result = await brain.run(ctx)
    assert result["response_plan"].action == "silence"
