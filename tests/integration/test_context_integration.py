"""Integration tests for ContextBrain with Orchestrator."""

import asyncio
import tempfile
from pathlib import Path

import pytest

from agent.brains.context_brain import ContextBrain
from agent.core.conversation_context import ConversationContext
from agent.orchestrator import AgentOrchestrator


def test_orchestrator_with_context_brain():
    """Test that orchestrator initializes ContextBrain."""
    orch = AgentOrchestrator()
    
    context_brain = None
    for brain in orch.brains:
        if isinstance(brain, ContextBrain):
            context_brain = brain
            break
    
    assert context_brain is not None, "ContextBrain not found in orchestrator"


@pytest.mark.asyncio
async def test_context_persists_across_turns():
    """Test that context persists when multiple turns are added."""
    with tempfile.TemporaryDirectory() as tmpdir:
        brain = ContextBrain(
            brain_id="context_brain",
            event_bus=None,
            shared_state=None,
            data_dir=tmpdir,
        )
        
        for i in range(5):
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
        
        brain.save_state()
        
        brain2 = ContextBrain(
            brain_id="context_brain",
            event_bus=None,
            shared_state=None,
            data_dir=tmpdir,
        )
        brain2.load_state()
        
        recent = brain2.get_recent_turns()
        assert len(recent) == 5
        assert recent[-1].turn_id == 4
