import asyncio
import pytest
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_output_brain_async_iterator_no_await():
    """Test that async iterator streaming works without await."""
    
    async def async_generator():
        yield b"chunk1"
        yield b"chunk2"

    def mock_synthesize(text, stream=False):
        if stream:
            return async_generator()
        return b"combined"
    
    result_streaming = mock_synthesize("test", stream=True)
    
    chunks = []
    async for chunk in result_streaming:
        chunks.append(chunk)
    
    assert len(chunks) == 2
    assert chunks[0] == b"chunk1"
    assert chunks[1] == b"chunk2"


@pytest.mark.asyncio
async def test_output_brain_fix_pattern():
    """Test the exact fix pattern used in OutputBrain._synthesize_and_stream."""
    
    class SimpleTTSProvider:
        def synthesize(self, text: str, stream: bool = False):
            if stream:
                async def chunks():
                    yield b"a"
                    yield b"b"
                return chunks()
            return b"ab"
    
    provider = SimpleTTSProvider()
    
    chunks_collected = []
    
    synthesize_result = provider.synthesize("test", stream=True)
    async for chunk in synthesize_result:  # type: ignore
        chunks_collected.append(chunk)
    
    assert len(chunks_collected) == 2
    assert b"".join(chunks_collected) == b"ab"
