import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from agent.output.piper_provider import PiperProvider
from agent.output.config import PiperConfig


class MockAudioChunk:
    """Mock audio chunk from Piper voice synthesis."""
    def __init__(self, audio: bytes, sample_rate: int = 22050):
        self.audio_int16_bytes = audio
        self.sample_rate = sample_rate
        self.phonemes = []
        self.phoneme_id_samples = None
    
    def sample_count(self) -> int:
        """Calculate number of samples (16-bit PCM)."""
        return len(self.audio_int16_bytes) // 2


@pytest.mark.asyncio
async def test_piper_provider_synthesize_streaming():
    """Test that PiperProvider.synthesize with stream=True returns proper AsyncIterator."""
    
    config = PiperConfig(provider="piper", model="pt_PT")
    
    with patch('agent.output.piper_provider.PiperVoice') as mock_piper_voice_class:
        # Mock the voice instance
        mock_voice = MagicMock()
        mock_piper_voice_class.load.return_value = mock_voice
        
        # Create test audio and split into chunks for mock
        test_audio = b"x" * 5000
        audio_chunks = [
            MockAudioChunk(test_audio[i:i+2048], sample_rate=22050)
            for i in range(0, len(test_audio), 2048)
        ]
        mock_voice.synthesize.return_value = audio_chunks
        
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
        
        # All but last chunk should be 1024 bytes (streaming chunk size)
        for chunk in chunks[:-1]:
            assert len(chunk) == 1024, f"Chunk size should be 1024, got {len(chunk)}"


@pytest.mark.asyncio
async def test_piper_provider_synthesize_non_streaming():
    """Test that PiperProvider.synthesize with stream=False returns bytes."""
    
    config = PiperConfig(provider="piper", model="pt_PT")
    
    with patch('agent.output.piper_provider.PiperVoice') as mock_piper_voice_class:
        mock_voice = MagicMock()
        mock_piper_voice_class.load.return_value = mock_voice
        
        test_audio = b"x" * 5000
        audio_chunks = [
            MockAudioChunk(test_audio[i:i+2048], sample_rate=22050)
            for i in range(0, len(test_audio), 2048)
        ]
        mock_voice.synthesize.return_value = audio_chunks
        
        provider = PiperProvider(config)
        
        result = await provider.synthesize("Test text", stream=False)
        
        assert isinstance(result, bytes), "Result should be bytes when stream=False"
        assert result == test_audio, "Result should equal synthesized audio"


@pytest.mark.asyncio
async def test_piper_provider_empty_text_raises_error():
    """Test that PiperProvider raises ValueError for empty text."""
    
    config = PiperConfig(provider="piper", model="pt_PT")
    
    with patch('agent.output.piper_provider.PiperVoice'):
        provider = PiperProvider(config)
        
        with pytest.raises(ValueError, match="Text cannot be empty"):
            await provider.synthesize("", stream=False)
        
        with pytest.raises(ValueError, match="Text cannot be empty"):
            await provider.synthesize("   ", stream=True)


@pytest.mark.asyncio
async def test_piper_provider_usage_stats():
    """Test that PiperProvider tracks usage statistics."""
    
    config = PiperConfig(provider="piper", model="pt_PT")
    
    with patch('agent.output.piper_provider.PiperVoice') as mock_piper_voice_class:
        mock_voice = MagicMock()
        mock_piper_voice_class.load.return_value = mock_voice
        
        test_audio = b"x" * 2048
        audio_chunks = [MockAudioChunk(test_audio, sample_rate=22050)]
        mock_voice.synthesize.return_value = audio_chunks
        
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
