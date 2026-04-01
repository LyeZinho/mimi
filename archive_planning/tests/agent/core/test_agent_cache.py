"""Unit tests for Agent response cache integration."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from agent.core.agent import AgentCore
from agent.core.memory import Memory
from agent.core.state import AgentState
from agent.core.response_cache import ResponseCache


class TestAgentCacheIntegration:
    """Tests for Agent cache integration."""

    @pytest.fixture
    def cache(self, tmp_path):
        """Provide ResponseCache with temp file."""
        return ResponseCache(tmp_path / "cache.json", ttl_seconds=3600)

    @pytest.fixture
    def agent(self, cache):
        """Provide AgentCore with mocked dependencies."""
        llm_mock = AsyncMock()
        router_mock = AsyncMock()
        
        agent = AgentCore(
            memory=Memory(),
            state=AgentState(),
            llm=llm_mock,
            router=router_mock,
            cache=cache
        )
        return agent

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_response(self, agent, cache):
        """Test that cache hit returns cached response without calling LLM."""
        text = "What is your name?"
        cached_response = {
            "status": "spoken",
            "text": "I'm Mimi!",
            "emotion": "happy"
        }
        
        key = ResponseCache.get_cache_key(text)
        cache.set(key, cached_response)
        cache.flush()
        
        result = await agent.handle_input(text)
        
        assert result == cached_response
        agent.llm.get_intent.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_miss_calls_llm(self, agent):
        """Test that cache miss calls LLM."""
        text = "What is your name?"
        
        agent.llm.get_intent.return_value = {
            "intent": "speak",
            "text": "I'm Mimi!",
            "emotion": "happy"
        }
        agent.router.execute.return_value = {
            "status": "spoken",
            "text": "I'm Mimi!",
            "emotion": "happy"
        }
        
        await agent.handle_input(text)
        
        agent.llm.get_intent.assert_called_once()

    @pytest.mark.asyncio
    async def test_response_cached_after_llm_call(self, agent, cache):
        """Test that new responses are cached after LLM call."""
        text = "What is your name?"
        response = {
            "status": "spoken",
            "text": "I'm Mimi!",
            "emotion": "happy"
        }
        
        agent.llm.get_intent.return_value = {
            "intent": "speak",
            "text": "I'm Mimi!",
            "emotion": "happy"
        }
        agent.router.execute.return_value = response
        
        await agent.handle_input(text)
        
        key = ResponseCache.get_cache_key(text)
        cached = cache.get(key)
        assert cached == response

    @pytest.mark.asyncio
    async def test_cache_key_from_user_input(self, agent, cache):
        """Test that cache key is derived from user input."""
        text = "Hello"
        response = {
            "status": "spoken",
            "text": "Hello!",
            "emotion": "happy"
        }
        
        agent.llm.get_intent.return_value = {
            "intent": "speak",
            "text": "Hello!",
            "emotion": "happy"
        }
        agent.router.execute.return_value = response
        
        await agent.handle_input(text)
        
        expected_key = ResponseCache.get_cache_key(text)
        cached = cache.get(expected_key)
        assert cached == response

    @pytest.mark.asyncio
    async def test_different_inputs_use_different_cache_keys(self, agent, cache):
        """Test that different inputs are cached separately."""
        text1 = "What is your name?"
        text2 = "What is your age?"
        
        response1 = {"status": "spoken", "text": "I'm Mimi!"}
        response2 = {"status": "spoken", "text": "I don't have an age!"}
        
        key1 = ResponseCache.get_cache_key(text1)
        key2 = ResponseCache.get_cache_key(text2)
        
        cache.set(key1, response1)
        cache.set(key2, response2)
        cache.flush()
        
        result1 = await agent.handle_input(text1)
        result2 = await agent.handle_input(text2)
        
        assert result1 == response1
        assert result2 == response2

    @pytest.mark.asyncio
    async def test_cache_preserves_all_response_fields(self, agent, cache):
        """Test that cache preserves all response fields including emotion/gesture."""
        text = "I'm excited!"
        response = {
            "status": "spoken",
            "text": "That's great!",
            "emotion": "excited",
            "expression": "smile",
            "animation": "idle_excited",
            "gesture": "jump",
            "duration_ms": 2500
        }
        
        key = ResponseCache.get_cache_key(text)
        cache.set(key, response)
        cache.flush()
        
        result = await agent.handle_input(text)
        
        assert result == response
        assert result["gesture"] == "jump"
        assert result["animation"] == "idle_excited"
