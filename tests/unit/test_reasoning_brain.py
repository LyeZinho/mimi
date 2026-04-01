import pytest
from unittest.mock import AsyncMock
from agent.brains.reasoning_brain import ReasoningBrain
from agent.schemas import TranscriptEvent, SentimentResult, AgentContext, ResponsePlan

def make_context(text: str = "hello") -> dict:
    ctx: dict = {
        "context": AgentContext(
            transcript=TranscriptEvent(text=text),
            sentiment=SentimentResult(emotion="neutral", intensity=0.5),
            memory=[],
            session_id="test",
        )
    }
    return ctx

@pytest.mark.asyncio
async def test_reasoning_brain_produces_response_plan(mocker):
    brain = ReasoningBrain.__new__(ReasoningBrain)
    brain._client = AsyncMock()
    brain._client.generate = AsyncMock(return_value="Hello! How can I help?")
    brain.name = "reasoning"

    ctx = make_context("hi mimi")
    result = await brain.run(ctx)

    assert "response_plan" in result
    plan = result["response_plan"]
    assert isinstance(plan, ResponsePlan)
    assert plan.text == "Hello! How can I help?"
    assert plan.action == "speak"

@pytest.mark.asyncio
async def test_reasoning_brain_passes_history_to_llm(mocker):
    from agent.schemas import MemoryEntry
    brain = ReasoningBrain.__new__(ReasoningBrain)
    brain._client = AsyncMock()
    brain._client.generate = AsyncMock(return_value="Sure!")
    brain.name = "reasoning"

    ctx = make_context("what did I say?")
    ctx["context"].memory = [MemoryEntry(role="user", content="I said hello")]
    
    result = await brain.run(ctx)
    call_args = brain._client.generate.call_args
    messages = call_args.kwargs["messages"] if call_args.kwargs else call_args.args[0]
    assert any("I said hello" in m["content"] for m in messages)
