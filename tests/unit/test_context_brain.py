"""Unit tests for ContextBrain."""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from agent.brains.context_brain import ContextBrain
from agent.core.conversation_context import ConversationContext
from agent.core.messaging import EventBus
from agent.core.messaging.shared_state import SharedAgentState


@pytest.fixture
def mock_brain_deps():
    """Create mock dependencies for Brain."""
    event_bus = MagicMock(spec=EventBus)
    shared_state = MagicMock(spec=SharedAgentState)
    shared_state.register_brain = MagicMock()
    return event_bus, shared_state


def test_context_brain_add_turn(mock_brain_deps):
    """Test adding a conversation turn to ContextBrain."""
    event_bus, shared_state = mock_brain_deps
    brain = ContextBrain(
        brain_id="context_brain",
        event_bus=event_bus,
        shared_state=shared_state,
    )
    
    ctx = ConversationContext(
        turn_id=1,
        user_input="How are you?",
        agent_response="I'm fine",
        user_mood="INTERESTED",
        agent_mood="STABLE",
        intent="greeting",
        topics=["greeting"],
        importance_score=0.6,
    )
    
    brain.add_turn(ctx)
    
    recent = brain.get_recent_turns(n=1)
    assert len(recent) == 1
    assert recent[0].turn_id == 1


def test_context_brain_build_context_prompt(mock_brain_deps):
    """Test building LLM prompt context."""
    event_bus, shared_state = mock_brain_deps
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
            topics=["topic"],
        )
        brain.add_turn(ctx)
    
    prompt_context = brain.build_llm_context(max_tokens=500)
    
    assert isinstance(prompt_context, str)
    assert len(prompt_context) > 0
    assert "Input" in prompt_context
