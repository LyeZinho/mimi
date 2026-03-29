"""Integration tests for UserProfileBrain with Orchestrator."""

import asyncio
import tempfile
from pathlib import Path

import pytest

from agent.brains.user_profile_brain import UserProfileBrain
from agent.brains.reasoning_brain import ReasoningBrain
from agent.brains.context_brain import ContextBrain
from agent.core.conversation_context import ConversationContext
from agent.core.messaging import EventBus, EventType, SharedAgentState
from agent.orchestrator import AgentOrchestrator


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
async def user_profile_brain(temp_data_dir, event_bus, shared_state):
    """Create a UserProfileBrain instance."""
    brain = UserProfileBrain(
        brain_id="user_profile_brain_test",
        event_bus=event_bus,
        shared_state=shared_state,
        data_dir=temp_data_dir,
    )
    await brain.initialize()
    return brain


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
async def test_user_profile_brain_initialization(user_profile_brain):
    """Test that UserProfileBrain initializes correctly."""
    assert user_profile_brain is not None
    assert user_profile_brain.brain_id == "user_profile_brain_test"
    assert user_profile_brain._profile_manager is not None
    assert user_profile_brain._analysis_interval == 10


@pytest.mark.asyncio
async def test_user_profile_brain_in_orchestrator():
    """Test that UserProfileBrain is initialized in orchestrator."""
    orch = AgentOrchestrator()
    
    profile_brain = None
    for brain in orch.brains:
        if isinstance(brain, UserProfileBrain):
            profile_brain = brain
            break
    
    assert profile_brain is not None, "UserProfileBrain not found in orchestrator"
    assert profile_brain.brain_id == "user_profile_brain"
@pytest.mark.asyncio
async def test_user_profile_brain_receives_response_ready_events(
    user_profile_brain, event_bus
):
    """Test that UserProfileBrain subscribes to RESPONSE_READY events."""
    event = type('MockEvent', (), {})()
    await user_profile_brain._on_response_ready(event)
    assert user_profile_brain._turns_since_analysis == 1


@pytest.mark.asyncio
async def test_user_profile_brain_triggers_analysis_after_interval(
    temp_data_dir, event_bus, shared_state
):
    """Test that profile analysis is triggered after reaching analysis interval."""
    brain = UserProfileBrain(
        brain_id="test_interval",
        event_bus=event_bus,
        shared_state=shared_state,
        data_dir=temp_data_dir,
    )
    await brain.initialize()
    brain._analysis_interval = 3
    
    event = type('MockEvent', (), {})()
    
    assert brain._turns_since_analysis == 0
    
    await brain._on_response_ready(event)
    assert brain._turns_since_analysis == 1
    
    await brain._on_response_ready(event)
    assert brain._turns_since_analysis == 2
    
    await brain._on_response_ready(event)
    assert brain._turns_since_analysis == 0


@pytest.mark.asyncio
async def test_user_profile_brain_gets_profile(
    temp_data_dir, event_bus, shared_state
):
    """Test that UserProfileBrain can retrieve current profile."""
    brain = UserProfileBrain(
        brain_id="test_profile_get",
        event_bus=event_bus,
        shared_state=shared_state,
        data_dir=temp_data_dir,
    )
    await brain.initialize()
    
    profile = brain.get_profile()
    assert profile is not None
    assert hasattr(profile, 'personality')
    assert hasattr(profile, 'interests')
    assert hasattr(profile, 'communication')
    assert hasattr(profile, 'support_needs')
    assert hasattr(profile, 'confidence')


@pytest.mark.asyncio
async def test_user_profile_brain_gets_profile_summary(
    temp_data_dir, event_bus, shared_state
):
    """Test that UserProfileBrain can generate profile summary."""
    brain = UserProfileBrain(
        brain_id="test_profile_summary",
        event_bus=event_bus,
        shared_state=shared_state,
        data_dir=temp_data_dir,
    )
    await brain.initialize()
    
    summary = brain.get_profile_summary()
    assert isinstance(summary, str)
    assert len(summary) > 0


@pytest.mark.asyncio
async def test_user_profile_brain_persists_profile(
    temp_data_dir, event_bus, shared_state
):
    """Test that UserProfileBrain can save and load profiles."""
    brain = UserProfileBrain(
        brain_id="test_persist",
        event_bus=event_bus,
        shared_state=shared_state,
        data_dir=temp_data_dir,
    )
    await brain.initialize()
    
    brain.save_profile()
    profile_path = temp_data_dir / "user_profile.json"
    assert profile_path.exists(), "Profile file should exist after save"
    
    brain2 = UserProfileBrain(
        brain_id="test_persist_2",
        event_bus=event_bus,
        shared_state=shared_state,
        data_dir=temp_data_dir,
    )
    await brain2.initialize()
    brain2.load_profile()
    
    loaded_profile = brain2.get_profile()
    assert loaded_profile is not None


@pytest.mark.asyncio
async def test_user_profile_and_context_brain_together(
    temp_data_dir, event_bus, shared_state
):
    """Test that UserProfileBrain and ContextBrain work together."""
    context_brain = ContextBrain(
        brain_id="context_brain_test",
        event_bus=event_bus,
        shared_state=shared_state,
        data_dir=temp_data_dir,
    )
    await context_brain.initialize()
    
    profile_brain = UserProfileBrain(
        brain_id="profile_brain_test",
        event_bus=event_bus,
        shared_state=shared_state,
        data_dir=temp_data_dir,
    )
    await profile_brain.initialize()
    
    for i in range(5):
        ctx = ConversationContext(
            turn_id=i,
            user_input=f"I'm feeling {'stressed' if i < 3 else 'better'} about work",
            agent_response=f"Response {i}",
            user_mood="ANXIOUS" if i < 3 else "ENERGIZED",
            agent_mood="SUPPORTIVE",
            intent="complaint" if i < 3 else "appreciation",
            topics=["work", "stress"],
            entities={},
            importance_score=0.7,
            user_mood_confidence=0.85,
        )
        context_brain.add_turn(ctx)
    
    await profile_brain._update_profile_if_needed()
    
    profile = profile_brain.get_profile()
    assert profile is not None
    assert profile.confidence > 0.0, "Profile confidence should increase with data"


@pytest.mark.asyncio
async def test_user_profile_brain_with_orchestrator_full_flow():
    """Test full flow with orchestrator initializing all 9 brains."""
    orch = AgentOrchestrator()
    
    assert len(orch.brains) == 9, f"Expected 9 brains, got {len(orch.brains)}"
    
    context_brain = None
    profile_brain = None
    reasoning_brain = None
    
    for brain in orch.brains:
        if isinstance(brain, ContextBrain):
            context_brain = brain
        elif isinstance(brain, UserProfileBrain):
            profile_brain = brain
        elif isinstance(brain, ReasoningBrain):
            reasoning_brain = brain
    
    assert context_brain is not None, "ContextBrain not found"
    assert profile_brain is not None, "UserProfileBrain not found"
    assert reasoning_brain is not None, "ReasoningBrain not found"
    
    assert context_brain.brain_id == "context_brain"
    assert profile_brain.brain_id == "user_profile_brain"


@pytest.mark.asyncio
async def test_user_profile_brain_incremental_updates(
    temp_data_dir, event_bus, shared_state
):
    """Test that profile updates incrementally as new data arrives."""
    context_brain = ContextBrain(
        brain_id="context_incremental",
        event_bus=event_bus,
        shared_state=shared_state,
        data_dir=temp_data_dir,
    )
    await context_brain.initialize()
    
    profile_brain = UserProfileBrain(
        brain_id="profile_incremental",
        event_bus=event_bus,
        shared_state=shared_state,
        data_dir=temp_data_dir,
    )
    await profile_brain.initialize()
    
    await profile_brain._update_profile_if_needed()
    profile1 = profile_brain.get_profile()
    confidence1 = profile1.confidence
    
    for i in range(3):
        ctx = ConversationContext(
            turn_id=i,
            user_input=f"Message {i}",
            agent_response=f"Response {i}",
            user_mood="INTERESTED",
            agent_mood="SUPPORTIVE",
            intent="statement",
            topics=["topic1"],
            entities={},
            importance_score=0.6,
            user_mood_confidence=0.7,
        )
        context_brain.add_turn(ctx)
    
    await profile_brain._update_profile_if_needed()
    profile2 = profile_brain.get_profile()
    confidence2 = profile2.confidence
    
    assert confidence2 > confidence1, \
        f"Confidence should increase: {confidence1} -> {confidence2}"


@pytest.mark.asyncio
async def test_orchestrator_all_brains_initialized():
    """Test that orchestrator initializes all 9 brains without errors."""
    orch = AgentOrchestrator()
    
    assert len(orch.brains) == 9, \
        f"Expected 9 brains, got {len(orch.brains)}"
    
    brain_types = {type(brain).__name__ for brain in orch.brains}
    expected_types = {
        'InputBrain',
        'ReasoningBrain',
        'PlanningBrain',
        'ExecutionBrain',
        'SentimentBrain',
        'AvatarBrain',
        'OutputBrain',
        'ContextBrain',
        'UserProfileBrain',
    }
    
    assert brain_types == expected_types, \
        f"Brain types mismatch. Got: {brain_types}, Expected: {expected_types}"
