"""Tests for ConversationMemory."""

import tempfile
import json
from pathlib import Path
from agent.core.conversation_memory import ConversationMemory
from agent.core.conversation_context import ConversationContext


def test_conversation_memory_add_and_retrieve():
    """Test adding and retrieving conversation turns."""
    mem = ConversationMemory(max_size=5)
    
    ctx1 = ConversationContext(
        turn_id=1,
        user_input="Hello",
        agent_response="Hi",
        user_mood="INTERESTED",
        agent_mood="STABLE",
        intent="greeting",
    )
    
    mem.add(ctx1)
    
    recent = mem.get_recent(n=1)
    assert len(recent) == 1
    assert recent[0].turn_id == 1


def test_conversation_memory_fifo_overflow():
    """Test FIFO behavior when exceeding max_size."""
    mem = ConversationMemory(max_size=3)
    
    for i in range(5):
        ctx = ConversationContext(
            turn_id=i,
            user_input=f"Input {i}",
            agent_response=f"Response {i}",
            user_mood="STABLE",
            agent_mood="STABLE",
            intent="statement",
        )
        mem.add(ctx)
    
    recent = mem.get_recent()
    assert len(recent) == 3
    assert recent[0].turn_id == 2
    assert recent[2].turn_id == 4


def test_conversation_memory_persistence():
    """Test saving and loading from JSON file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "context.json"
        mem = ConversationMemory(max_size=3, file_path=file_path)
        
        ctx = ConversationContext(
            turn_id=1,
            user_input="Hello",
            agent_response="Hi",
            user_mood="INTERESTED",
            agent_mood="STABLE",
            intent="greeting",
        )
        mem.add(ctx)
        mem.save()
        
        assert file_path.exists()
        
        mem2 = ConversationMemory(max_size=3, file_path=file_path)
        mem2.load()
        
        recent = mem2.get_recent()
        assert len(recent) == 1
        assert recent[0].turn_id == 1
