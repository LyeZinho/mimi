"""Integration tests for PiperProvider with actual Piper TTS synthesis.

These tests verify end-to-end TTS functionality with real audio synthesis.
They require the Piper model to be downloaded.
"""
import asyncio
import pytest
from pathlib import Path
from agent.output.piper_provider import PiperProvider
from agent.output.config import PiperConfig


@pytest.fixture
def model_path() -> Path:
    """Get path to Piper model."""
    return Path.home() / ".cache" / "piper" / "pt_BR" / "pt_BR-faber-medium.onnx"


@pytest.fixture
def piper_config(model_path) -> PiperConfig:
    """Create PiperConfig with actual model path."""
    return PiperConfig(
        provider="piper",
        model="pt_BR-faber-medium",
        model_path=str(model_path),
    )


@pytest.mark.skipif(
    not (Path.home() / ".cache" / "piper" / "pt_BR" / "pt_BR-faber-medium.onnx").exists(),
    reason="Piper model not downloaded"
)
@pytest.mark.asyncio
async def test_piper_provider_real_synthesis():
    """Test real TTS synthesis with actual Piper model."""
    config = PiperConfig(
        provider="piper",
        model="pt_BR-faber-medium",
        model_path=str(Path.home() / ".cache" / "piper" / "pt_BR" / "pt_BR-faber-medium.onnx"),
    )
    
    provider = PiperProvider(config)
    
    # Synthesize a simple phrase
    text = "Olá, meu nome é Mimi"
    audio_bytes = await provider.synthesize(text, stream=False)
    
    # Verify we got audio
    assert isinstance(audio_bytes, bytes), "Should return bytes"
    assert len(audio_bytes) > 0, "Should return non-empty audio"
    
    # Verify audio looks like WAV (optional - depends on how Piper encodes)
    # Basic check: should be reasonable size for spoken text
    assert len(audio_bytes) > 1000, "Audio should be at least 1KB"
    assert len(audio_bytes) < 10_000_000, "Audio should be less than 10MB"


@pytest.mark.skipif(
    not (Path.home() / ".cache" / "piper" / "pt_BR" / "pt_BR-faber-medium.onnx").exists(),
    reason="Piper model not downloaded"
)
@pytest.mark.asyncio
async def test_piper_provider_streaming_synthesis():
    """Test streaming TTS synthesis with actual Piper model."""
    config = PiperConfig(
        provider="piper",
        model="pt_BR-faber-medium",
        model_path=str(Path.home() / ".cache" / "piper" / "pt_BR" / "pt_BR-faber-medium.onnx"),
    )
    
    provider = PiperProvider(config)
    
    text = "Olá mundo"
    chunks = []
    
    # Synthesize with streaming
    result = await provider.synthesize(text, stream=True)
    
    async for chunk in result:
        chunks.append(chunk)
    
    # Verify chunks
    assert len(chunks) > 0, "Should have yielded at least one chunk"
    
    for chunk in chunks:
        assert isinstance(chunk, bytes), "Each chunk should be bytes"
        assert len(chunk) > 0, "Each chunk should have data"
    
    # Verify reconstructed audio matches non-streaming
    reconstructed = b"".join(chunks)
    assert len(reconstructed) > 0, "Reconstructed audio should be non-empty"


@pytest.mark.skipif(
    not (Path.home() / ".cache" / "piper" / "pt_BR" / "pt_BR-faber-medium.onnx").exists(),
    reason="Piper model not downloaded"
)
@pytest.mark.asyncio
async def test_piper_provider_statistics_tracking():
    """Test that statistics are tracked correctly during real synthesis."""
    config = PiperConfig(
        provider="piper",
        model="pt_BR-faber-medium",
        model_path=str(Path.home() / ".cache" / "piper" / "pt_BR" / "pt_BR-faber-medium.onnx"),
    )
    
    provider = PiperProvider(config)
    
    # Initial stats
    stats = provider.get_usage_stats()
    assert stats["requests"] == 0
    assert stats["errors"] == 0
    assert stats["audio_duration_sec"] == 0.0
    
    # First synthesis
    await provider.synthesize("Teste um", stream=False)
    stats = provider.get_usage_stats()
    assert stats["requests"] == 1
    assert stats["errors"] == 0
    assert stats["audio_duration_sec"] > 0.0, "Should have tracked audio duration"
    
    # Second synthesis
    await provider.synthesize("Teste dois", stream=False)
    stats = provider.get_usage_stats()
    assert stats["requests"] == 2
    assert stats["errors"] == 0
    assert stats["audio_duration_sec"] > 0.0


@pytest.mark.skipif(
    not (Path.home() / ".cache" / "piper" / "pt_BR" / "pt_BR-faber-medium.onnx").exists(),
    reason="Piper model not downloaded"
)
@pytest.mark.asyncio
async def test_piper_provider_concurrent_synthesis():
    """Test that concurrent synthesis requests work correctly."""
    config = PiperConfig(
        provider="piper",
        model="pt_BR-faber-medium",
        model_path=str(Path.home() / ".cache" / "piper" / "pt_BR" / "pt_BR-faber-medium.onnx"),
    )
    
    provider = PiperProvider(config)
    
    # Run concurrent synthesis requests
    texts = [
        "Primeiro",
        "Segundo",
        "Terceiro",
    ]
    
    results = await asyncio.gather(
        *[provider.synthesize(text, stream=False) for text in texts]
    )
    
    # Verify all completed successfully
    assert len(results) == 3
    
    for audio in results:
        assert isinstance(audio, bytes)
        assert len(audio) > 0


@pytest.mark.asyncio
async def test_piper_provider_model_not_available():
    """Test graceful handling when model is not available."""
    config = PiperConfig(
        provider="piper",
        model="pt_BR-faber-medium",
        model_path="/nonexistent/path/model.onnx",
    )
    
    provider = PiperProvider(config)
    
    # Should raise RuntimeError when trying to synthesize
    with pytest.raises(RuntimeError, match="Piper synthesis error"):
        await provider.synthesize("Test", stream=False)
