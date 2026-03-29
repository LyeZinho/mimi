"""Tests for ConversationalChainManager."""

import time
from agent.core.conversational_chains import (
    ConversationState, TransitionRecord, ConversationalChainManager
)


def test_conversation_state_creation():
    """Test creating a conversation state."""
    state = ConversationState(mood="INTERESTED", topic="technical")
    
    assert state.mood == "INTERESTED"
    assert state.topic == "technical"
    assert state.to_key() == "INTERESTED|technical"


def test_conversation_state_from_key():
    """Test creating state from key."""
    state = ConversationState.from_key("ANALYTICAL|python")
    
    assert state.mood == "ANALYTICAL"
    assert state.topic == "python"


def test_markov_chain_transition():
    """Test recording state transitions."""
    manager = ConversationalChainManager()
    
    state1 = ConversationState(mood="ANALYTICAL", topic="technical")
    state2 = ConversationState(mood="INTERESTED", topic="technical")
    
    manager.record_transition(state1, state2)
    
    transitions = manager.get_transitions_from(state1)
    assert len(transitions) == 1
    assert transitions[0][0].to_key() == state2.to_key()


def test_markov_chain_prediction():
    """Test predicting next state by frequency when weights are equal."""
    manager = ConversationalChainManager()
    
    state1 = ConversationState(mood="ANALYTICAL", topic="technical")
    state2 = ConversationState(mood="INTERESTED", topic="technical")
    state3 = ConversationState(mood="ENERGIZED", topic="technical")
    
    for _ in range(5):
        manager.record_transition(state1, state2)
    
    for _ in range(2):
        manager.record_transition(state1, state3)
    
    # Set both to same weight manually to test count-based selection
    trans = manager.get_transitions_from(state1)
    for t in trans:
        t[2].weight = 1.0
        t[2].last_seen = time.time()
    
    next_state = manager.predict_next_state(state1)
    assert next_state is not None
    # With equal weights, higher count wins (5 > 2)
    assert next_state.to_key() == state2.to_key()


def test_markov_chain_weight_decay():
    """Test weight decay over time."""
    manager = ConversationalChainManager()
    
    state1 = ConversationState(mood="STABLE", topic="general")
    state2 = ConversationState(mood="STABLE", topic="general")
    
    manager.record_transition(state1, state2)
    chain = manager.get_transitions_from(state1)[0]
    
    original_weight = chain[1]
    
    chain[2].last_seen = time.time() - (30 * 24 * 3600)
    decayed = chain[2].calculate_weight()
    
    assert decayed < original_weight
