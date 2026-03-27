"""Tests for LLM usage statistics tracking."""

import pytest
from agent.llm.usage_tracker import UsageStats


class TestUsageStats:
    """Test UsageStats dataclass."""

    def test_usage_stats_initialization(self):
        """Test that UsageStats initializes with correct defaults."""
        stats = UsageStats(provider="openai", model="gpt-4")
        
        assert stats.provider == "openai"
        assert stats.model == "gpt-4"
        assert stats.tokens_in == 0
        assert stats.tokens_out == 0
        assert stats.requests == 0
        assert stats.errors == 0
        assert stats.total_latency_ms == 0.0

    def test_avg_latency_calculation(self):
        """Test that avg_latency_ms calculates correctly with requests."""
        stats = UsageStats(
            provider="openai",
            model="gpt-4",
            requests=5,
            total_latency_ms=1000.0
        )
        
        assert stats.avg_latency_ms == 200.0

    def test_avg_latency_with_no_requests(self):
        """Test that avg_latency_ms returns 0.0 when requests=0."""
        stats = UsageStats(
            provider="openai",
            model="gpt-4",
            total_latency_ms=1000.0
        )
        
        assert stats.avg_latency_ms == 0.0

    def test_total_tokens(self):
        """Test that total_tokens property sums input and output tokens."""
        stats = UsageStats(
            provider="openai",
            model="gpt-4",
            tokens_in=150,
            tokens_out=250
        )
        
        assert stats.total_tokens == 400

    def test_stats_summary_string(self):
        """Test error_rate property calculation."""
        stats = UsageStats(
            provider="openai",
            model="gpt-4",
            requests=10,
            errors=2
        )
        
        assert stats.error_rate == 20.0

    def test_error_rate_with_no_requests(self):
        """Test that error_rate returns 0.0 when requests=0."""
        stats = UsageStats(
            provider="openai",
            model="gpt-4",
            errors=5
        )
        
        assert stats.error_rate == 0.0

    def test_get_summary(self):
        """Test get_summary() returns properly formatted string."""
        stats = UsageStats(
            provider="openai",
            model="gpt-4",
            tokens_in=150,
            tokens_out=250,
            requests=10,
            errors=1,
            total_latency_ms=2500.0
        )
        
        summary = stats.get_summary()
        
        # Verify format includes all required components
        assert "LLM Usage:" in summary
        assert "openai/gpt-4" in summary
        assert "Tokens: In=150 Out=250 Total=400" in summary
        assert "Requests=10" in summary
        assert "Errors=1" in summary
        assert "10.0% error rate" in summary
        assert "Avg Latency: 250ms" in summary
