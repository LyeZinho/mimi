"""Integration test for end-to-end text pipeline."""
import pytest
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_text_turn_end_to_end(mocker):
    """Test a single text turn: input → reasoning → output text"""
    # Mock Ollama calls
    mocker.patch(
        "agent.llm.ollama_client.OllamaClient.generate",
        side_effect=[
            '{"emotion": "neutral", "intensity": 0.5}',  # sentiment
            "Hi there! Nice to meet you.",                # reasoning
        ],
    )
    # Mock Redis (not running in unit tests) - using redis.asyncio, NOT aioredis
    mock_redis = AsyncMock()
    mock_redis.rpush = AsyncMock()
    mock_redis.lrange = AsyncMock(return_value=[])
    mock_redis.ltrim = AsyncMock()
    mock_redis.delete = AsyncMock()
    mock_redis.aclose = AsyncMock()
    mocker.patch("redis.asyncio.Redis.from_url", return_value=mock_redis)

    from agent.orchestrator import Orchestrator

    orchestrator = Orchestrator()
    await orchestrator.setup()

    response = await orchestrator.process_text("Hello Mimi!")
    assert response is not None
    assert len(response) > 0

    await orchestrator.teardown()
