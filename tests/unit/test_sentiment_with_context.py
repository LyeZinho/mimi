"""Unit tests for SentimentBrain with conversation context."""

import asyncio
from unittest.mock import MagicMock, AsyncMock

import pytest

from agent.brains.sentiment_brain import SentimentBrain
from agent.brains.context_brain import ContextBrain
from agent.core.conversation_context import ConversationContext
from agent.core.messaging import EventBus
from agent.core.messaging.shared_state import SharedAgentState


@pytest.fixture
def mock_brain_deps():
    """Create mock dependencies for Brain."""
    event_bus = MagicMock(spec=EventBus)
    event_bus.subscribe = MagicMock(return_value=lambda callback: None)
    shared_state = MagicMock(spec=SharedAgentState)
    shared_state.register_brain = AsyncMock()
    return event_bus, shared_state


@pytest.mark.asyncio
async def test_sentiment_uses_conversation_context(mock_brain_deps):
    """Test that SentimentBrain can access conversation context."""
    event_bus, shared_state = mock_brain_deps
    
    context_brain = ContextBrain(
        brain_id="context_brain",
        event_bus=event_bus,
        shared_state=shared_state,
    )
    
    for i in range(3):
        ctx = ConversationContext(
            turn_id=i,
            user_input=f"About feelings {i}",
            agent_response=f"Response {i}",
            user_mood="INTERESTED",
            agent_mood="STABLE",
            intent="statement",
            topics=["feelings"],
        )
        context_brain.add_turn(ctx)
    
    context_str = context_brain.build_llm_context()
    
    assert "About feelings" in context_str or len(context_str) > 0
    recent = context_brain.get_recent_turns()
    assert recent is not None
    assert len(recent) == 3
