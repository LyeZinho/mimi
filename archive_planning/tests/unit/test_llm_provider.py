"""
Unit tests for LLM Provider abstract base class.
Following TDD approach: tests first, implementation after.
"""
import pytest
from abc import ABC
from agent.llm.config import LLMConfig
from agent.llm.provider import LLMProvider


class TestCannotInstantiateAbstract:
    """Test that LLMProvider cannot be instantiated directly."""

    def test_cannot_instantiate_abstract(self):
        """Test that attempting to instantiate LLMProvider raises TypeError."""
        config = LLMConfig(provider="test", model="test-model")
        
        with pytest.raises(TypeError, match="abstract"):
            LLMProvider(config)


class ConcreteProvider(LLMProvider):
    """Concrete implementation for testing."""

    async def generate(self, prompt, stream=False):
        """Dummy generate implementation."""
        return "generated response"

    def count_tokens(self, text):
        """Dummy count_tokens implementation."""
        return len(text.split())

    async def validate_connection(self):
        """Dummy validate_connection implementation."""
        return True


class TestConcreteProviderWorks:
    """Test that concrete implementations of LLMProvider work."""

    def test_concrete_provider_works(self):
        """Test that concrete provider can be instantiated and used."""
        config = LLMConfig(provider="test", model="test-model")
        provider = ConcreteProvider(config)
        
        # Verify it's an instance of LLMProvider
        assert isinstance(provider, LLMProvider)
        assert isinstance(provider, ABC)
        
        # Verify config is stored
        assert provider.config == config
        assert provider.config.provider == "test"
        assert provider.config.model == "test-model"


class TestTokenCountTracking:
    """Test token counting tracking mechanism."""

    def test_token_count_tracking(self):
        """Test that token counts are tracked and updated."""
        config = LLMConfig(provider="test", model="test-model")
        provider = ConcreteProvider(config)
        
        # Initial state
        assert provider.token_count_in == 0
        assert provider.token_count_out == 0
        assert provider.request_count == 0
        assert provider.error_count == 0
        assert provider.total_latency_ms == 0.0
        
        # Can update token counts (for tracking purposes)
        provider.token_count_in = 10
        provider.token_count_out = 20
        provider.request_count = 1
        provider.total_latency_ms = 150.5
        
        assert provider.token_count_in == 10
        assert provider.token_count_out == 20
        assert provider.request_count == 1
        assert provider.total_latency_ms == 150.5


class TestHasRequiredMethods:
    """Test that LLMProvider defines required abstract methods."""

    def test_has_required_methods(self):
        """Test that LLMProvider has all required abstract methods."""
        config = LLMConfig(provider="test", model="test-model")
        provider = ConcreteProvider(config)
        
        # Verify abstract methods exist
        assert hasattr(provider, 'generate')
        assert callable(provider.generate)
        
        assert hasattr(provider, 'count_tokens')
        assert callable(provider.count_tokens)
        
        assert hasattr(provider, 'validate_connection')
        assert callable(provider.validate_connection)
        
        # Verify get_usage_stats exists (concrete method)
        assert hasattr(provider, 'get_usage_stats')
        assert callable(provider.get_usage_stats)


class TestGetUsageStats:
    """Test get_usage_stats concrete method."""

    def test_get_usage_stats_returns_dict(self):
        """Test that get_usage_stats returns dict with correct keys."""
        config = LLMConfig(provider="openai", model="gpt-4")
        provider = ConcreteProvider(config)
        
        # Simulate some usage
        provider.token_count_in = 100
        provider.token_count_out = 50
        provider.request_count = 5
        provider.error_count = 1
        provider.total_latency_ms = 2500.0
        
        stats = provider.get_usage_stats()
        
        # Verify it returns dict with required keys
        assert isinstance(stats, dict)
        assert 'provider' in stats
        assert 'model' in stats
        assert 'tokens_in' in stats
        assert 'tokens_out' in stats
        assert 'requests' in stats
        assert 'errors' in stats
        assert 'avg_latency_ms' in stats
        
        # Verify values
        assert stats['provider'] == 'openai'
        assert stats['model'] == 'gpt-4'
        assert stats['tokens_in'] == 100
        assert stats['tokens_out'] == 50
        assert stats['requests'] == 5
        assert stats['errors'] == 1
        assert stats['avg_latency_ms'] == 500.0  # 2500 / 5

    def test_get_usage_stats_avg_latency_zero_requests(self):
        """Test avg_latency_ms when no requests made."""
        config = LLMConfig(provider="test", model="test-model")
        provider = ConcreteProvider(config)
        
        stats = provider.get_usage_stats()
        
        # Should handle zero requests gracefully
        assert stats['avg_latency_ms'] == 0.0
