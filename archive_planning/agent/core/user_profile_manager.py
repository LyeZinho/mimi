"""Manager for analyzing long-term memory and building user profiles."""

from __future__ import annotations

import logging
import time
import json
from pathlib import Path
from typing import Optional
from collections import Counter, defaultdict
import sqlite3

from agent.core.user_profile import (
    UserProfile,
    PersonalityTraits,
    InterestProfile,
    CommunicationStyle,
    SupportNeeds,
    SupportStyle,
)

logger = logging.getLogger(__name__)


class UserProfileManager:
    """Analyzes long-term memory (Layer 4) to build comprehensive user profiles."""
    
    def __init__(self, db_path: str | Path, profile_path: str | Path = "data/user_profile.json"):
        """Initialize profile manager with Layer 4 database path.
        
        Args:
            db_path: Path to Layer 4 SQLite database (long_term_memory.db)
            profile_path: Path to save/load user profile JSON
        """
        self.db_path = Path(db_path)
        self.profile_path = Path(profile_path)
        self.profile_path.parent.mkdir(exist_ok=True)
        
        self.profile = self._load_or_create_profile()
    
    def _load_or_create_profile(self) -> UserProfile:
        """Load existing profile or create new one."""
        if self.profile_path.exists():
            try:
                with open(self.profile_path, "r") as f:
                    data = json.load(f)
                    profile = UserProfile.from_dict(data)
                    logger.info(f"Loaded user profile from {self.profile_path}")
                    return profile
            except Exception as e:
                logger.warning(f"Failed to load profile: {e}, creating new")
        
        return UserProfile()
    
    def save_profile(self) -> None:
        """Save current profile to disk."""
        try:
            with open(self.profile_path, "w") as f:
                json.dump(self.profile.to_dict(), f, indent=2)
            logger.info(f"Profile saved to {self.profile_path}")
        except Exception as e:
            logger.error(f"Failed to save profile: {e}")
    
    def analyze(self) -> UserProfile:
        """Analyze Layer 4 data and update profile.
        
        Returns:
            Updated UserProfile
        """
        if not self.db_path.exists():
            logger.warning(f"Layer 4 database not found at {self.db_path}")
            return self.profile
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                memories = conn.execute(
                    """
                    SELECT user_mood, agent_mood, intent, topics, user_input, 
                           importance_score, timestamp
                    FROM long_term_memories
                    ORDER BY timestamp ASC
                    """
                ).fetchall()
            
            if not memories:
                logger.warning("No memories in Layer 4 database")
                return self.profile
            
            self._analyze_personality(memories)
            self._analyze_interests(memories)
            self._analyze_communication(memories)
            self._analyze_support_needs(memories)
            
            self.profile.last_updated = time.time()
            self.profile.memory_turnover_count += 1
            self._calculate_confidence()
            
            self.save_profile()
            logger.info(f"Profile analysis complete (confidence: {self.profile.confidence:.2f})")
            return self.profile
        
        except Exception as e:
            logger.error(f"Failed to analyze profile: {e}")
            return self.profile
    
    def _analyze_personality(self, memories: list) -> None:
        """Analyze mood patterns to determine personality traits."""
        moods = [m[0] for m in memories]  # user_mood column
        
        if not moods:
            return
        
        mood_counts = Counter(moods)
        total_moods = len(moods)
        
        sorted_moods = mood_counts.most_common(2)
        
        self.profile.personality.dominant_mood = sorted_moods[0][0]
        self.profile.personality.dominant_mood_frequency = sorted_moods[0][1] / total_moods
        
        if len(sorted_moods) > 1:
            self.profile.personality.secondary_mood = sorted_moods[1][0]
            self.profile.personality.secondary_mood_frequency = sorted_moods[1][1] / total_moods
        
        mood_values = {
            "ENERGIZED": 1.0,
            "HAPPY": 0.8,
            "CONTENT": 0.6,
            "STABLE": 0.4,
            "NEUTRAL": 0.3,
            "ANXIOUS": -0.4,
            "SAD": -0.8,
            "DEPRESSED": -1.0,
        }
        
        numeric_moods = [mood_values.get(m, 0.0) for m in moods]
        mean_mood = sum(numeric_moods) / len(numeric_moods) if numeric_moods else 0.0
        variance = sum((m - mean_mood) ** 2 for m in numeric_moods) / len(numeric_moods)
        std_dev = variance ** 0.5
        
        self.profile.personality.emotional_range = std_dev
        
        if len(moods) > 2:
            self.profile.personality.mood_resilience = self._calculate_resilience(moods)
    
    def _calculate_resilience(self, moods: list[str]) -> float:
        """Calculate how quickly user recovers from negative moods.
        
        Higher value = faster recovery (more resilient).
        """
        negative_moods = {"ANXIOUS", "SAD", "DEPRESSED"}
        recovery_times = []
        
        in_negative_state = False
        negative_start = 0
        
        for i, mood in enumerate(moods):
            if mood in negative_moods:
                if not in_negative_state:
                    in_negative_state = True
                    negative_start = i
            else:
                if in_negative_state:
                    recovery_times.append(i - negative_start)
                    in_negative_state = False
        
        if not recovery_times:
            return 0.5
        
        avg_recovery = sum(recovery_times) / len(recovery_times)
        max_recovery = max(recovery_times)
        
        resilience = 1.0 - min(avg_recovery / (max_recovery + 1), 0.99)
        return resilience
    
    def _analyze_interests(self, memories: list) -> None:
        """Analyze topics to determine interests and passions."""
        all_topics = []
        topic_importance = defaultdict(list)
        
        for memory in memories:
            topics_str = memory[3]
            importance = memory[5]
            
            if topics_str:
                try:
                    import json as json_module
                    topics = json_module.loads(topics_str)
                    all_topics.extend(topics)
                    for topic in topics:
                        topic_importance[topic].append(importance)
                except:
                    pass
        
        if not all_topics:
            return
        
        topic_counts = Counter(all_topics)
        total_topics = len(all_topics)
        unique_topics = len(topic_counts)
        
        self.profile.interests.primary_topics = [
            (topic, count / total_topics, sum(topic_importance[topic]) / len(topic_importance[topic]))
            for topic, count in topic_counts.most_common(5)
        ]
        
        self.profile.interests.passion_level = sum(
            v for _, _, v in self.profile.interests.primary_topics
        ) / len(self.profile.interests.primary_topics) if self.profile.interests.primary_topics else 0.0
        
        self.profile.interests.new_topic_frequency = unique_topics / max(total_topics, 1)
        
        self.profile.interests.recurring_concerns = [
            (topic, count) for topic, count in topic_counts.most_common(3)
        ]
    
    def _analyze_communication(self, memories: list) -> None:
        """Analyze communication patterns and style."""
        intents = [m[2] for m in memories]
        user_inputs = [m[4] for m in memories]
        
        if not intents:
            return
        
        intent_counts = Counter(intents)
        total_intents = len(intents)
        
        self.profile.communication.primary_intent = intent_counts.most_common(1)[0][0]
        self.profile.communication.intent_distribution = {
            intent: count / total_intents
            for intent, count in intent_counts.items()
        }
        
        if user_inputs:
            avg_input_length = sum(len(inp) for inp in user_inputs) / len(user_inputs)
            self.profile.communication.verbosity = min(avg_input_length / 500.0, 1.0)
        
        self.profile.communication.avg_turns_per_session = len(memories) / max(self.profile.memory_turnover_count, 1)
        
        self.profile.communication.expressiveness = self.profile.interests.passion_level
    
    def _analyze_support_needs(self, memories: list) -> None:
        """Analyze support patterns and help-seeking behavior."""
        intents = [m[2] for m in memories]
        moods = [m[0] for m in memories]
        
        complaint_count = sum(1 for intent in intents if intent == "complaint")
        request_count = sum(1 for intent in intents if intent == "request")
        total_intents = len(intents)
        
        self.profile.support_needs.complaint_frequency = complaint_count / max(total_intents, 1)
        self.profile.support_needs.help_seeking_frequency = request_count / max(total_intents, 1)
        
        if complaint_count > total_intents * 0.3:
            if request_count > total_intents * 0.3:
                self.profile.support_needs.validation_preference = SupportStyle.BALANCED
            else:
                self.profile.support_needs.validation_preference = SupportStyle.EMOTIONAL
        elif request_count > total_intents * 0.3:
            self.profile.support_needs.validation_preference = SupportStyle.PRACTICAL
        else:
            self.profile.support_needs.validation_preference = SupportStyle.BALANCED
        
        if "DEPRESSED" in moods:
            if moods.count("DEPRESSED") > len(moods) * 0.2:
                self.profile.support_needs.crisis_indicators.append("persistent_depression")
        
        if "ANXIOUS" in moods:
            if moods.count("ANXIOUS") > len(moods) * 0.3:
                self.profile.support_needs.crisis_indicators.append("high_anxiety")
    
    def _calculate_confidence(self) -> None:
        """Calculate overall profile confidence (0-1)."""
        if self.profile.memory_turnover_count == 0:
            self.profile.confidence = 0.0
            return
        
        memory_score = min(self.profile.memory_turnover_count / 10.0, 1.0)
        
        topic_diversity = len(self.profile.interests.recurring_concerns) / 3.0
        
        mood_distribution_score = (
            self.profile.personality.dominant_mood_frequency +
            (self.profile.personality.secondary_mood_frequency if self.profile.personality.secondary_mood else 0.0)
        ) / 2.0
        
        self.profile.confidence = (memory_score + topic_diversity + mood_distribution_score) / 3.0
    
    def get_profile_summary(self) -> str:
        """Generate a human-readable profile summary."""
        lines = []
        lines.append("=== USER PROFILE SUMMARY ===")
        lines.append("")
        
        lines.append("PERSONALITY:")
        lines.append(f"  Dominant Mood: {self.profile.personality.dominant_mood} ({self.profile.personality.dominant_mood_frequency:.1%})")
        if self.profile.personality.secondary_mood:
            lines.append(f"  Secondary Mood: {self.profile.personality.secondary_mood} ({self.profile.personality.secondary_mood_frequency:.1%})")
        lines.append(f"  Emotional Range: {self.profile.personality.emotional_range:.2f} (σ)")
        lines.append(f"  Mood Resilience: {self.profile.personality.mood_resilience:.1%}")
        lines.append("")
        
        lines.append("INTERESTS:")
        for topic, frequency, importance in self.profile.interests.primary_topics[:3]:
            lines.append(f"  - {topic}: {frequency:.1%} frequency, {importance:.2f} importance")
        lines.append(f"  Passion Level: {self.profile.interests.passion_level:.2f}")
        lines.append("")
        
        lines.append("COMMUNICATION STYLE:")
        lines.append(f"  Primary Intent: {self.profile.communication.primary_intent}")
        lines.append(f"  Verbosity: {self.profile.communication.verbosity:.1%}")
        lines.append(f"  Expressiveness: {self.profile.communication.expressiveness:.2f}")
        lines.append("")
        
        lines.append("SUPPORT NEEDS:")
        lines.append(f"  Complaint Frequency: {self.profile.support_needs.complaint_frequency:.1%}")
        lines.append(f"  Help-Seeking Frequency: {self.profile.support_needs.help_seeking_frequency:.1%}")
        lines.append(f"  Validation Preference: {self.profile.support_needs.validation_preference.value}")
        if self.profile.support_needs.crisis_indicators:
            lines.append(f"  Crisis Indicators: {', '.join(self.profile.support_needs.crisis_indicators)}")
        lines.append("")
        
        lines.append(f"PROFILE CONFIDENCE: {self.profile.confidence:.1%}")
        lines.append(f"Last Updated: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.profile.last_updated))}")
        
        return "\n".join(lines)
