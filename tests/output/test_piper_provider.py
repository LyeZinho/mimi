import asyncio
import pytest
from unittest.mock import patch, MagicMock
from agent.output.piper_provider import PiperProvider
from agent.output.config import PiperConfig


@pytest.mark.asyncio
async def test_piper_provider_synthesize_streaming():
    """Test that PiperProvider.synthesize with stream=True returns proper AsyncIterator."""
    
    config = PiperConfig(provider="piper", model="pt_PT")
    
    with patch('agent.output.piper_provider.piper') as mock_piper:
        test_audio = b"x" * 5000
        mock_piper.synthesize_args.return_value = {
            "audio_data": test_audio,
            "sample_rate": 22050,
        }
        
        provider = PiperProvider(config)
        
        result = await provider.synthesize("Test text", stream=True)
        
        assert hasattr(result, '__aiter__'), "Result should be an async iterator"
        
        chunks = []
        async for chunk in result:
            chunks.append(chunk)
        
        assert len(chunks) > 0, "Should have yielded at least one chunk"
        
        for chunk in chunks:
            assert isinstance(chunk, bytes), f"Each chunk should be bytes, got {type(chunk)}"
        
        full_reconstructed = b"".join(chunks)
        assert full_reconstructed == test_audio, "Concatenated chunks should equal original audio"
        
        for chunk in chunks[:-1]:
            assert len(chunk) == 1024, f"Chunk size should be 1024, got {len(chunk)}"


@pytest.mark.asyncio
async def test_piper_provider_synthesize_non_streaming():
    """Test that PiperProvider.synthesize with stream=False returns bytes."""
    
    config = PiperConfig(provider="piper", model="pt_PT")
    
    with patch('agent.output.piper_provider.piper') as mock_piper:
        test_audio = b"x" * 5000
        mock_piper.synthesize_args.return_value = {
            "audio_data": test_audio,
            "sample_rate": 22050,
        }
        
        provider = PiperProvider(config)
        
        result = await provider.synthesize("Test text", stream=False)
        
        assert isinstance(result, bytes), "Result should be bytes when stream=False"
        assert result == test_audio, "Result should equal synthesized audio"


@pytest.mark.asyncio
async def test_piper_provider_empty_text_raises_error():
    """Test that PiperProvider raises ValueError for empty text."""
    
    config = PiperConfig(provider="piper", model="pt_PT")
    
    with patch('agent.output.piper_provider.piper'):
        provider = PiperProvider(config)
        
        with pytest.raises(ValueError, match="Text cannot be empty"):
            await provider.synthesize("", stream=False)
        
        with pytest.raises(ValueError, match="Text cannot be empty"):
            await provider.synthesize("   ", stream=True)


@pytest.mark.asyncio
async def test_piper_provider_usage_stats():
    """Test that PiperProvider tracks usage statistics."""
    
    config = PiperConfig(provider="piper", model="pt_PT")
    
    with patch('agent.output.piper_provider.piper') as mock_piper:
        test_audio = b"x" * 2048  
        mock_piper.synthesize_args.return_value = {
            "audio_data": test_audio,
            "sample_rate": 22050,
        }
        
        provider = PiperProvider(config)
        
        initial_stats = provider.get_usage_stats()
        assert initial_stats["requests"] == 0
        assert initial_stats["errors"] == 0
        
        await provider.synthesize("Test", stream=False)
        
        stats = provider.get_usage_stats()
        assert stats["requests"] == 1
        assert stats["errors"] == 0
        
        try:
            await provider.synthesize("", stream=False)
        except ValueError:
            pass
        
        stats = provider.get_usage_stats()
        assert stats["requests"] == 1
        assert stats["errors"] == 1
