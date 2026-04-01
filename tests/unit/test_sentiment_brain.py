import pytest
from unittest.mock import AsyncMock
from agent.brains.sentiment_brain import SentimentBrain
from agent.schemas import TranscriptEvent, AgentContext, SentimentResult

def make_context(text: str) -> dict:
    return {
        "context": AgentContext(
            transcript=TranscriptEvent(text=text),
            memory=[],
            session_id="test",
        )
    }

@pytest.mark.asyncio
async def test_sentiment_brain_sets_sentiment(mocker):
    brain = SentimentBrain.__new__(SentimentBrain)
    brain._client = AsyncMock()
    brain._client.generate = AsyncMock(return_value='{"emotion": "happy", "intensity": 0.9}')
    brain.name = "sentiment"

    ctx = make_context("This is great!")
    result = await brain.run(ctx)

    assert result["context"].sentiment is not None
    assert result["context"].sentiment.emotion == "happy"

@pytest.mark.asyncio
async def test_sentiment_brain_falls_back_on_invalid_json(mocker):
    brain = SentimentBrain.__new__(SentimentBrain)
    brain._client = AsyncMock()
    brain._client.generate = AsyncMock(return_value="oops not json")
    brain.name = "sentiment"

    ctx = make_context("something")
    result = await brain.run(ctx)
    # Fallback: neutral sentiment, never crashes
    assert result["context"].sentiment.emotion == "neutral"
