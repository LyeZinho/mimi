import pytest
from agent.memory.long_term import LongTermMemory
from agent.schemas import MemoryEntry

@pytest.fixture
async def mem(tmp_path):
    db_path = str(tmp_path / "test.db")
    m = LongTermMemory(db_path=db_path)
    await m.connect()
    yield m
    await m.disconnect()

@pytest.mark.asyncio
async def test_save_and_load(mem):
    entry = MemoryEntry(role="user", content="remember this")
    await mem.save("session1", entry)
    results = await mem.load("session1", limit=10)
    assert len(results) == 1
    assert results[0].content == "remember this"

@pytest.mark.asyncio
async def test_load_empty_session(mem):
    results = await mem.load("nonexistent", limit=10)
    assert results == []

@pytest.mark.asyncio
async def test_load_respects_limit(mem):
    for i in range(5):
        await mem.save("s", MemoryEntry(role="user", content=f"msg {i}"))
    results = await mem.load("s", limit=3)
    assert len(results) == 3
