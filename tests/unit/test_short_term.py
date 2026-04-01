import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from agent.memory.short_term import ShortTermMemory
from agent.schemas import MemoryEntry

@pytest.fixture
def mock_redis(mocker):
    redis = AsyncMock()
    mocker.patch("redis.asyncio.Redis.from_url", return_value=redis)
    return redis

@pytest.mark.asyncio
async def test_add_and_get_history(mock_redis):
    mock_redis.rpush = AsyncMock()
    mock_redis.lrange = AsyncMock(return_value=[
        b'{"role": "user", "content": "hello", "timestamp": "2026-01-01T00:00:00"}'
    ])
    
    mem = ShortTermMemory(redis_url="redis://fake")
    await mem.connect()
    await mem.add("session1", MemoryEntry(role="user", content="hello"))
    entries = await mem.get_history("session1", limit=10)
    
    assert len(entries) == 1
    assert entries[0].content == "hello"

@pytest.mark.asyncio
async def test_clear_session(mock_redis):
    mock_redis.delete = AsyncMock()
    mem = ShortTermMemory(redis_url="redis://fake")
    await mem.connect()
    await mem.clear("session1")
    mock_redis.delete.assert_called_once()
