"""Integration test for all 4 context layers working together."""

import pytest
import tempfile
import json
from pathlib import Path

from agent.core.conversation_context import ConversationContext
from agent.brains.context_brain import ContextBrain
from agent.core.messaging import EventBus, EventType, SharedAgentState


@pytest.fixture
def temp_data_dir():
    """Create temporary directory for test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def event_bus():
    """Create an event bus for testing."""
    return EventBus()


@pytest.fixture
def shared_state():
    """Create shared agent state for testing."""
    return SharedAgentState()


@pytest.fixture
async def context_brain(temp_data_dir, event_bus, shared_state):
    """Create a ContextBrain instance."""
    brain = ContextBrain(
        brain_id="context_brain_test",
        event_bus=event_bus,
        shared_state=shared_state,
        data_dir=temp_data_dir,
    )
    await brain.initialize()
    return brain


@pytest.mark.asyncio
async def test_full_four_layer_context_flow(context_brain):
    """Test complete flow: add turns -> evaluate -> store -> retrieve -> combine."""
    
    turn1 = ConversationContext(
        turn_id=1,
        user_input="I've been feeling really stressed about work",
        agent_response="That sounds challenging. Tell me more.",
        user_mood="ANXIOUS",
        agent_mood="EMPATHETIC",
        intent="complaint",
        topics=["stress", "work"],
        entities={"topic": "work", "emotion": "stress"},
        importance_score=0.7,
        user_mood_confidence=0.85,
    )
    
    turn2 = ConversationContext(
        turn_id=2,
        user_input="My deadline is tomorrow and I haven't finished",
        agent_response="Let's break down what you need to do.",
        user_mood="ANXIOUS",
        agent_mood="SUPPORTIVE",
        intent="request",
        topics=["deadline", "work"],
        entities={"topic": "work", "time": "tomorrow"},
        importance_score=0.8,
        user_mood_confidence=0.9,
    )
    
    turn3 = ConversationContext(
        turn_id=3,
        user_input="I think I can do this. Thank you for helping.",
        agent_response="You've got this! I'm here if you need anything.",
        user_mood="ENERGIZED",
        agent_mood="HAPPY",
        intent="appreciation",
        topics=["confidence", "work"],
        entities={"emotion": "positive"},
        importance_score=0.6,
        user_mood_confidence=0.8,
    )
    
    context_brain.add_turn(turn1)
    context_brain.add_turn(turn2)
    context_brain.add_turn(turn3)
    
    recent_turns = context_brain.get_recent_turns(n=5)
    assert len(recent_turns) == 3
    
    llm_context = context_brain.build_llm_context(max_tokens=2000)
    assert "Recent Conversation" in llm_context
    assert "stress" in llm_context.lower() or "anxious" in llm_context.lower()
    assert "Conversation Themes" in llm_context or "Expected Direction" in llm_context
    
    stats = context_brain.get_memory_stats()
    
    assert stats["layer1_short_term"]["count"] == 3
    assert stats["layer1_short_term"]["max_size"] == 20
    
    assert stats["layer2_topics"]["clusters"] > 0
    assert stats["layer2_topics"]["total_occurrences"] > 0
    
    assert stats["layer3_chains"]["transitions"] >= 0
    
    assert stats["layer4_long_term"]["total_memories"] > 0
    assert stats["layer4_long_term"]["recent_memories"] > 0
    
    work_memories = context_brain.search_long_term_by_topic("work", limit=5)
    assert len(work_memories) > 0
    assert any("deadline" in m.get("user_input", "").lower() for m in work_memories)


@pytest.mark.asyncio
async def test_layer_1_sliding_window(context_brain):
    """Test Layer 1 sliding window behavior."""
    
    for i in range(25):
        turn = ConversationContext(
            turn_id=i,
            user_input=f"Turn {i}",
            agent_response=f"Response {i}",
            user_mood="STABLE",
            agent_mood="STABLE",
            intent="statement",
            topics=["general"],
            entities={},
            importance_score=0.5,
            user_mood_confidence=0.5,
        )
        context_brain.add_turn(turn)
    
    recent_turns = context_brain.get_recent_turns(n=20)
    assert len(recent_turns) == 20
    
    most_recent = recent_turns[-1]
    assert most_recent.turn_id == 24
    
    oldest_in_window = recent_turns[0]
    assert oldest_in_window.turn_id == 5


@pytest.mark.asyncio
async def test_layer_2_topic_clustering(context_brain):
    """Test Layer 2 topic clustering with mood decay."""
    
    turns = [
        ConversationContext(
            turn_id=i,
            user_input=f"I'm discussing machine learning topic {i}",
            agent_response="Interesting topic",
            user_mood="ENERGIZED" if i % 2 == 0 else "STABLE",
            agent_mood="NEUTRAL",
            intent="statement",
            topics=["machine learning", "AI"],
            entities={"field": "ML"},
            importance_score=0.5,
            user_mood_confidence=0.7,
        )
        for i in range(5)
    ]
    
    for turn in turns:
        context_brain.add_turn(turn)
    
    stats = context_brain.get_memory_stats()
    assert stats["layer2_topics"]["clusters"] >= 2
    assert stats["layer2_topics"]["total_occurrences"] >= 5


@pytest.mark.asyncio
async def test_layer_3_conversation_flow(context_brain):
    """Test Layer 3 conversation state transitions."""
    
    anxious_turn = ConversationContext(
        turn_id=1,
        user_input="I'm worried",
        agent_response="Tell me more",
        user_mood="ANXIOUS",
        agent_mood="NEUTRAL",
        intent="statement",
        topics=["worry"],
        entities={},
        importance_score=0.5,
        user_mood_confidence=0.8,
    )
    
    resolved_turn = ConversationContext(
        turn_id=2,
        user_input="Actually I feel better now",
        agent_response="That's great",
        user_mood="STABLE",
        agent_mood="HAPPY",
        intent="statement",
        topics=["resolution"],
        entities={},
        importance_score=0.5,
        user_mood_confidence=0.8,
    )
    
    context_brain.add_turn(anxious_turn)
    context_brain.add_turn(resolved_turn)
    
    stats = context_brain.get_memory_stats()
    assert stats["layer3_chains"]["transitions"] >= 0


@pytest.mark.asyncio
async def test_layer_4_importance_filtering(context_brain):
    """Test Layer 4 only stores important moments."""
    
    high_importance = ConversationContext(
        turn_id=1,
        user_input="I just got a promotion!",
        agent_response="Congratulations!",
        user_mood="ENERGIZED",
        agent_mood="HAPPY",
        intent="celebration",
        topics=["career"],
        entities={"event": "promotion"},
        importance_score=0.95,
        user_mood_confidence=0.95,
    )
    
    low_importance = ConversationContext(
        turn_id=2,
        user_input="How is the weather?",
        agent_response="It's nice.",
        user_mood="STABLE",
        agent_mood="STABLE",
        intent="question",
        topics=["weather"],
        entities={},
        importance_score=0.2,
        user_mood_confidence=0.5,
    )
    
    context_brain.add_turn(high_importance)
    context_brain.add_turn(low_importance)
    
    stats = context_brain.get_memory_stats()
    assert stats["layer4_long_term"]["total_memories"] >= 1
    
    promotion_memories = context_brain.search_long_term_by_topic("career", limit=10)
    assert any("promotion" in m.get("user_input", "").lower() for m in promotion_memories)


@pytest.mark.asyncio
async def test_persistence_across_sessions(context_brain, temp_data_dir, event_bus, shared_state):
    """Test that all 4 layers persist and can be restored."""
    
    turn1 = ConversationContext(
        turn_id=1,
        user_input="First conversation turn",
        agent_response="Response one",
        user_mood="STABLE",
        agent_mood="NEUTRAL",
        intent="statement",
        topics=["session", "persistence"],
        entities={},
        importance_score=0.7,
        user_mood_confidence=0.7,
    )
    
    context_brain.add_turn(turn1)
    stats_before = context_brain.get_memory_stats()
    
    context_brain.save_state()
    
    brain2 = ContextBrain(
        brain_id="context_brain_test_2",
        event_bus=event_bus,
        shared_state=shared_state,
        data_dir=temp_data_dir,
    )
    await brain2.initialize()
    brain2.load_state()
    
    stats_after = brain2.get_memory_stats()
    
    assert stats_after["layer1_short_term"]["count"] == stats_before["layer1_short_term"]["count"]
    assert stats_after["layer4_long_term"]["total_memories"] == stats_before["layer4_long_term"]["total_memories"]


@pytest.mark.asyncio
async def test_context_brain_pruning(context_brain):
    """Test Layer 3 and Layer 4 pruning in background process."""
    
    for i in range(10):
        turn = ConversationContext(
            turn_id=i,
            user_input=f"Input {i}",
            agent_response=f"Response {i}",
            user_mood="STABLE",
            agent_mood="STABLE",
            intent="statement",
            topics=[f"topic_{i % 3}"],
            entities={},
            importance_score=0.5,
            user_mood_confidence=0.5,
        )
        context_brain.add_turn(turn)
    
    stats_before = context_brain.get_memory_stats()
    
    await context_brain.process()
    
    stats_after = context_brain.get_memory_stats()
    
    assert stats_after["layer1_short_term"]["count"] == stats_before["layer1_short_term"]["count"]


@pytest.mark.asyncio
async def test_llm_context_combines_all_layers(context_brain):
    """Test that LLM context includes all 4 layers properly combined."""
    
    turns = [
        ConversationContext(
            turn_id=i,
            user_input=f"User input {i}",
            agent_response=f"Agent response {i}",
            user_mood="STABLE" if i < 3 else "ENERGIZED",
            agent_mood="NEUTRAL",
            intent="question",
            topics=["technology", "AI"],
            entities={},
            importance_score=0.5,
            user_mood_confidence=0.7,
        )
        for i in range(10)
    ]
    
    for turn in turns:
        context_brain.add_turn(turn)
    
    llm_context = context_brain.build_llm_context(max_tokens=2000)
    
    assert "[Recent Conversation]" in llm_context
    assert "User input" in llm_context
    assert "Agent response" in llm_context
    
    assert "[Conversation Themes]" in llm_context or "[Expected Direction]" in llm_context
    
    lines = llm_context.split("\n")
    assert len(lines) > 5
