"""Unit tests for user profile analysis system."""

import pytest
import tempfile
import json
from pathlib import Path

from agent.core.user_profile import (
    UserProfile,
    PersonalityTraits,
    SupportStyle,
)
from agent.core.user_profile_manager import UserProfileManager
from agent.core.long_term_memory import LongTermMemoryManager
from agent.core.conversation_context import ConversationContext


@pytest.fixture
def temp_data_dir():
    """Create temporary directory for test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def layer4_manager(temp_data_dir):
    """Create Layer 4 manager for testing."""
    return LongTermMemoryManager(db_path=temp_data_dir / "long_term_memory.db")


@pytest.fixture
def profile_manager(temp_data_dir, layer4_manager):
    """Create profile manager with Layer 4 data."""
    for i in range(10):
        context = ConversationContext(
            turn_id=i,
            user_input=f"Test input {i}",
            agent_response=f"Test response {i}",
            user_mood="ANXIOUS" if i < 5 else "ENERGIZED",
            agent_mood="SUPPORTIVE",
            intent="complaint" if i < 5 else "appreciation",
            topics=["work", "stress"] if i < 5 else ["achievement", "progress"],
            entities={},
            importance_score=0.7,
            user_mood_confidence=0.8,
        )
        layer4_manager.store_if_important(context, threshold=0.5)
    
    return UserProfileManager(
        db_path=temp_data_dir / "long_term_memory.db",
        profile_path=temp_data_dir / "user_profile.json",
    )


def test_user_profile_creation():
    """Test UserProfile dataclass creation and serialization."""
    profile = UserProfile()
    
    assert profile.user_id == "default_user"
    assert profile.personality.dominant_mood == "STABLE"
    assert profile.confidence == 0.0
    
    profile_dict = profile.to_dict()
    assert "personality" in profile_dict
    assert "interests" in profile_dict
    
    restored = UserProfile.from_dict(profile_dict)
    assert restored.user_id == profile.user_id
    assert restored.personality.dominant_mood == profile.personality.dominant_mood


def test_user_profile_personality_analysis(profile_manager):
    """Test personality trait analysis from Layer 4."""
    profile = profile_manager.analyze()
    
    assert profile.personality.dominant_mood in ["ANXIOUS", "ENERGIZED"]
    assert profile.personality.dominant_mood_frequency > 0
    assert profile.personality.emotional_range >= 0
    assert profile.personality.mood_resilience >= 0


def test_user_profile_interests_analysis(profile_manager):
    """Test interest analysis from Layer 4."""
    profile = profile_manager.analyze()
    
    assert len(profile.interests.primary_topics) > 0
    assert profile.interests.passion_level > 0
    assert profile.interests.new_topic_frequency >= 0
    assert len(profile.interests.recurring_concerns) > 0
    
    for topic, frequency, importance in profile.interests.primary_topics:
        assert 0 <= frequency <= 1
        assert 0 <= importance <= 1


def test_user_profile_communication_analysis(profile_manager):
    """Test communication style analysis."""
    profile = profile_manager.analyze()
    
    assert profile.communication.primary_intent in ["complaint", "appreciation", "statement"]
    assert len(profile.communication.intent_distribution) > 0
    assert 0 <= profile.communication.verbosity <= 1
    assert profile.communication.expressiveness >= 0


def test_user_profile_support_needs_analysis(profile_manager):
    """Test support needs analysis."""
    profile = profile_manager.analyze()
    
    assert 0 <= profile.support_needs.complaint_frequency <= 1
    assert 0 <= profile.support_needs.help_seeking_frequency <= 1
    assert profile.support_needs.validation_preference in [
        SupportStyle.EMOTIONAL,
        SupportStyle.PRACTICAL,
        SupportStyle.BALANCED,
    ]


def test_user_profile_confidence_calculation(profile_manager):
    """Test confidence score calculation."""
    profile = profile_manager.analyze()
    
    assert 0 <= profile.confidence <= 1
    
    profile.memory_turnover_count = 0
    profile_manager._calculate_confidence()
    assert profile_manager.profile.confidence == 0.0


def test_user_profile_mood_resilience(profile_manager):
    """Test resilience calculation (recovery from negative moods)."""
    profile = profile_manager.analyze()
    
    resilience = profile.personality.mood_resilience
    assert 0 <= resilience <= 1


def test_user_profile_persistence(profile_manager, temp_data_dir):
    """Test profile persistence to disk."""
    profile1 = profile_manager.analyze()
    profile1_confidence = profile1.confidence
    
    profile_manager.save_profile()
    
    new_manager = UserProfileManager(
        db_path=temp_data_dir / "long_term_memory.db",
        profile_path=temp_data_dir / "user_profile.json",
    )
    
    assert new_manager.profile.confidence == profile1_confidence
    assert new_manager.profile.personality.dominant_mood == profile1.personality.dominant_mood


def test_user_profile_summary_generation(profile_manager):
    """Test human-readable profile summary."""
    profile_manager.analyze()
    summary = profile_manager.get_profile_summary()
    
    assert "PERSONALITY" in summary
    assert "INTERESTS" in summary
    assert "COMMUNICATION STYLE" in summary
    assert "SUPPORT NEEDS" in summary
    assert "PROFILE CONFIDENCE" in summary


def test_user_profile_empty_layer4(temp_data_dir):
    """Test profile analysis with no Layer 4 data."""
    manager = UserProfileManager(
        db_path=temp_data_dir / "nonexistent.db",
        profile_path=temp_data_dir / "user_profile.json",
    )
    
    profile = manager.analyze()
    assert profile.personality.dominant_mood == "STABLE"
    assert profile.confidence == 0.0
