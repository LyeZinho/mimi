"""Conversation context data structures."""

from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class ConversationContext:
    """Single conversation turn with metadata."""
    
    turn_id: int
    user_input: str
    agent_response: str
    user_mood: str
    agent_mood: str
    intent: str
    topics: list[str] = field(default_factory=list)
    entities: dict[str, str] = field(default_factory=dict)
    importance_score: float = 0.5
    timestamp: float = field(default_factory=time.time)
    user_mood_confidence: float = 0.5
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    def to_json_serializable(self) -> dict[str, Any]:
        """Ensure all fields are JSON-serializable."""
        data = self.to_dict()
        data["timestamp"] = float(data["timestamp"])
        data["user_mood_confidence"] = float(data["user_mood_confidence"])
        data["importance_score"] = float(data["importance_score"])
        return data
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConversationContext:
        """Create from dictionary."""
        return cls(**data)
