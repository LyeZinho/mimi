"""User personality profile built from long-term conversation memory."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import time


class MoodFrequency(str, Enum):
    """Mood distribution categories."""
    VERY_FREQUENT = "very_frequent"
    FREQUENT = "frequent"
    OCCASIONAL = "occasional"
    RARE = "rare"


class SupportStyle(str, Enum):
    """User's preferred support style."""
    EMOTIONAL = "emotional"
    PRACTICAL = "practical"
    BALANCED = "balanced"


@dataclass
class PersonalityTraits:
    """User's emotional personality profile."""
    
    dominant_mood: str
    dominant_mood_frequency: float
    secondary_mood: Optional[str] = None
    secondary_mood_frequency: float = 0.0
    mood_resilience: float = 0.0
    emotional_range: float = 0.0
    last_updated: float = field(default_factory=time.time)


@dataclass
class InterestProfile:
    """User's interests and passions."""
    
    primary_topics: list[tuple[str, float, float]] = field(default_factory=list)
    topic_clusters: dict[str, list[str]] = field(default_factory=dict)
    passion_level: float = 0.0
    new_topic_frequency: float = 0.0
    recurring_concerns: list[tuple[str, int]] = field(default_factory=list)
    last_updated: float = field(default_factory=time.time)


@dataclass
class CommunicationStyle:
    """User's communication patterns."""
    
    primary_intent: str
    intent_distribution: dict[str, float] = field(default_factory=dict)
    verbosity: float = 0.0
    avg_turns_per_session: float = 0.0
    response_promptness: str = "moderate"
    expressiveness: float = 0.0
    last_updated: float = field(default_factory=time.time)


@dataclass
class SupportNeeds:
    """User's support and help-seeking patterns."""
    
    complaint_frequency: float = 0.0
    help_seeking_frequency: float = 0.0
    validation_preference: SupportStyle = SupportStyle.BALANCED
    crisis_indicators: list[str] = field(default_factory=list)
    recovery_patterns: dict[str, float] = field(default_factory=dict)
    last_updated: float = field(default_factory=time.time)


@dataclass
class UserProfile:
    """Complete user personality profile from long-term memory."""
    
    user_id: str = "default_user"
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    memory_turnover_count: int = 0
    
    personality: PersonalityTraits = field(default_factory=lambda: PersonalityTraits(
        dominant_mood="STABLE",
        dominant_mood_frequency=0.0,
    ))
    
    interests: InterestProfile = field(default_factory=InterestProfile)
    
    communication: CommunicationStyle = field(default_factory=lambda: CommunicationStyle(
        primary_intent="statement",
        intent_distribution={},
    ))
    
    support_needs: SupportNeeds = field(default_factory=SupportNeeds)
    
    confidence: float = 0.0
    
    def to_dict(self) -> dict:
        """Convert profile to dictionary for JSON serialization."""
        return {
            "user_id": self.user_id,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "memory_turnover_count": self.memory_turnover_count,
            "personality": {
                "dominant_mood": self.personality.dominant_mood,
                "dominant_mood_frequency": self.personality.dominant_mood_frequency,
                "secondary_mood": self.personality.secondary_mood,
                "secondary_mood_frequency": self.personality.secondary_mood_frequency,
                "mood_resilience": self.personality.mood_resilience,
                "emotional_range": self.personality.emotional_range,
            },
            "interests": {
                "primary_topics": self.interests.primary_topics,
                "topic_clusters": self.interests.topic_clusters,
                "passion_level": self.interests.passion_level,
                "new_topic_frequency": self.interests.new_topic_frequency,
                "recurring_concerns": self.interests.recurring_concerns,
            },
            "communication": {
                "primary_intent": self.communication.primary_intent,
                "intent_distribution": self.communication.intent_distribution,
                "verbosity": self.communication.verbosity,
                "avg_turns_per_session": self.communication.avg_turns_per_session,
                "response_promptness": self.communication.response_promptness,
                "expressiveness": self.communication.expressiveness,
            },
            "support_needs": {
                "complaint_frequency": self.support_needs.complaint_frequency,
                "help_seeking_frequency": self.support_needs.help_seeking_frequency,
                "validation_preference": self.support_needs.validation_preference.value,
                "crisis_indicators": self.support_needs.crisis_indicators,
                "recovery_patterns": self.support_needs.recovery_patterns,
            },
            "confidence": self.confidence,
        }
    
    @staticmethod
    def from_dict(data: dict) -> UserProfile:
        """Reconstruct profile from dictionary."""
        return UserProfile(
            user_id=data.get("user_id", "default_user"),
            created_at=data.get("created_at", time.time()),
            last_updated=data.get("last_updated", time.time()),
            memory_turnover_count=data.get("memory_turnover_count", 0),
            personality=PersonalityTraits(
                dominant_mood=data["personality"]["dominant_mood"],
                dominant_mood_frequency=data["personality"]["dominant_mood_frequency"],
                secondary_mood=data["personality"].get("secondary_mood"),
                secondary_mood_frequency=data["personality"].get("secondary_mood_frequency", 0.0),
                mood_resilience=data["personality"].get("mood_resilience", 0.0),
                emotional_range=data["personality"].get("emotional_range", 0.0),
            ),
            interests=InterestProfile(
                primary_topics=data["interests"].get("primary_topics", []),
                topic_clusters=data["interests"].get("topic_clusters", {}),
                passion_level=data["interests"].get("passion_level", 0.0),
                new_topic_frequency=data["interests"].get("new_topic_frequency", 0.0),
                recurring_concerns=data["interests"].get("recurring_concerns", []),
            ),
            communication=CommunicationStyle(
                primary_intent=data["communication"]["primary_intent"],
                intent_distribution=data["communication"].get("intent_distribution", {}),
                verbosity=data["communication"].get("verbosity", 0.0),
                avg_turns_per_session=data["communication"].get("avg_turns_per_session", 0.0),
                response_promptness=data["communication"].get("response_promptness", "moderate"),
                expressiveness=data["communication"].get("expressiveness", 0.0),
            ),
            support_needs=SupportNeeds(
                complaint_frequency=data["support_needs"].get("complaint_frequency", 0.0),
                help_seeking_frequency=data["support_needs"].get("help_seeking_frequency", 0.0),
                validation_preference=SupportStyle(
                    data["support_needs"].get("validation_preference", "balanced")
                ),
                crisis_indicators=data["support_needs"].get("crisis_indicators", []),
                recovery_patterns=data["support_needs"].get("recovery_patterns", {}),
            ),
            confidence=data.get("confidence", 0.0),
        )
