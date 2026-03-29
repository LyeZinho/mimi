"""Conversational Markov chains (Layer 3 - Pattern Flow)."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ConversationState:
    """Represents a conversation state (mood + topic)."""
    
    mood: str
    topic: str = "general"
    
    def to_key(self) -> str:
        """Convert to string key for lookups."""
        return f"{self.mood}|{self.topic}"
    
    @classmethod
    def from_key(cls, key: str) -> ConversationState:
        """Create from string key."""
        parts = key.split("|")
        mood = parts[0] if parts else "STABLE"
        topic = parts[1] if len(parts) > 1 else "general"
        return cls(mood=mood, topic=topic)
    
    def __hash__(self) -> int:
        return hash(self.to_key())
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, ConversationState):
            return False
        return self.to_key() == other.to_key()


@dataclass
class TransitionRecord:
    """Records a state transition with metadata."""
    
    from_state: ConversationState
    to_state: ConversationState
    count: int = 1
    weight: float = 1.0
    last_seen: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)
    
    DECAY_RATE = 0.01
    
    def record_occurrence(self) -> None:
        """Record another occurrence of this transition."""
        self.count += 1
        self.last_seen = time.time()
        self.weight = min(1.0, self.weight + 0.1)
    
    def calculate_weight(self) -> float:
        """Calculate current weight with time decay.
        
        Formula: weight * e^(-DECAY_RATE * days_since_seen)
        """
        days_since = (time.time() - self.last_seen) / (24 * 3600)
        decay = 2.71828 ** (-self.DECAY_RATE * days_since)
        return self.weight * decay
    
    def to_dict(self) -> dict:
        """Convert to dictionary for persistence."""
        return {
            "from_state": self.from_state.to_key(),
            "to_state": self.to_state.to_key(),
            "count": self.count,
            "weight": self.weight,
            "last_seen": self.last_seen,
            "created_at": self.created_at,
        }


class ConversationalChainManager:
    """Manages Markov chain transitions between conversation states."""
    
    def __init__(self) -> None:
        self._transitions: dict[str, list[tuple[ConversationState, float, TransitionRecord]]] = {}
    
    def record_transition(self, from_state: ConversationState, to_state: ConversationState) -> None:
        """Record a transition from one state to another."""
        from_key = from_state.to_key()
        
        if from_key not in self._transitions:
            self._transitions[from_key] = []
        
        for to_state_existing, _, record in self._transitions[from_key]:
            if to_state_existing == to_state:
                record.record_occurrence()
                logger.debug(f"Updated transition {from_key} -> {to_state.to_key()}")
                return
        
        record = TransitionRecord(from_state=from_state, to_state=to_state)
        self._transitions[from_key].append((to_state, record.calculate_weight(), record))
        logger.debug(f"Added transition {from_key} -> {to_state.to_key()}")
    
    def get_transitions_from(self, state: ConversationState) -> list[tuple[ConversationState, float, TransitionRecord]]:
        """Get all transitions from a given state."""
        return self._transitions.get(state.to_key(), [])
    
    def predict_next_state(self, current_state: ConversationState) -> Optional[ConversationState]:
        """Predict the most likely next state."""
        transitions = self.get_transitions_from(current_state)
        
        if not transitions:
            return None
        
        sorted_trans = sorted(
            transitions,
            key=lambda t: (-t[2].calculate_weight(), -t[2].count),
        )
        
        return sorted_trans[0][0]
    
    def get_prediction_distribution(
        self,
        state: ConversationState,
        n: int = 3,
    ) -> list[tuple[ConversationState, float]]:
        """Get top N likely next states with probabilities."""
        transitions = self.get_transitions_from(state)
        
        if not transitions:
            return []
        
        weighted = [(t[0], t[2].calculate_weight(), t[2].count) for t in transitions]
        total_weight = sum(w for _, w, _ in weighted)
        
        if total_weight == 0:
            return []
        
        probabilities = [(s, w / total_weight) for s, w, _ in weighted]
        probabilities.sort(key=lambda x: x[1], reverse=True)
        return probabilities[:n]
    
    def prune_old_transitions(self, weight_threshold: float = 0.1) -> int:
        """Remove transitions with very low decayed weight.
        
        Returns: Number of transitions removed
        """
        removed = 0
        
        for from_key in list(self._transitions.keys()):
            transitions = self._transitions[from_key]
            valid = [t for t in transitions if t[2].calculate_weight() >= weight_threshold]
            
            if len(valid) < len(transitions):
                removed += len(transitions) - len(valid)
                self._transitions[from_key] = valid
            
            if not valid:
                del self._transitions[from_key]
        
        logger.info(f"Pruned {removed} low-weight transitions")
        return removed
    
    def clear(self) -> None:
        """Clear all transitions."""
        self._transitions.clear()
        logger.info("Conversational chains cleared")
    
    def to_dict(self) -> dict:
        """Export for persistence."""
        result = {}
        for from_key, transitions in self._transitions.items():
            result[from_key] = [t[2].to_dict() for t in transitions]
        return result
    
    @classmethod
    def from_dict(cls, data: dict) -> ConversationalChainManager:
        """Import from persisted data."""
        manager = cls()
        
        for from_key, transitions in data.items():
            from_state = ConversationState.from_key(from_key)
            for trans_data in transitions:
                to_state = ConversationState.from_key(trans_data["to_state"])
                record = TransitionRecord(
                    from_state=from_state,
                    to_state=to_state,
                    count=trans_data["count"],
                    weight=trans_data["weight"],
                    last_seen=trans_data["last_seen"],
                    created_at=trans_data["created_at"],
                )
                manager._transitions.setdefault(from_key, []).append(
                    (to_state, record.calculate_weight(), record)
                )
        
        return manager
