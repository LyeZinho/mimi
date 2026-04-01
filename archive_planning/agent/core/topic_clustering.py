"""Topic clustering (Layer 2 - Pattern Recognition)."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class TopicCluster:
    """Represents a recurring topic in conversation."""
    
    topic_name: str
    frequency: int = 1
    last_seen: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)
    co_occurrences: dict[str, int] = field(default_factory=dict)
    mood_associations: dict[str, float] = field(default_factory=dict)
    
    DECAY_RATE = 0.05
    
    def calculate_importance(self) -> float:
        """Calculate decayed importance score.
        
        Formula: frequency * e^(-DECAY_RATE * hours_since_seen)
        """
        hours_since = (time.time() - self.last_seen) / 3600
        decay = 2.71828 ** (-self.DECAY_RATE * hours_since)
        return self.frequency * decay
    
    def record_co_occurrence(self, other_topic: str) -> None:
        """Record co-occurrence with another topic."""
        self.co_occurrences[other_topic] = self.co_occurrences.get(other_topic, 0) + 1
    
    def record_mood_association(self, mood: str, strength: float = 0.8) -> None:
        """Record association with a mood."""
        current = self.mood_associations.get(mood, 0.0)
        self.mood_associations[mood] = 0.7 * current + 0.3 * strength
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for persistence."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TopicCluster:
        """Create from dictionary."""
        return cls(**data)


class TopicClusterManager:
    """Manages collection of topic clusters with updates and queries."""
    
    def __init__(self) -> None:
        self._clusters: dict[str, TopicCluster] = {}
    
    def add_topics(
        self,
        topics: list[str],
        current_mood: str = "STABLE",
        mood_strength: float = 0.8,
    ) -> None:
        """Add or update topics and their co-occurrences.
        
        Args:
            topics: List of topic keywords
            current_mood: Current mood of user/agent
            mood_strength: Strength of mood-topic association (0-1)
        """
        now = time.time()
        
        for topic in topics:
            if topic not in self._clusters:
                self._clusters[topic] = TopicCluster(topic_name=topic)
            
            cluster = self._clusters[topic]
            cluster.frequency += 1
            cluster.last_seen = now
            cluster.record_mood_association(current_mood, mood_strength)
        
        for i, topic1 in enumerate(topics):
            for topic2 in topics[i + 1:]:
                self._clusters[topic1].record_co_occurrence(topic2)
                self._clusters[topic2].record_co_occurrence(topic1)
        
        logger.debug(f"Added topics: {topics} in mood {current_mood}")
    
    def get_cluster(self, topic: str) -> Optional[TopicCluster]:
        """Get specific topic cluster."""
        return self._clusters.get(topic)
    
    def get_all(self) -> list[TopicCluster]:
        """Get all clusters."""
        return list(self._clusters.values())
    
    def get_top_by_importance(self, n: int = 5) -> list[TopicCluster]:
        """Get top N topics by decayed importance."""
        sorted_clusters = sorted(
            self._clusters.values(),
            key=lambda c: c.calculate_importance(),
            reverse=True,
        )
        return sorted_clusters[:n]
    
    def get_summary(self, n: int = 5) -> str:
        """Get human-readable topic summary for LLM prompt."""
        top_topics = self.get_top_by_importance(n)
        
        if not top_topics:
            return "No topics discussed yet."
        
        lines = ["Key topics in this conversation:"]
        for topic in top_topics:
            importance = topic.calculate_importance()
            if topic.mood_associations:
                top_mood = max(topic.mood_associations, key=topic.mood_associations.get)
                lines.append(f"- {topic.topic_name} (appears {topic.frequency}x, often {top_mood})")
            else:
                lines.append(f"- {topic.topic_name} (appears {topic.frequency}x)")
        
        return "\n".join(lines)
    
    def prune_old_topics(self, importance_threshold: float = 2.0) -> int:
        """Remove topics with low decayed importance.
        
        Returns: Number of topics removed
        """
        to_remove = [
            topic for topic, cluster in self._clusters.items()
            if cluster.calculate_importance() < importance_threshold
        ]
        
        for topic in to_remove:
            del self._clusters[topic]
        
        logger.info(f"Pruned {len(to_remove)} low-importance topics")
        return len(to_remove)
    
    def clear(self) -> None:
        """Clear all topics."""
        self._clusters.clear()
        logger.info("Topic clusters cleared")
    
    def to_dict(self) -> dict[str, dict[str, Any]]:
        """Export all clusters for persistence."""
        return {name: cluster.to_dict() for name, cluster in self._clusters.items()}
    
    @classmethod
    def from_dict(cls, data: dict[str, dict[str, Any]]) -> TopicClusterManager:
        """Import from persisted data."""
        manager = cls()
        for topic_name, cluster_data in data.items():
            manager._clusters[topic_name] = TopicCluster.from_dict(cluster_data)
        return manager
