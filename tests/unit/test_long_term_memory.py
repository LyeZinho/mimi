"""Unit tests for LongTermMemoryManager."""

import tempfile
import time
from pathlib import Path

import pytest

from agent.core.long_term_memory import LongTermMemoryManager
from agent.core.conversation_context import ConversationContext


def test_long_term_memory_importance_scoring():
    """Test importance scoring for long-term storage."""
    manager = LongTermMemoryManager()
    
    ctx = ConversationContext(
        turn_id=1,
        user_input="I love Mimi!",
        agent_response="Thank you!",
        user_mood="ENERGIZED",
        agent_mood="ENERGIZED",
        intent="appreciation",
        importance_score=0.8,
        user_mood_confidence=0.9,
    )
    
    importance = manager.calculate_importance_score(ctx)
    
    assert importance > 0.5
    assert isinstance(importance, float)


def test_long_term_memory_store_and_retrieve():
    """Test storing and retrieving important turns."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "longterm.db"
        manager = LongTermMemoryManager(db_path=db_path)
        
        ctx = ConversationContext(
            turn_id=1,
            user_input="Remember this",
            agent_response="Got it",
            user_mood="INTERESTED",
            agent_mood="STABLE",
            intent="statement",
            topics=["memory"],
            importance_score=0.7,
        )
        
        manager.store_if_important(ctx, threshold=0.6)
        
        retrieved = manager.search_by_topic("memory", limit=5)
        assert len(retrieved) >= 1
        assert retrieved[0]["user_input"] == "Remember this"


def test_long_term_memory_auto_pruning():
    """Test automatic pruning of old low-importance entries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "longterm.db"
        manager = LongTermMemoryManager(db_path=db_path)
        
        # Store old entry with LOW importance so it gets pruned
        old_time = time.time() - (30 * 24 * 3600)
        
        ctx = ConversationContext(
            turn_id=1,
            user_input="Old message",
            agent_response="Old response",
            user_mood="STABLE",
            agent_mood="STABLE",
            intent="statement",
            topics=["old"],
            importance_score=0.2,
            user_mood_confidence=0.3,
        )
        ctx.timestamp = old_time
        manager.store_if_important(ctx, threshold=0.1)
        
        # Verify it was stored
        stats = manager.get_memory_stats()
        assert stats["total_entries"] >= 1
        
        # Now prune entries older than 20 days with low importance
        count = manager.prune_old_entries(days=20)
        assert count >= 1
