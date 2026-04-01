"""Tests for ConversationContext."""

from agent.core.conversation_context import ConversationContext


def test_conversation_context_creation():
    """Test creating a conversation context turn."""
    ctx = ConversationContext(
        turn_id=1,
        user_input="Hello",
        agent_response="Hi there",
        user_mood="INTERESTED",
        agent_mood="STABLE",
        intent="greeting",
        topics=["greeting"],
        importance_score=0.7,
    )
    
    assert ctx.turn_id == 1
    assert ctx.user_input == "Hello"
    assert ctx.importance_score == 0.7
    assert ctx.timestamp is not None
    assert isinstance(ctx.to_dict(), dict)


def test_conversation_context_json_serializable():
    """Test JSON serialization."""
    ctx = ConversationContext(
        turn_id=2,
        user_input="Test",
        agent_response="Response",
        user_mood="STABLE",
        agent_mood="STABLE",
        intent="statement",
    )
    
    json_data = ctx.to_json_serializable()
    assert isinstance(json_data["timestamp"], float)
    assert isinstance(json_data["user_mood_confidence"], float)


def test_conversation_context_from_dict():
    """Test creating from dictionary."""
    data = {
        "turn_id": 3,
        "user_input": "Hello",
        "agent_response": "Hi",
        "user_mood": "INTERESTED",
        "agent_mood": "STABLE",
        "intent": "greeting",
    }
    
    ctx = ConversationContext.from_dict(data)
    assert ctx.turn_id == 3
    assert ctx.user_input == "Hello"
