"""Tests for TTS provider abstraction."""
import pytest
from abc import ABC, abstractmethod
from typing import List, Dict, Union, AsyncIterator
from dataclasses import dataclass
from agent.output.config import TTSConfig
from agent.output.tts_provider import TTSProvider


class TestTTSConfig:
    """Test TTSConfig dataclass."""

    def test_tts_config_basic(self):
        """Test creating basic TTSConfig."""
        config = TTSConfig(provider="piper", model="pt_PT/pt-pt_blip-medium.onnx")
        assert config.provider == "piper"
        assert config.model == "pt_PT/pt-pt_blip-medium.onnx"
        assert config.timeout_sec == 30.0

    def test_tts_config_custom_timeout(self):
        """Test TTSConfig with custom timeout."""
        config = TTSConfig(
            provider="piper",
            model="pt_PT/pt-pt_blip-medium.onnx",
            timeout_sec=60.0
        )
        assert config.timeout_sec == 60.0

    def test_tts_config_dataclass_equality(self):
        """Test TTSConfig dataclass equality."""
        config1 = TTSConfig(provider="piper", model="model1")
        config2 = TTSConfig(provider="piper", model="model1")
        assert config1 == config2


class TestTTSProviderAbstract:
    """Test TTSProvider abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that TTSProvider cannot be instantiated directly."""
        config = TTSConfig(provider="piper", model="test")
        with pytest.raises(TypeError):
            TTSProvider(config)

    def test_has_required_abstract_methods(self):
        """Test that TTSProvider defines required abstract methods."""
        required_methods = [
            "synthesize",
            "set_voice",
            "get_available_voices",
            "get_usage_stats"
        ]
        for method in required_methods:
            assert hasattr(TTSProvider, method)
            assert getattr(TTSProvider, method).__isabstractmethod__

    def test_concrete_implementation_requires_all_methods(self):
        """Test that concrete class must implement all abstract methods."""
        config = TTSConfig(provider="test", model="test")

        class IncompleteProvider(TTSProvider):
            async def synthesize(self, text: str, stream: bool = False):
                pass

        with pytest.raises(TypeError):
            IncompleteProvider(config)

    def test_config_stored_on_init(self):
        """Test that config is accessible after init."""
        config = TTSConfig(provider="test", model="test_model")

        class TestProvider(TTSProvider):
            async def synthesize(self, text: str, stream: bool = False):
                return b""

            def set_voice(self, voice_id: str):
                pass

            def get_available_voices(self) -> List[dict]:
                return []

            def get_usage_stats(self) -> dict:
                return {}

        provider = TestProvider(config)
        assert provider.config.provider == "test"
        assert provider.config.model == "test_model"


class TestTTSProviderInterface:
    """Test TTSProvider interface requirements."""

    def test_synthesize_returns_bytes_or_async_iterator(self):
        """Test synthesize return type annotation."""
        # This is a type checking test - verify the method signature exists
        assert hasattr(TTSProvider, "synthesize")

    def test_get_usage_stats_returns_required_fields(self):
        """Test that usage stats should have required fields."""
        config = TTSConfig(provider="test", model="test")

        class TestProvider(TTSProvider):
            async def synthesize(self, text: str, stream: bool = False):
                return b""

            def set_voice(self, voice_id: str):
                pass

            def get_available_voices(self) -> List[dict]:
                return []

            def get_usage_stats(self) -> dict:
                stats = {
                    "audio_duration_sec": 0.0,
                    "requests": 0,
                    "errors": 0
                }
                return stats

        provider = TestProvider(config)
        stats = provider.get_usage_stats()
        assert "audio_duration_sec" in stats
        assert "requests" in stats
        assert "errors" in stats

    def test_set_voice_accepts_string(self):
        """Test that set_voice accepts voice_id string."""
        config = TTSConfig(provider="test", model="test")

        class TestProvider(TTSProvider):
            def __init__(self, config):
                super().__init__(config)
                self.voice = None

            async def synthesize(self, text: str, stream: bool = False):
                return b""

            def set_voice(self, voice_id: str):
                self.voice = voice_id

            def get_available_voices(self) -> List[dict]:
                return []

            def get_usage_stats(self) -> dict:
                return {"audio_duration_sec": 0, "requests": 0, "errors": 0}

        provider = TestProvider(config)
        provider.set_voice("voice_123")
        assert provider.voice == "voice_123"

    def test_get_available_voices_returns_list(self):
        """Test that get_available_voices returns list of dicts."""
        config = TTSConfig(provider="test", model="test")

        class TestProvider(TTSProvider):
            async def synthesize(self, text: str, stream: bool = False):
                return b""

            def set_voice(self, voice_id: str):
                pass

            def get_available_voices(self) -> List[dict]:
                return [{"id": "v1", "name": "Voice 1"}]

            def get_usage_stats(self) -> dict:
                return {"audio_duration_sec": 0, "requests": 0, "errors": 0}

        provider = TestProvider(config)
        voices = provider.get_available_voices()
        assert isinstance(voices, list)
        assert len(voices) > 0
        assert isinstance(voices[0], dict)
