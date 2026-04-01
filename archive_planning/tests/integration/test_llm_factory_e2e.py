"""End-to-end integration tests for LLM factory and providers."""
import pytest
from agent.llm.factory import LLMProviderFactory
from agent.llm.config import OllamaConfig


@pytest.mark.asyncio
class TestLLMFactoryE2E:
    """End-to-end tests for LLM provider factory and integration."""

    async def test_factory_creates_valid_provider(self):
        """Test factory creates valid provider with correct config and initial stats."""
        config = OllamaConfig(
            provider="ollama",
            model="phi3:mini",
            host="http://localhost:11434"
        )

        provider = await LLMProviderFactory.create(config)

        assert provider is not None
        assert provider.config.model == "phi3:mini"
        assert provider.request_count == 0

    async def test_provider_tracks_stats(self):
        """Test provider tracks usage statistics correctly."""
        config = OllamaConfig(
            provider="ollama",
            model="phi3:mini",
            host="http://localhost:11434"
        )

        provider = await LLMProviderFactory.create(config)
        stats = provider.get_usage_stats()

        assert stats["provider"] == "ollama"
        assert stats["model"] == "phi3:mini"
        assert stats["requests"] == 0
        assert stats["errors"] == 0

    async def test_factory_cleanup(self):
        """Test provider cleanup resources without error."""
        config = OllamaConfig(
            provider="ollama",
            model="phi3:mini",
            host="http://localhost:11434"
        )

        provider = await LLMProviderFactory.create(config)

        if hasattr(provider, "close") and callable(provider.close):
            await provider.close()
