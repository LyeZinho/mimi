"""
Tests for ReasoningBrain with LLM provider integration.

Tests verify:
1. ReasoningBrain accepts optional LLMProvider parameter
2. ReasoningBrain uses LLM provider when available
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from agent.brains.reasoning_brain import ReasoningBrain
from agent.llm.provider import LLMProvider


@pytest.mark.asyncio
async def test_reasoning_brain_accepts_provider():
    """Test that ReasoningBrain accepts and stores llm_provider parameter."""
    mock_provider = AsyncMock(spec=LLMProvider)
    mock_bus = AsyncMock()
    mock_state = AsyncMock()
    
    brain = ReasoningBrain(
        brain_id="test_reasoning",
        event_bus=mock_bus,
        shared_state=mock_state,
        llm_provider=mock_provider
    )
    
    assert brain.llm_provider is not None
    assert brain.llm_provider is mock_provider


@pytest.mark.asyncio
async def test_reasoning_brain_uses_llm():
    """Test that ReasoningBrain uses LLM provider when calling _infer_intent."""
    mock_provider = AsyncMock(spec=LLMProvider)
    mock_response = json.dumps({
        "intent": "greeting",
        "confidence": 0.95,
        "parameters": {},
        "sentiment": "positive"
    })
    mock_provider.generate.return_value = mock_response
    
    mock_bus = AsyncMock()
    mock_state = AsyncMock()
    mock_state.register_brain = AsyncMock()
    
    brain = ReasoningBrain(
        brain_id="test_reasoning",
        event_bus=mock_bus,
        shared_state=mock_state,
        llm_provider=mock_provider
    )
    
    await brain.initialize()
    
    result = await brain._infer_intent("olá Mimi", {"user_id": "123"})
    
    assert mock_provider.generate.called
    assert "intent" in result
    assert result["intent"] == "greeting"
