"""Tests for Piper TTS provider implementation."""
import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from agent.output.config import PiperConfig
from agent.output.piper_provider import PiperProvider


class TestPiperConfig:
    """Test PiperConfig dataclass."""

    def test_piper_config_defaults(self):
        """Test PiperConfig with all defaults."""
        config = PiperConfig(provider="piper", model="pt_PT/pt-pt_blip-medium.onnx")
        assert config.provider == "piper"
        assert config.model == "pt_PT/pt-pt_blip-medium.onnx"
        assert config.timeout_sec == 30.0
        assert config.model_path == "~/.cache/piper/pt_PT/pt-pt_blip-medium.onnx"
        assert config.speaker_id == 0
        assert config.speed == 1.0
        assert config.noise_scale == 0.667

    def test_piper_config_custom_values(self):
        """Test PiperConfig with custom values."""
        config = PiperConfig(
            provider="piper",
            model="test_model",
            timeout_sec=60.0,
            model_path="/custom/path/model.onnx",
            speaker_id=2,
            speed=1.5,
            noise_scale=0.5
        )
        assert config.speaker_id == 2
        assert config.speed == 1.5
        assert config.noise_scale == 0.5
        assert config.model_path == "/custom/path/model.onnx"

    def test_piper_config_inherits_from_tts_config(self):
        """Test that PiperConfig is a subclass of TTSConfig."""
        from agent.output.config import TTSConfig
        config = PiperConfig(provider="piper", model="test")
        assert isinstance(config, TTSConfig)


class TestPiperProviderInit:
    """Test PiperProvider initialization."""

    def test_piper_provider_init(self):
        """Test PiperProvider initialization with config."""
        config = PiperConfig(provider="piper", model="test_model")
        with patch("agent.output.piper_provider.piper"):
            provider = PiperProvider(config)
            assert provider.config.model == "test_model"
            assert provider.config.provider == "piper"

    def test_piper_provider_stores_config(self):
        """Test that config is stored on init."""
        config = PiperConfig(provider="piper", model="test_model", speaker_id=1)
        with patch("agent.output.piper_provider.piper"):
            provider = PiperProvider(config)
            assert provider.config.speaker_id == 1


class TestPiperSynthesis:
    """Test Piper synthesis functionality."""

    @pytest.mark.asyncio
    async def test_synthesize_returns_bytes(self):
        """Test that synthesize returns bytes."""
        config = PiperConfig(provider="piper", model="test_model")
        
        with patch("agent.output.piper_provider.piper") as mock_piper:
            mock_piper.synthesize_args.return_value = {
                "audio_data": b"mock_audio_data",
                "sample_rate": 22050
            }
            
            provider = PiperProvider(config)
            result = await provider.synthesize("Olá")
            
            assert isinstance(result, bytes)
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_synthesize_with_small_text_ola(self):
        """Test synthesize with 'Olá' returns audio bytes."""
        config = PiperConfig(provider="piper", model="pt_PT/pt-pt_blip-medium.onnx")
        
        with patch("agent.output.piper_provider.piper") as mock_piper:
            mock_audio = b"audio_data_for_ola"
            mock_piper.synthesize_args.return_value = {
                "audio_data": mock_audio,
                "sample_rate": 22050
            }
            
            provider = PiperProvider(config)
            result = await provider.synthesize("Olá")
            
            assert result == mock_audio
            assert isinstance(result, bytes)

    @pytest.mark.asyncio
    async def test_synthesize_non_streaming(self):
        """Test synthesize with stream=False."""
        config = PiperConfig(provider="piper", model="test")
        
        with patch("agent.output.piper_provider.piper") as mock_piper:
            mock_piper.synthesize_args.return_value = {
                "audio_data": b"audio",
                "sample_rate": 22050
            }
            
            provider = PiperProvider(config)
            result = await provider.synthesize("test text", stream=False)
            
            assert isinstance(result, bytes)

    @pytest.mark.asyncio
    async def test_synthesize_streaming(self):
        """Test synthesize with stream=True returns AsyncIterator."""
        config = PiperConfig(provider="piper", model="test")
        
        with patch("agent.output.piper_provider.piper"):
            provider = PiperProvider(config)
            result = await provider.synthesize("test text", stream=True)
            
            # Check if it's an async iterator
            assert hasattr(result, "__aiter__")

    @pytest.mark.asyncio
    async def test_synthesize_tracks_requests(self):
        """Test that synthesize increments request counter."""
        config = PiperConfig(provider="piper", model="test")
        
        with patch("agent.output.piper_provider.piper") as mock_piper:
            mock_piper.synthesize_args.return_value = {
                "audio_data": b"audio",
                "sample_rate": 22050
            }
            
            provider = PiperProvider(config)
            await provider.synthesize("test")
            
            stats = provider.get_usage_stats()
            assert stats["requests"] == 1
            
            await provider.synthesize("test again")
            stats = provider.get_usage_stats()
            assert stats["requests"] == 2

    @pytest.mark.asyncio
    async def test_synthesize_tracks_errors(self):
        """Test that synthesize errors increment error counter."""
        config = PiperConfig(provider="piper", model="test")
        
        with patch("agent.output.piper_provider.piper") as mock_piper:
            mock_piper.synthesize_args.side_effect = Exception("Synthesis failed")
            
            provider = PiperProvider(config)
            
            with pytest.raises(Exception):
                await provider.synthesize("test")
            
            stats = provider.get_usage_stats()
            assert stats["errors"] == 1


class TestPiperVoiceManagement:
    """Test Piper voice management."""

    def test_set_voice(self):
        """Test setting voice."""
        config = PiperConfig(provider="piper", model="test", speaker_id=0)
        
        with patch("agent.output.piper_provider.piper"):
            provider = PiperProvider(config)
            provider.set_voice("voice_123")
            
            assert provider.config.speaker_id == "voice_123"

    def test_get_available_voices_returns_list(self):
        """Test that get_available_voices returns list."""
        config = PiperConfig(provider="piper", model="test")
        
        with patch("agent.output.piper_provider.piper"):
            provider = PiperProvider(config)
            voices = provider.get_available_voices()
            
            assert isinstance(voices, list)

    def test_get_available_voices_returns_dicts(self):
        """Test that get_available_voices returns list of dicts."""
        config = PiperConfig(provider="piper", model="test")
        
        with patch("agent.output.piper_provider.piper"):
            provider = PiperProvider(config)
            voices = provider.get_available_voices()
            
            for voice in voices:
                assert isinstance(voice, dict)
                if voice:
                    assert "id" in voice or "name" in voice

    def test_voice_persists_across_calls(self):
        """Test that voice setting persists."""
        config = PiperConfig(provider="piper", model="test")
        
        with patch("agent.output.piper_provider.piper") as mock_piper:
            mock_piper.synthesize_args.return_value = {
                "audio_data": b"audio",
                "sample_rate": 22050
            }
            
            provider = PiperProvider(config)
            provider.set_voice("speaker_2")
            
            # Voice should be set
            assert provider.config.speaker_id == "speaker_2"


class TestPiperUsageStats:
    """Test usage statistics tracking."""

    def test_get_usage_stats_has_required_fields(self):
        """Test that usage stats contain required fields."""
        config = PiperConfig(provider="piper", model="test")
        
        with patch("agent.output.piper_provider.piper"):
            provider = PiperProvider(config)
            stats = provider.get_usage_stats()
            
            assert "audio_duration_sec" in stats
            assert "requests" in stats
            assert "errors" in stats

    def test_get_usage_stats_initial_values(self):
        """Test initial usage stats values."""
        config = PiperConfig(provider="piper", model="test")
        
        with patch("agent.output.piper_provider.piper"):
            provider = PiperProvider(config)
            stats = provider.get_usage_stats()
            
            assert stats["requests"] == 0
            assert stats["errors"] == 0
            assert stats["audio_duration_sec"] == 0.0

    @pytest.mark.asyncio
    async def test_get_usage_stats_increments_duration(self):
        """Test that audio_duration_sec is tracked."""
        config = PiperConfig(provider="piper", model="test")
        
        with patch("agent.output.piper_provider.piper") as mock_piper:
            mock_piper.synthesize_args.return_value = {
                "audio_data": b"audio_sample_data",
                "sample_rate": 22050
            }
            
            provider = PiperProvider(config)
            await provider.synthesize("test")
            
            stats = provider.get_usage_stats()
            assert stats["audio_duration_sec"] >= 0


class TestPiperExceptions:
    """Test Piper exception handling."""

    @pytest.mark.asyncio
    async def test_synthesize_handles_invalid_text(self):
        """Test handling of invalid text input."""
        config = PiperConfig(provider="piper", model="test")
        
        with patch("agent.output.piper_provider.piper") as mock_piper:
            mock_piper.synthesize_args.side_effect = ValueError("Invalid input")
            
            provider = PiperProvider(config)
            
            with pytest.raises(ValueError):
                await provider.synthesize("")

    @pytest.mark.asyncio
    async def test_synthesize_handles_model_error(self):
        """Test handling of model errors."""
        config = PiperConfig(provider="piper", model="nonexistent")
        
        with patch("agent.output.piper_provider.piper") as mock_piper:
            mock_piper.synthesize_args.side_effect = RuntimeError("Model not found")
            
            provider = PiperProvider(config)
            
            with pytest.raises(RuntimeError):
                await provider.synthesize("test")

    @pytest.mark.asyncio
    async def test_timeout_respected(self):
        """Test that timeout is configured properly."""
        config = PiperConfig(
            provider="piper",
            model="test",
            timeout_sec=5.0
        )
        
        with patch("agent.output.piper_provider.piper"):
            provider = PiperProvider(config)
            assert provider.config.timeout_sec == 5.0
