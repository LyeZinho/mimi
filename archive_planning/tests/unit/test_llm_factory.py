"""Tests for LLMProviderFactory."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from agent.llm.factory import LLMProviderFactory
from agent.llm.config import LLMConfig, OllamaConfig
from agent.llm.ollama_provider import OllamaProvider
from agent.llm.errors import LLMValidationError


class TestFactoryCreatesOllama:
    """Test that factory creates OllamaProvider when config.provider is 'ollama'."""

    @pytest.mark.asyncio
    async def test_factory_creates_ollama(self):
        config = OllamaConfig(
            provider="ollama",
            model="phi3:mini",
            host="http://localhost:11434",
            temperature=0.7,
            top_p=0.9
        )

        provider = await LLMProviderFactory.create(config)

        assert isinstance(provider, OllamaProvider)
        assert provider.config.provider == "ollama"
        assert provider.config.model == "phi3:mini"


class TestFactoryValidatesConnection:
    """Test that factory validates connection and logs warning if fails."""

    @pytest.mark.asyncio
    async def test_factory_validates_connection(self):
        config = OllamaConfig(
            provider="ollama",
            model="phi3:mini",
            host="http://localhost:11434"
        )

        with patch.object(OllamaProvider, 'validate_connection', new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = True

            provider = await LLMProviderFactory.create(config)

            mock_validate.assert_called_once()
            assert isinstance(provider, OllamaProvider)


class TestFactoryUnknownProvider:
    """Test that factory raises LLMValidationError for unknown provider."""

    @pytest.mark.asyncio
    async def test_factory_unknown_provider(self):
        config = LLMConfig(provider="unknown_provider", model="test-model")

        with pytest.raises(LLMValidationError) as exc_info:
            await LLMProviderFactory.create(config)

        assert "unknown_provider" in str(exc_info.value)


class TestFactoryIsSingleton:
    """Test that factory class is stateless (not instance-based)."""

    def test_factory_is_singleton(self):
        # Factory should only have static methods, no instance methods
        # Check that register_provider and create are static/class methods
        assert hasattr(LLMProviderFactory, 'create')
        assert hasattr(LLMProviderFactory, 'register_provider')
        
        # Verify _PROVIDERS dict exists and has ollama
        assert hasattr(LLMProviderFactory, '_PROVIDERS')
        assert 'ollama' in LLMProviderFactory._PROVIDERS
        assert LLMProviderFactory._PROVIDERS['ollama'] == OllamaProvider
