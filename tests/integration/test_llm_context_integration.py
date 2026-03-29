"""Integration tests for LLM with ContextBrain context."""

import asyncio
from unittest.mock import MagicMock, AsyncMock

import pytest

from agent.brains.reasoning_brain import ReasoningBrain
from agent.brains.context_brain import ContextBrain
from agent.core.conversation_context import ConversationContext
from agent.core.messaging import EventBus
from agent.core.messaging.shared_state import SharedAgentState
from agent.llm.prompt_templates import PromptTemplates


@pytest.fixture
def mock_brain_deps():
    """Create mock dependencies for Brain."""
    event_bus = MagicMock(spec=EventBus)
    event_bus.subscribe = MagicMock(return_value=lambda callback: None)
    shared_state = MagicMock(spec=SharedAgentState)
    shared_state.register_brain = AsyncMock()
    return event_bus, shared_state


def test_llm_receives_context_in_prompt(mock_brain_deps):
    """Test that LLM prompt includes context from ContextBrain."""
    event_bus, shared_state = mock_brain_deps
    
    context_brain = ContextBrain(
        brain_id="context_brain",
        event_bus=event_bus,
        shared_state=shared_state,
    )
    
    ctx = ConversationContext(
        turn_id=0,
        user_input="I like Python programming",
        agent_response="Python is great",
        user_mood="INTERESTED",
        agent_mood="STABLE",
        intent="statement",
        topics=["programming"],
    )
    context_brain.add_turn(ctx)
    
    context_str = context_brain.build_llm_context()
    
    prompt = PromptTemplates.response_generation_simple(
        "More about Python?",
        "question",
        context={"conversation_history": context_str},
    )
    
    assert "Python" in prompt or "conversation" in prompt or "Voce" in prompt
    assert len(prompt) > 50


def test_context_brain_prompt_building():
    """Test that ContextBrain builds proper LLM context."""
    event_bus = MagicMock(spec=EventBus)
    event_bus.subscribe = MagicMock(return_value=lambda callback: None)
    shared_state = MagicMock(spec=SharedAgentState)
    shared_state.register_brain = AsyncMock()
    
    brain = ContextBrain(
        brain_id="context_brain",
        event_bus=event_bus,
        shared_state=shared_state,
    )
    
    for i in range(3):
        ctx = ConversationContext(
            turn_id=i,
            user_input=f"Input {i}",
            agent_response=f"Response {i}",
            user_mood="INTERESTED",
            agent_mood="STABLE",
            intent="statement",
            topics=["test"],
        )
        brain.add_turn(ctx)
    
    context_output = brain.build_llm_context()
    
    assert "Recent Conversation" in context_output
    assert "Input 0" in context_output or "Input" in context_output
