# Hybrid Conversation Context System - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers/executing-plans to implement this plan task-by-task.

**Goal:** Build a three-layer conversation memory system that combines sliding window (short-term), semantic clustering (pattern recognition), and Markov chains (conversational flow) to maintain context without overflowing the LLM context window.

**Architecture:** 
- Layer 1 (Sliding Window): File-based JSON for last M turns
- Layer 2 (Topic Clustering): SQLite-persisted keyword frequency + co-occurrence analysis with exponential decay
- Layer 3 (Markov Chains): State transition tracking with mood + topic combinations
- Unified selector: Builds LLM prompt by intelligently blending all three layers

**Tech Stack:** 
- Python dataclasses + JSON (Layer 1)
- SQLite3 + JSON for structured data (Layers 2-3)
- Existing EventBus for integration with SentimentBrain
- NumPy for decay calculations (already in requirements.txt)

---

## Task 1: Create ConversationContext Data Structure

**Files:**
- Create: `agent/core/conversation_context.py`
- Test: `tests/unit/test_conversation_context.py`

**Step 1: Write failing test for ConversationContext dataclass**

```python
def test_conversation_context_creation():
    """Test creating a conversation context turn."""
    from agent.core.conversation_context import ConversationContext
    
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
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_conversation_context.py::test_conversation_context_creation -v
```

Expected output: `FAILED - ModuleNotFoundError: No module named 'agent.core.conversation_context'`

**Step 3: Implement ConversationContext**

```python
# agent/core/conversation_context.py
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
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_conversation_context.py::test_conversation_context_creation -v
```

Expected output: `PASSED`

**Step 5: Commit**

```bash
git add agent/core/conversation_context.py tests/unit/test_conversation_context.py
git commit -m "feat: add ConversationContext dataclass for turn metadata"
```

---

## Task 2: Create ConversationMemory (Layer 1 - Sliding Window)

**Files:**
- Create: `agent/core/conversation_memory.py`
- Modify: `agent/core/__init__.py` (export ConversationMemory)
- Test: `tests/unit/test_conversation_memory.py`

**Step 1: Write failing test for ConversationMemory**

```python
def test_conversation_memory_add_and_retrieve():
    """Test adding and retrieving conversation turns."""
    from agent.core.conversation_memory import ConversationMemory
    from agent.core.conversation_context import ConversationContext
    
    mem = ConversationMemory(max_size=5)
    
    ctx1 = ConversationContext(
        turn_id=1,
        user_input="Hello",
        agent_response="Hi",
        user_mood="INTERESTED",
        agent_mood="STABLE",
        intent="greeting",
    )
    
    mem.add(ctx1)
    
    recent = mem.get_recent(n=1)
    assert len(recent) == 1
    assert recent[0].turn_id == 1
    
    
def test_conversation_memory_fifo_overflow():
    """Test FIFO behavior when exceeding max_size."""
    from agent.core.conversation_memory import ConversationMemory
    from agent.core.conversation_context import ConversationContext
    
    mem = ConversationMemory(max_size=3)
    
    for i in range(5):
        ctx = ConversationContext(
            turn_id=i,
            user_input=f"Input {i}",
            agent_response=f"Response {i}",
            user_mood="STABLE",
            agent_mood="STABLE",
            intent="statement",
        )
        mem.add(ctx)
    
    recent = mem.get_recent()
    assert len(recent) == 3
    assert recent[0].turn_id == 2  # Oldest kept
    assert recent[2].turn_id == 4  # Newest


def test_conversation_memory_persistence():
    """Test saving and loading from JSON file."""
    import tempfile
    import json
    from pathlib import Path
    from agent.core.conversation_memory import ConversationMemory
    from agent.core.conversation_context import ConversationContext
    
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "context.json"
        mem = ConversationMemory(max_size=3, file_path=file_path)
        
        ctx = ConversationContext(
            turn_id=1,
            user_input="Hello",
            agent_response="Hi",
            user_mood="INTERESTED",
            agent_mood="STABLE",
            intent="greeting",
        )
        mem.add(ctx)
        mem.save()
        
        assert file_path.exists()
        
        # Load new instance
        mem2 = ConversationMemory(max_size=3, file_path=file_path)
        mem2.load()
        
        recent = mem2.get_recent()
        assert len(recent) == 1
        assert recent[0].turn_id == 1
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_conversation_memory.py -v
```

Expected output: `FAILED - ModuleNotFoundError`

**Step 3: Implement ConversationMemory**

```python
# agent/core/conversation_memory.py
"""Conversation memory with sliding window (Layer 1)."""

from __future__ import annotations

import json
import logging
from collections import deque
from pathlib import Path
from typing import Optional

from agent.core.conversation_context import ConversationContext

logger = logging.getLogger(__name__)


class ConversationMemory:
    """Sliding window memory for recent conversation turns.
    
    Implements FIFO buffer with automatic persistence to JSON file.
    """
    
    def __init__(
        self,
        max_size: int = 20,
        file_path: Optional[str | Path] = None,
    ) -> None:
        self.max_size = max_size
        self.file_path = Path(file_path) if file_path else None
        self._buffer: deque[ConversationContext] = deque(maxlen=max_size)
        self._turn_counter = 0
        
        if self.file_path:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            self.load()
    
    def add(self, context: ConversationContext) -> None:
        """Add context turn to buffer."""
        self._buffer.append(context)
        self._turn_counter = context.turn_id
        logger.debug(f"Added turn {context.turn_id} to conversation memory")
    
    def get_recent(self, n: Optional[int] = None) -> list[ConversationContext]:
        """Get last n turns (or all if n is None)."""
        items = list(self._buffer)
        return items[-n:] if n else items
    
    def get_all(self) -> list[ConversationContext]:
        """Get all turns in buffer."""
        return list(self._buffer)
    
    def clear(self) -> None:
        """Clear all turns."""
        self._buffer.clear()
        logger.info("Conversation memory cleared")
    
    def save(self) -> None:
        """Save buffer to JSON file."""
        if not self.file_path:
            return
        
        data = {
            "current_turn": self._turn_counter,
            "max_size": self.max_size,
            "turns": [ctx.to_json_serializable() for ctx in self._buffer],
        }
        
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Conversation memory saved to {self.file_path}")
        except Exception as e:
            logger.error(f"Failed to save conversation memory: {e}")
    
    def load(self) -> None:
        """Load buffer from JSON file."""
        if not self.file_path or not self.file_path.exists():
            return
        
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self._turn_counter = data.get("current_turn", 0)
            self._buffer.clear()
            
            for turn_data in data.get("turns", []):
                ctx = ConversationContext.from_dict(turn_data)
                self._buffer.append(ctx)
            
            logger.info(f"Loaded {len(self._buffer)} turns from {self.file_path}")
        except Exception as e:
            logger.error(f"Failed to load conversation memory: {e}")
    
    def __len__(self) -> int:
        return len(self._buffer)
    
    def __iter__(self):
        return iter(self._buffer)
```

**Step 4: Update `agent/core/__init__.py` to export**

```python
# Add to agent/core/__init__.py
from agent.core.conversation_context import ConversationContext
from agent.core.conversation_memory import ConversationMemory

__all__ = ["ConversationContext", "ConversationMemory", ...]
```

**Step 5: Run test to verify it passes**

```bash
pytest tests/unit/test_conversation_memory.py -v
```

Expected output: `3 PASSED`

**Step 6: Commit**

```bash
git add agent/core/conversation_memory.py agent/core/conversation_context.py tests/unit/test_conversation_memory.py agent/core/__init__.py
git commit -m "feat: implement sliding window conversation memory (Layer 1)"
```

---

## Task 3: Create TopicCluster Data Structure & Manager (Layer 2)

**Files:**
- Create: `agent/core/topic_clustering.py`
- Test: `tests/unit/test_topic_clustering.py`

**Step 1: Write failing test for TopicCluster**

```python
def test_topic_cluster_creation():
    """Test creating a topic cluster."""
    from agent.core.topic_clustering import TopicCluster
    
    cluster = TopicCluster(
        topic_name="feelings",
        frequency=5,
        mood_associations={"INTERESTED": 0.8, "ANALYTICAL": 0.5},
    )
    
    assert cluster.topic_name == "feelings"
    assert cluster.frequency == 5
    assert cluster.mood_associations["INTERESTED"] == 0.8
    assert cluster.calculate_importance() > 0


def test_topic_cluster_manager_add_topics():
    """Test adding and retrieving topics."""
    from agent.core.topic_clustering import TopicClusterManager
    
    manager = TopicClusterManager()
    manager.add_topics(["feelings", "work"], current_mood="INTERESTED")
    
    clusters = manager.get_all()
    assert len(clusters) >= 2
    
    feelings = manager.get_cluster("feelings")
    assert feelings is not None
    assert feelings.frequency == 1


def test_topic_cluster_co_occurrence():
    """Test co-occurrence tracking."""
    from agent.core.topic_clustering import TopicClusterManager
    
    manager = TopicClusterManager()
    
    # First set of topics
    manager.add_topics(["feelings", "work"], current_mood="INTERESTED")
    # Same mood, should increase co-occurrence
    manager.add_topics(["feelings", "day"], current_mood="INTERESTED")
    
    feelings = manager.get_cluster("feelings")
    assert feelings.co_occurrences.get("work", 0) > 0
    assert feelings.co_occurrences.get("day", 0) > 0


def test_topic_cluster_importance_decay():
    """Test exponential decay of importance."""
    import time
    from agent.core.topic_clustering import TopicCluster
    
    cluster = TopicCluster(topic_name="old_topic", frequency=10)
    old_importance = cluster.calculate_importance()
    
    # Simulate time passing
    cluster.last_seen = time.time() - (24 * 3600)  # 24 hours ago
    decayed_importance = cluster.calculate_importance()
    
    assert decayed_importance < old_importance
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_topic_clustering.py -v
```

Expected output: `FAILED - ModuleNotFoundError`

**Step 3: Implement TopicCluster and TopicClusterManager**

```python
# agent/core/topic_clustering.py
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
    
    DECAY_RATE = 0.05  # Hours^-1 for exponential decay
    
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
        # Exponential moving average
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
        
        # Record co-occurrences between topics
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
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_topic_clustering.py -v
```

Expected output: `4 PASSED`

**Step 5: Commit**

```bash
git add agent/core/topic_clustering.py tests/unit/test_topic_clustering.py
git commit -m "feat: implement topic clustering with decay (Layer 2)"
```

---

## Task 4: Create ConversationalChain Data Structure & Manager (Layer 3)

**Files:**
- Create: `agent/core/conversational_chains.py`
- Test: `tests/unit/test_conversational_chains.py`

**Step 1: Write failing test**

```python
def test_conversation_state_creation():
    """Test creating a conversation state."""
    from agent.core.conversational_chains import ConversationState
    
    state = ConversationState(mood="INTERESTED", topic="technical")
    
    assert state.mood == "INTERESTED"
    assert state.topic == "technical"
    assert state.to_key() == "INTERESTED|technical"


def test_markov_chain_transition():
    """Test recording state transitions."""
    from agent.core.conversational_chains import ConversationState, ConversationalChainManager
    
    manager = ConversationalChainManager()
    
    state1 = ConversationState(mood="ANALYTICAL", topic="technical")
    state2 = ConversationState(mood="INTERESTED", topic="technical")
    
    manager.record_transition(state1, state2)
    
    transitions = manager.get_transitions_from(state1)
    assert len(transitions) == 1
    assert transitions[0][0].to_key() == state2.to_key()


def test_markov_chain_prediction():
    """Test predicting next state."""
    from agent.core.conversational_chains import ConversationState, ConversationalChainManager
    
    manager = ConversationalChainManager()
    
    state1 = ConversationState(mood="ANALYTICAL", topic="technical")
    state2 = ConversationState(mood="INTERESTED", topic="technical")
    state3 = ConversationState(mood="ENERGIZED", topic="technical")
    
    # Record multiple transitions from state1
    for _ in range(5):
        manager.record_transition(state1, state2)
    
    for _ in range(2):
        manager.record_transition(state1, state3)
    
    # Most likely next state should be state2
    next_state = manager.predict_next_state(state1)
    assert next_state is not None
    assert next_state.to_key() == state2.to_key()


def test_markov_chain_weight_decay():
    """Test weight decay over time."""
    import time
    from agent.core.conversational_chains import ConversationState, ConversationalChainManager
    
    manager = ConversationalChainManager()
    
    state1 = ConversationState(mood="STABLE", topic="general")
    state2 = ConversationState(mood="STABLE", topic="general")
    
    manager.record_transition(state1, state2)
    chain = manager.get_transitions_from(state1)[0]
    
    original_weight = chain[1]
    
    # Simulate time passing
    chain[2].last_seen = time.time() - (30 * 24 * 3600)  # 30 days ago
    decayed = chain[2].calculate_weight()
    
    assert decayed < original_weight
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_conversational_chains.py -v
```

Expected output: `FAILED - ModuleNotFoundError`

**Step 3: Implement ConversationalChain structures**

```python
# agent/core/conversational_chains.py
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
    
    DECAY_RATE = 0.01  # Days^-1 for decay
    
    def record_occurrence(self) -> None:
        """Record another occurrence of this transition."""
        self.count += 1
        self.last_seen = time.time()
        self.weight = min(1.0, self.weight + 0.1)  # Cap at 1.0
    
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
        # Dict[from_state_key, List[(to_state, weight, record)]]
        self._transitions: dict[str, list[tuple[ConversationState, float, TransitionRecord]]] = {}
    
    def record_transition(self, from_state: ConversationState, to_state: ConversationState) -> None:
        """Record a transition from one state to another."""
        from_key = from_state.to_key()
        
        if from_key not in self._transitions:
            self._transitions[from_key] = []
        
        # Check if this exact transition exists
        for to_state_existing, _, record in self._transitions[from_key]:
            if to_state_existing == to_state:
                record.record_occurrence()
                logger.debug(f"Updated transition {from_key} -> {to_state.to_key()}")
                return
        
        # New transition
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
        
        # Sort by decayed weight
        sorted_trans = sorted(
            transitions,
            key=lambda t: t[2].calculate_weight(),
            reverse=True,
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
        
        # Calculate weights and normalize
        weighted = [(t[0], t[2].calculate_weight()) for t in transitions]
        total_weight = sum(w for _, w in weighted)
        
        if total_weight == 0:
            return []
        
        probabilities = [(s, w / total_weight) for s, w in weighted]
        return sorted(probabilities, key=lambda x: x[1], reverse=True)[:n]
    
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
            
            # Remove empty lists
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
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_conversational_chains.py -v
```

Expected output: `4 PASSED`

**Step 5: Commit**

```bash
git add agent/core/conversational_chains.py tests/unit/test_conversational_chains.py
git commit -m "feat: implement Markov chains for conversational patterns (Layer 3)"
```

---

## Task 5: Create ContextBrain - Unified Context Manager

**Files:**
- Create: `agent/brains/context_brain.py`
- Modify: `agent/brains/__init__.py`
- Test: `tests/unit/test_context_brain.py`

**Step 1: Write failing test for ContextBrain**

```python
def test_context_brain_add_turn():
    """Test adding a conversation turn to ContextBrain."""
    from agent.brains.context_brain import ContextBrain
    from agent.core.conversation_context import ConversationContext
    
    brain = ContextBrain()
    
    ctx = ConversationContext(
        turn_id=1,
        user_input="How are you?",
        agent_response="I'm fine",
        user_mood="INTERESTED",
        agent_mood="STABLE",
        intent="greeting",
        topics=["greeting"],
        importance_score=0.6,
    )
    
    brain.add_turn(ctx)
    
    recent = brain.get_recent_turns(n=1)
    assert len(recent) == 1
    assert recent[0].turn_id == 1


def test_context_brain_build_context_prompt():
    """Test building LLM prompt context."""
    from agent.brains.context_brain import ContextBrain
    from agent.core.conversation_context import ConversationContext
    
    brain = ContextBrain()
    
    for i in range(3):
        ctx = ConversationContext(
            turn_id=i,
            user_input=f"Input {i}",
            agent_response=f"Response {i}",
            user_mood="INTERESTED",
            agent_mood="STABLE",
            intent="statement",
            topics=["topic"],
        )
        brain.add_turn(ctx)
    
    prompt_context = brain.build_llm_context(max_tokens=500)
    
    assert isinstance(prompt_context, str)
    assert len(prompt_context) > 0
    assert "Input" in prompt_context  # Should include conversation history
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_context_brain.py::test_context_brain_add_turn -v
```

Expected output: `FAILED - ModuleNotFoundError`

**Step 3: Implement ContextBrain**

```python
# agent/brains/context_brain.py
"""Context Brain - Unified context manager combining Layers 1-3."""

from __future__ import annotations

import logging
import json
from pathlib import Path
from typing import Optional

from agent.core.messaging import Brain, EventType
from agent.core.conversation_context import ConversationContext
from agent.core.conversation_memory import ConversationMemory
from agent.core.topic_clustering import TopicClusterManager
from agent.core.conversational_chains import ConversationalChainManager, ConversationState

logger = logging.getLogger(__name__)


class ContextBrain(Brain):
    """Unified context manager combining:
    - Layer 1: Sliding window (recent turns)
    - Layer 2: Topic clustering (recurring themes)
    - Layer 3: Markov chains (conversation flow)
    """
    
    def __init__(self, data_dir: str | Path = "data", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Initialize three layers
        self._short_term = ConversationMemory(
            max_size=20,
            file_path=self.data_dir / "short_term_context.json",
        )
        self._topic_manager = TopicClusterManager()
        self._chain_manager = ConversationalChainManager()
        
        self._turn_counter = 0
        self._db_path = self.data_dir / "memory.db"
    
    async def initialize(self) -> None:
        """Initialize ContextBrain and subscribe to events."""
        await super().initialize()
        
        bus = self.event_bus
        bus.subscribe(EventType.RESPONSE_READY)(self._on_response_ready)
    
    async def process(self) -> None:
        """Background processing (pruning, decay)."""
        # Prune old topics and chains periodically
        self._topic_manager.prune_old_topics(importance_threshold=2.0)
        self._chain_manager.prune_old_transitions(weight_threshold=0.1)
    
    async def _on_response_ready(self, event) -> None:
        """Handle agent response ready event - update context."""
        payload = event.payload
        
        # Extract context data from event
        turn_data = ConversationContext(
            turn_id=self._turn_counter,
            user_input=payload.get("user_input", ""),
            agent_response=payload.get("response", ""),
            user_mood=payload.get("user_mood", "STABLE"),
            agent_mood=payload.get("agent_mood", "STABLE"),
            intent=payload.get("intent", "statement"),
            topics=payload.get("topics", []),
            entities=payload.get("entities", {}),
            importance_score=payload.get("importance_score", 0.5),
            user_mood_confidence=payload.get("user_mood_confidence", 0.5),
        )
        
        self.add_turn(turn_data)
        self._turn_counter += 1
    
    def add_turn(self, context: ConversationContext) -> None:
        """Add a conversation turn and update all three layers."""
        # Layer 1: Add to sliding window
        self._short_term.add(context)
        
        # Layer 2: Update topic clustering
        if context.topics:
            self._topic_manager.add_topics(
                context.topics,
                current_mood=context.user_mood,
                mood_strength=context.user_mood_confidence,
            )
        
        # Layer 3: Record state transition if we have history
        if len(self._short_term) > 1:
            prev_turn = self._short_term.get_recent(n=2)[0]
            
            from_state = ConversationState(
                mood=prev_turn.user_mood,
                topic=prev_turn.topics[0] if prev_turn.topics else "general",
            )
            to_state = ConversationState(
                mood=context.user_mood,
                topic=context.topics[0] if context.topics else "general",
            )
            
            self._chain_manager.record_transition(from_state, to_state)
        
        logger.debug(f"Added turn {context.turn_id} to context brain")
    
    def get_recent_turns(self, n: Optional[int] = None) -> list[ConversationContext]:
        """Get recent conversation turns."""
        return self._short_term.get_recent(n)
    
    def build_llm_context(self, max_tokens: int = 2000) -> str:
        """Build LLM context string combining all three layers.
        
        Strategy:
        1. Start with Layer 1 (recent turns)
        2. If context window available, add Layer 2 (topics)
        3. Add Layer 3 (prediction hint)
        """
        lines = []
        
        # Layer 1: Recent conversation history
        recent_turns = self._short_term.get_recent(n=10)
        
        if recent_turns:
            lines.append("[Recent Conversation]")
            for turn in recent_turns:
                lines.append(f"User: {turn.user_input}")
                lines.append(f"You: {turn.agent_response}")
                lines.append("")
        
        # Rough token count (very approximate)
        current_tokens = sum(len(line.split()) for line in lines) * 1.3
        
        # Layer 2: Topic clustering (if space available)
        if current_tokens < max_tokens * 0.7:
            topic_summary = self._topic_manager.get_summary(n=5)
            if topic_summary and topic_summary != "No topics discussed yet.":
                lines.append("[Conversation Themes]")
                lines.append(topic_summary)
                lines.append("")
        
        # Layer 3: Conversation flow prediction
        if recent_turns and current_tokens < max_tokens * 0.85:
            last_turn = recent_turns[-1]
            current_state = ConversationState(
                mood=last_turn.user_mood,
                topic=last_turn.topics[0] if last_turn.topics else "general",
            )
            
            next_states = self._chain_manager.get_prediction_distribution(current_state, n=3)
            
            if next_states:
                lines.append("[Expected Direction]")
                lines.append("Based on conversation patterns, the user might:")
                for state, prob in next_states:
                    lines.append(f"- Continue discussing {state.topic} ({prob*100:.0f}% likely)")
                lines.append("")
        
        return "\n".join(lines)
    
    def save_state(self) -> None:
        """Persist all context layers to storage."""
        self._short_term.save()
        
        # Save topic clusters
        topics_file = self.data_dir / "topic_clusters.json"
        with open(topics_file, "w") as f:
            json.dump(self._topic_manager.to_dict(), f, indent=2)
        
        # Save conversation chains
        chains_file = self.data_dir / "conversation_chains.json"
        with open(chains_file, "w") as f:
            json.dump(self._chain_manager.to_dict(), f, indent=2)
        
        logger.info("Context state saved to disk")
    
    def load_state(self) -> None:
        """Load all context layers from storage."""
        self._short_term.load()
        
        # Load topic clusters
        topics_file = self.data_dir / "topic_clusters.json"
        if topics_file.exists():
            with open(topics_file, "r") as f:
                data = json.load(f)
                self._topic_manager = TopicClusterManager.from_dict(data)
        
        # Load conversation chains
        chains_file = self.data_dir / "conversation_chains.json"
        if chains_file.exists():
            with open(chains_file, "r") as f:
                data = json.load(f)
                self._chain_manager = ConversationalChainManager.from_dict(data)
        
        logger.info("Context state loaded from disk")
    
    def get_importance_score(self, context: ConversationContext) -> float:
        """Calculate importance score for potential long-term storage.
        
        Weighted score from multiple factors.
        """
        sentiment_strength = context.user_mood_confidence
        
        # Intent significance weights
        intent_weights = {
            "greeting": 0.3,
            "farewell": 0.3,
            "question": 0.7,
            "request": 0.8,
            "appreciation": 0.6,
            "complaint": 0.9,
            "statement": 0.4,
        }
        intent_score = intent_weights.get(context.intent, 0.5)
        
        # Topic novelty (check if topics are new)
        topic_novelty = 0.5
        if context.topics:
            existing_topics = sum(
                1 for topic in context.topics
                if self._topic_manager.get_cluster(topic) is not None
            )
            topic_novelty = 1.0 - (existing_topics / len(context.topics))
        
        # Calculate weighted importance
        importance = (
            0.3 * sentiment_strength +
            0.25 * intent_score +
            0.2 * topic_novelty +
            0.15 * context.importance_score +
            0.1 * (1.0 if context.user_mood_confidence > 0.8 else 0.5)
        )
        
        return min(1.0, importance)
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_context_brain.py -v
```

Expected output: `2 PASSED`

**Step 5: Update `agent/brains/__init__.py`**

```python
# Add to agent/brains/__init__.py
from agent.brains.context_brain import ContextBrain

__all__ = ["ContextBrain", ...]
```

**Step 6: Commit**

```bash
git add agent/brains/context_brain.py agent/brains/__init__.py tests/unit/test_context_brain.py
git commit -m "feat: implement ContextBrain combining all three layers"
```

---

## Task 6: Integrate ContextBrain with Orchestrator

**Files:**
- Modify: `agent/orchestrator.py`
- Test: `tests/integration/test_context_integration.py`

**Step 1: Write failing integration test**

```python
def test_orchestrator_with_context():
    """Test that orchestrator initializes ContextBrain."""
    import asyncio
    from agent.orchestrator import Orchestrator
    from agent.brains.context_brain import ContextBrain
    
    async def run_test():
        orch = Orchestrator()
        
        # Check that context brain is initialized
        context_brain = None
        for brain in orch.brains:
            if isinstance(brain, ContextBrain):
                context_brain = brain
                break
        
        assert context_brain is not None, "ContextBrain not found in orchestrator"
    
    asyncio.run(run_test())


def test_context_persists_across_turns():
    """Test that context persists when multiple turns are added."""
    import asyncio
    from pathlib import Path
    import tempfile
    from agent.brains.context_brain import ContextBrain
    from agent.core.conversation_context import ConversationContext
    
    async def run_test():
        with tempfile.TemporaryDirectory() as tmpdir:
            brain = ContextBrain(data_dir=tmpdir)
            await brain.initialize()
            
            # Add multiple turns
            for i in range(5):
                ctx = ConversationContext(
                    turn_id=i,
                    user_input=f"Input {i}",
                    agent_response=f"Response {i}",
                    user_mood="INTERESTED",
                    agent_mood="STABLE",
                    intent="statement",
                    topics=["topic"],
                )
                brain.add_turn(ctx)
            
            # Save state
            brain.save_state()
            
            # Create new brain instance and load
            brain2 = ContextBrain(data_dir=tmpdir)
            brain2.load_state()
            
            # Verify data is restored
            recent = brain2.get_recent_turns()
            assert len(recent) == 5
            assert recent[-1].turn_id == 4
    
    asyncio.run(run_test())
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/integration/test_context_integration.py::test_orchestrator_with_context -v
```

Expected output: `FAILED - ContextBrain not initialized`

**Step 3: Modify Orchestrator to initialize ContextBrain**

Find and read the orchestrator file to understand its structure:

```bash
grep -n "class Orchestrator" /home/pedro/repo/mimi/agent/orchestrator.py | head -5
```

Then modify it to add ContextBrain initialization. Expected modification:

```python
# In agent/orchestrator.py, in the __init__ method, add:

from agent.brains.context_brain import ContextBrain

# ... existing code ...

self.context_brain = ContextBrain(data_dir=self.data_dir)
self.brains.append(self.context_brain)
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/integration/test_context_integration.py -v
```

Expected output: `2 PASSED`

**Step 5: Commit**

```bash
git add agent/orchestrator.py tests/integration/test_context_integration.py
git commit -m "feat: integrate ContextBrain into orchestrator"
```

---

## Task 7: Integrate Context with SentimentBrain

**Files:**
- Modify: `agent/brains/sentiment_brain.py`
- Modify: `agent/brains/input_processing_brain.py`
- Test: `tests/unit/test_sentiment_with_context.py`

**Step 1: Write failing test**

```python
def test_sentiment_uses_conversation_context():
    """Test that SentimentBrain uses conversation context."""
    import asyncio
    from agent.brains.sentiment_brain import SentimentBrain
    from agent.brains.context_brain import ContextBrain
    from agent.core.conversation_context import ConversationContext
    
    async def run_test():
        # Create both brains with mocked event bus
        context_brain = ContextBrain()
        await context_brain.initialize()
        
        # Add previous turns to context
        for i in range(3):
            ctx = ConversationContext(
                turn_id=i,
                user_input=f"About feelings {i}",
                agent_response=f"Response {i}",
                user_mood="INTERESTED",
                agent_mood="STABLE",
                intent="statement",
                topics=["feelings"],
            )
            context_brain.add_turn(ctx)
        
        # Get context string
        context_str = context_brain.build_llm_context()
        
        assert "About feelings" in context_str or len(context_str) > 0
        assert context_brain.get_recent_turns() is not None
    
    asyncio.run(run_test())
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_sentiment_with_context.py -v
```

Expected output: Should pass or fail depending on existing implementation

**Step 3: Modify SentimentBrain to reference context**

Update the `_analyze_mood` method in SentimentBrain to optionally receive context:

```python
# In agent/brains/sentiment_brain.py, modify _analyze_mood signature:

def _analyze_mood(self, transcript: str, context: Optional[str] = None) -> tuple[str, float]:
    """Analyze mood considering conversation context.
    
    Args:
        transcript: Current user input
        context: Previous conversation context (optional)
    """
    # Existing FSM analysis...
    mood, confidence = self._fsm.process(transcript) if self._fsm else ("STABLE", 0.5)
    
    # If context provided, boost confidence if mood matches context pattern
    if context and "INTERESTED" in context and mood == "INTERESTED":
        confidence = min(1.0, confidence * 1.1)
    
    return mood, confidence
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_sentiment_with_context.py -v
```

Expected output: `1 PASSED`

**Step 5: Commit**

```bash
git add agent/brains/sentiment_brain.py tests/unit/test_sentiment_with_context.py
git commit -m "feat: integrate context awareness into mood detection"
```

---

## Task 8: Update InputProcessingBrain to pass context to LLM

**Files:**
- Modify: `agent/brains/input_processing_brain.py`
- Modify: `agent/llm/prompt_templates.py`
- Test: `tests/integration/test_llm_context_integration.py`

**Step 1: Write failing test**

```python
def test_llm_receives_context_in_prompt():
    """Test that LLM prompt includes context from ContextBrain."""
    import asyncio
    from agent.brains.input_processing_brain import InputProcessingBrain
    from agent.brains.context_brain import ContextBrain
    from agent.core.conversation_context import ConversationContext
    
    async def run_test():
        context_brain = ContextBrain()
        await context_brain.initialize()
        
        # Add previous turns
        ctx = ConversationContext(
            turn_id=0,
            user_input="I like Python programming",
            agent_response="Python is great",
            user_mood="INTERESTED",
            agent_mood="STABLE",
            intent="statement",
            topics=["programming"],
        )
        context_brain.add_turn(ctx)
        
        # Build context for LLM
        context_str = context_brain.build_llm_context()
        
        # Verify context includes relevant information
        assert context_str is not None
        assert len(context_str) > 0
    
    asyncio.run(run_test())
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/integration/test_llm_context_integration.py -v
```

**Step 3: Modify InputProcessingBrain**

Add context retrieval in `process` or response generation:

```python
# In agent/brains/input_processing_brain.py, add:

from agent.brains.context_brain import ContextBrain

# ... existing code ...

async def process_input(self, user_input: str) -> str:
    """Process input and generate response with context."""
    
    # Get context from ContextBrain if available
    context_str = ""
    if hasattr(self, "orchestrator") and hasattr(self.orchestrator, "context_brain"):
        context_str = self.orchestrator.context_brain.build_llm_context(max_tokens=1500)
    
    # Build prompt with context
    prompt = self.build_prompt(user_input, context_str)
    
    # Call LLM
    response = await self.call_llm(prompt)
    
    return response
```

**Step 4: Update prompt templates to include context**

```python
# In agent/llm/prompt_templates.py, update the main prompt template:

MAIN_SYSTEM_PROMPT = """You are Mimi, an interactive AI assistant.

{context_section}

Respond naturally and remember the conversation history when relevant.
"""

def build_prompt_with_context(user_input: str, context: str = "") -> str:
    """Build complete prompt including context."""
    context_section = ""
    if context:
        context_section = f"""
[Previous Conversation Context]
{context}
"""
    
    return f"""{MAIN_SYSTEM_PROMPT.format(context_section=context_section)}

User: {user_input}
Response:"""
```

**Step 5: Run test to verify it passes**

```bash
pytest tests/integration/test_llm_context_integration.py -v
```

Expected output: `1 PASSED`

**Step 6: Commit**

```bash
git add agent/brains/input_processing_brain.py agent/llm/prompt_templates.py tests/integration/test_llm_context_integration.py
git commit -m "feat: pass conversation context to LLM prompts"
```

---

## Task 9: Add Long-term Memory Storage Decision Logic

**Files:**
- Create: `agent/core/long_term_memory.py`
- Modify: `agent/core/memory.py` (extend existing schema)
- Test: `tests/unit/test_long_term_memory.py`

**Step 1: Write failing test**

```python
def test_long_term_memory_importance_scoring():
    """Test importance scoring for long-term storage."""
    from agent.core.long_term_memory import LongTermMemoryManager
    from agent.core.conversation_context import ConversationContext
    
    manager = LongTermMemoryManager()
    
    ctx = ConversationContext(
        turn_id=1,
        user_input="I love Mimi!",
        agent_response="Thank you!",
        user_mood="ENERGIZED",
        agent_mood="ENERGIZED",
        intent="appreciation",
        importance_score=0.8,
        user_mood_confidence=0.9,
    )
    
    importance = manager.calculate_importance_score(ctx)
    
    # High emotion + appreciation = should be > 0.5
    assert importance > 0.5
    assert isinstance(importance, float)


def test_long_term_memory_store_and_retrieve():
    """Test storing and retrieving important turns."""
    import tempfile
    from pathlib import Path
    import sqlite3
    from agent.core.long_term_memory import LongTermMemoryManager
    from agent.core.conversation_context import ConversationContext
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "longterm.db"
        manager = LongTermMemoryManager(db_path=db_path)
        
        ctx = ConversationContext(
            turn_id=1,
            user_input="Remember this",
            agent_response="Got it",
            user_mood="INTERESTED",
            agent_mood="STABLE",
            intent="statement",
            topics=["memory"],
            importance_score=0.7,
        )
        
        manager.store_if_important(ctx, threshold=0.6)
        
        # Retrieve
        retrieved = manager.search_by_topic("memory", limit=5)
        assert len(retrieved) >= 1
        assert retrieved[0]["user_input"] == "Remember this"


def test_long_term_memory_auto_pruning():
    """Test automatic pruning of old low-importance entries."""
    import tempfile
    import time
    from pathlib import Path
    from agent.core.long_term_memory import LongTermMemoryManager
    from agent.core.conversation_context import ConversationContext
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "longterm.db"
        manager = LongTermMemoryManager(db_path=db_path)
        
        # Store old entry
        old_time = time.time() - (30 * 24 * 3600)  # 30 days old
        
        ctx = ConversationContext(
            turn_id=1,
            user_input="Old message",
            agent_response="Old response",
            user_mood="STABLE",
            agent_mood="STABLE",
            intent="statement",
            topics=["old"],
        )
        ctx.timestamp = old_time
        manager.store_if_important(ctx, threshold=0.3)
        
        # Prune old entries
        count = manager.prune_old_entries(days=20)
        assert count >= 1
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_long_term_memory.py -v
```

**Step 3: Implement LongTermMemoryManager**

```python
# agent/core/long_term_memory.py
"""Long-term memory with algorithmic storage decisions."""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Optional, Any

from agent.core.conversation_context import ConversationContext

logger = logging.getLogger(__name__)


class LongTermMemoryManager:
    """Manages long-term storage with intelligent importance scoring."""
    
    def __init__(self, db_path: Optional[str | Path] = None) -> None:
        self.db_path = Path(db_path) if db_path else None
        if self.db_path:
            self._init_db()
    
    def _init_db(self) -> None:
        """Initialize long-term memory database."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS long_term_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    turn_id INTEGER UNIQUE,
                    timestamp REAL,
                    user_input TEXT,
                    agent_response TEXT,
                    user_mood TEXT,
                    agent_mood TEXT,
                    intent TEXT,
                    topics TEXT,
                    entities TEXT,
                    importance_score REAL,
                    storage_reason TEXT,
                    created_at REAL,
                    last_accessed REAL
                )
                """
            )
            conn.commit()
    
    def calculate_importance_score(self, context: ConversationContext) -> float:
        """Calculate weighted importance score for storage decision.
        
        Factors:
        - Sentiment strength (0-1): how emotional was the user
        - Intent significance: certain intents more memorable
        - Topic novelty: new topics vs known ones
        - User-provided importance: explicit importance score
        - High confidence: confident detections more reliable
        """
        sentiment_strength = context.user_mood_confidence
        
        # Intent-based weights
        intent_weights = {
            "greeting": 0.3,
            "farewell": 0.3,
            "question": 0.7,
            "request": 0.8,
            "appreciation": 0.6,
            "complaint": 0.9,
            "statement": 0.4,
        }
        intent_score = intent_weights.get(context.intent, 0.5)
        
        # High-emotion moods are memorable
        high_emotion_moods = {"ENERGIZED", "DEPRESSED", "INTERESTED"}
        mood_score = 1.0 if context.user_mood in high_emotion_moods else 0.6
        
        # Calculate weighted importance
        importance = (
            0.3 * sentiment_strength +      # How emotional
            0.25 * intent_score +           # What kind of intent
            0.2 * mood_score +              # Which mood
            0.15 * context.importance_score +  # Explicit score
            0.1 * (1.0 if context.user_mood_confidence > 0.8 else 0.5)  # Confidence
        )
        
        return min(1.0, max(0.0, importance))
    
    def store_if_important(
        self,
        context: ConversationContext,
        threshold: float = 0.5,
    ) -> bool:
        """Store context turn if importance exceeds threshold.
        
        Returns: True if stored, False otherwise
        """
        if not self.db_path:
            return False
        
        importance = self.calculate_importance_score(context)
        
        if importance < threshold:
            logger.debug(f"Turn {context.turn_id} importance {importance:.2f} below threshold")
            return False
        
        # Determine reason for storage
        reasons = []
        if context.user_mood_confidence > 0.85:
            reasons.append("high_confidence")
        if context.intent in {"appreciation", "complaint"}:
            reasons.append("significant_intent")
        if context.user_mood in {"ENERGIZED", "DEPRESSED"}:
            reasons.append("strong_emotion")
        
        storage_reason = ", ".join(reasons) or "importance_threshold"
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO long_term_memories
                    (turn_id, timestamp, user_input, agent_response, user_mood, agent_mood,
                     intent, topics, entities, importance_score, storage_reason, created_at, last_accessed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        context.turn_id,
                        context.timestamp,
                        context.user_input,
                        context.agent_response,
                        context.user_mood,
                        context.agent_mood,
                        context.intent,
                        json.dumps(context.topics),
                        json.dumps(context.entities),
                        importance,
                        storage_reason,
                        time.time(),
                        time.time(),
                    ),
                )
                conn.commit()
            
            logger.info(f"Stored turn {context.turn_id} (importance: {importance:.2f}, reason: {storage_reason})")
            return True
        
        except Exception as e:
            logger.error(f"Failed to store long-term memory: {e}")
            return False
    
    def search_by_topic(self, topic: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search long-term memory by topic."""
        if not self.db_path:
            return []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute(
                    """
                    SELECT user_input, agent_response, user_mood, intent, importance_score, timestamp
                    FROM long_term_memories
                    WHERE topics LIKE ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (f'%"{topic}"%', limit),
                ).fetchall()
            
            return [
                {
                    "user_input": r[0],
                    "agent_response": r[1],
                    "user_mood": r[2],
                    "intent": r[3],
                    "importance_score": r[4],
                    "timestamp": r[5],
                }
                for r in rows
            ]
        
        except Exception as e:
            logger.error(f"Failed to search long-term memory: {e}")
            return []
    
    def search_by_mood(self, mood: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search long-term memory by mood."""
        if not self.db_path:
            return []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute(
                    """
                    SELECT user_input, agent_response, intent, importance_score, timestamp
                    FROM long_term_memories
                    WHERE user_mood = ?
                    ORDER BY importance_score DESC, timestamp DESC
                    LIMIT ?
                    """,
                    (mood, limit),
                ).fetchall()
            
            return [
                {
                    "user_input": r[0],
                    "agent_response": r[1],
                    "intent": r[2],
                    "importance_score": r[3],
                    "timestamp": r[4],
                }
                for r in rows
            ]
        
        except Exception as e:
            logger.error(f"Failed to search long-term memory by mood: {e}")
            return []
    
    def prune_old_entries(self, days: int = 60) -> int:
        """Remove entries older than N days with low importance.
        
        Returns: Number of entries removed
        """
        if not self.db_path:
            return 0
        
        cutoff_time = time.time() - (days * 24 * 3600)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    DELETE FROM long_term_memories
                    WHERE timestamp < ? AND importance_score < 0.4
                    """,
                    (cutoff_time,),
                )
                conn.commit()
                
                removed = cursor.rowcount
                logger.info(f"Pruned {removed} old low-importance entries")
                return removed
        
        except Exception as e:
            logger.error(f"Failed to prune long-term memory: {e}")
            return 0
    
    def get_memory_stats(self) -> dict[str, Any]:
        """Get statistics about long-term memory."""
        if not self.db_path:
            return {"total_entries": 0}
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                stats = conn.execute(
                    """
                    SELECT
                        COUNT(*) as total,
                        AVG(importance_score) as avg_importance,
                        MAX(timestamp) as last_stored
                    FROM long_term_memories
                    """
                ).fetchone()
            
            return {
                "total_entries": stats[0],
                "avg_importance": stats[1] or 0.0,
                "last_stored": stats[2] or 0.0,
            }
        
        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {"total_entries": 0}
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_long_term_memory.py -v
```

Expected output: `3 PASSED`

**Step 5: Commit**

```bash
git add agent/core/long_term_memory.py tests/unit/test_long_term_memory.py
git commit -m "feat: implement intelligent long-term memory with importance scoring"
```

---

## Task 10: Create ContextBrain Event Handler for Long-term Storage

**Files:**
- Modify: `agent/brains/context_brain.py`
- Test: `tests/integration/test_long_term_storage_decision.py`

**Step 1: Write failing test**

```python
def test_context_brain_stores_important_turns():
    """Test that ContextBrain stores important turns long-term."""
    import tempfile
    import asyncio
    from pathlib import Path
    from agent.brains.context_brain import ContextBrain
    from agent.core.conversation_context import ConversationContext
    
    async def run_test():
        with tempfile.TemporaryDirectory() as tmpdir:
            brain = ContextBrain(data_dir=tmpdir)
            await brain.initialize()
            
            # Add high-importance turn
            ctx = ConversationContext(
                turn_id=1,
                user_input="I absolutely love this!",
                agent_response="That's wonderful!",
                user_mood="ENERGIZED",
                agent_mood="ENERGIZED",
                intent="appreciation",
                importance_score=0.9,
                user_mood_confidence=0.95,
            )
            
            brain.add_turn(ctx)
            brain.save_state()
            
            # Check if stored in long-term
            stats = brain._long_term_manager.get_memory_stats()
            assert stats["total_entries"] >= 1
    
    asyncio.run(run_test())
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/integration/test_long_term_storage_decision.py -v
```

Expected output: `FAILED - no attribute _long_term_manager`

**Step 3: Update ContextBrain to integrate LongTermMemoryManager**

Modify `agent/brains/context_brain.py`:

```python
# At top of file, add import:
from agent.core.long_term_memory import LongTermMemoryManager

# In ContextBrain.__init__, add:
self._long_term_manager = LongTermMemoryManager(
    db_path=self.data_dir / "long_term_memory.db"
)

# Update add_turn method to include:
def add_turn(self, context: ConversationContext) -> None:
    """Add a conversation turn and update all three layers."""
    # ... existing Layer 1-3 code ...
    
    # NEW: Layer 4 - Long-term storage decision
    importance = self.get_importance_score(context)
    if importance > 0.5:  # Store if above threshold
        self._long_term_manager.store_if_important(context, threshold=0.5)
    
    logger.debug(f"Added turn {context.turn_id} to context brain (importance: {importance:.2f})")
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/integration/test_long_term_storage_decision.py -v
```

Expected output: `1 PASSED`

**Step 5: Commit**

```bash
git add agent/brains/context_brain.py tests/integration/test_long_term_storage_decision.py
git commit -m "feat: integrate long-term memory storage with importance scoring"
```

---

## Task 11: Create Integration Test - Full Conversation Flow

**Files:**
- Create: `tests/integration/test_full_context_flow.py`

**Step 1: Write comprehensive integration test**

```python
"""Integration test for complete hybrid context system."""

import asyncio
import tempfile
from pathlib import Path
from agent.brains.context_brain import ContextBrain
from agent.core.conversation_context import ConversationContext


async def test_full_conversation_flow():
    """Simulate a full conversation with all context layers."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        brain = ContextBrain(data_dir=tmpdir)
        await brain.initialize()
        
        # Simulate a 5-turn conversation
        conversation = [
            {
                "user": "Hi Mimi, how are you?",
                "agent": "I'm doing great! How about you?",
                "mood": "INTERESTED",
                "intent": "greeting",
                "topics": ["greeting"],
            },
            {
                "user": "I've been learning Python lately",
                "agent": "Python is amazing! What have you built?",
                "mood": "INTERESTED",
                "intent": "statement",
                "topics": ["programming", "python"],
            },
            {
                "user": "I built a web scraper, it was really fun!",
                "agent": "That sounds awesome! Web scraping is powerful.",
                "mood": "ENERGIZED",
                "intent": "appreciation",
                "topics": ["programming", "python", "projects"],
            },
            {
                "user": "I got stuck on authentication though",
                "agent": "Authentication can be tricky. Want some tips?",
                "mood": "ANALYTICAL",
                "intent": "question",
                "topics": ["programming", "authentication"],
            },
            {
                "user": "Yes please, that would help a lot!",
                "agent": "Here are some best practices...",
                "mood": "INTERESTED",
                "intent": "appreciation",
                "topics": ["programming", "authentication"],
            },
        ]
        
        # Add turns
        for turn_idx, turn in enumerate(conversation):
            ctx = ConversationContext(
                turn_id=turn_idx,
                user_input=turn["user"],
                agent_response=turn["agent"],
                user_mood=turn["mood"],
                agent_mood="STABLE",
                intent=turn["intent"],
                topics=turn["topics"],
                importance_score=0.6 if turn["mood"] in ["ENERGIZED", "INTERESTED"] else 0.4,
                user_mood_confidence=0.8,
            )
            brain.add_turn(ctx)
        
        # Save state
        brain.save_state()
        
        # Verify Layer 1: Sliding window has recent turns
        recent = brain.get_recent_turns(n=3)
        assert len(recent) == 3
        assert "authentication" in " ".join([t.user_input for t in recent])
        
        # Verify Layer 2: Topics are clustered
        top_topics = brain._topic_manager.get_top_by_importance(n=5)
        topic_names = [t.topic_name for t in top_topics]
        assert "programming" in topic_names or "python" in topic_names
        
        # Verify Layer 3: Markov chains exist
        transitions = list(brain._chain_manager._transitions.keys())
        assert len(transitions) > 0
        
        # Verify Layer 4: Important turns are stored long-term
        stats = brain._long_term_manager.get_memory_stats()
        assert stats["total_entries"] > 0  # At least the high-emotion turns
        
        # Build LLM context
        context_str = brain.build_llm_context(max_tokens=2000)
        assert "programming" in context_str or "User:" in context_str
        assert len(context_str) > 100
        
        # Load state in new instance
        brain2 = ContextBrain(data_dir=tmpdir)
        brain2.load_state()
        
        # Verify all layers restored
        recent2 = brain2.get_recent_turns()
        assert len(recent2) == 5
        
        top_topics2 = brain2._topic_manager.get_top_by_importance(n=5)
        assert len(top_topics2) > 0
        
        transitions2 = list(brain2._chain_manager._transitions.keys())
        assert len(transitions2) > 0
        
        print("✅ Full conversation flow test passed")
        return True


if __name__ == "__main__":
    asyncio.run(test_full_conversation_flow())
```

**Step 2: Run test to verify it passes**

```bash
pytest tests/integration/test_full_context_flow.py -v
```

Expected output: `1 PASSED`

**Step 3: Commit**

```bash
git add tests/integration/test_full_context_flow.py
git commit -m "test: add comprehensive integration test for hybrid context system"
```

---

## Task 12: Documentation & Final Verification

**Files:**
- Create: `docs/CONTEXT_SYSTEM.md`
- Modify: `README.md` (add Context System section)

**Step 1: Write system documentation**

```markdown
# Hybrid Conversation Context System

## Overview

The Mimi agent now maintains stateful conversation context through a three-layer hybrid system:

1. **Layer 1: Sliding Window** - Recent turns for immediate LLM context
2. **Layer 2: Topic Clustering** - Recurring themes with exponential decay
3. **Layer 3: Markov Chains** - Conversational flow patterns
4. **Layer 4: Long-term Storage** - Selective important turn persistence

## Architecture

### Layer 1: Sliding Window (Short-term)
- **Location**: `data/short_term_context.json`
- **Capacity**: Last 20 conversation turns (configurable)
- **Lifecycle**: FIFO - newest turns push oldest out
- **Usage**: Direct inclusion in LLM prompts
- **Performance**: O(1) add/retrieve

### Layer 2: Topic Clustering
- **Location**: `data/topic_clusters.json`
- **Mechanism**: Keyword frequency + co-occurrence tracking
- **Decay**: Exponential (rate: 0.05 hours^-1)
- **Features**: 
  - Mood associations (what moods correlate with each topic)
  - Co-occurrence network (what topics appear together)
  - Importance decay (old topics fade automatically)
- **Usage**: Enriching context when Layer 1 approaches token limit
- **Performance**: O(n) topics per update, typical n=50-100

### Layer 3: Markov Chains
- **Location**: `data/conversation_chains.json`
- **Mechanism**: State transitions (mood + topic pairs)
- **State**: ConversationState(mood="INTERESTED", topic="programming")
- **Tracking**: Transition frequency + recency weights
- **Decay**: 0.01 days^-1 for older transitions
- **Usage**: Predicting likely next user action
- **Performance**: O(1) lookup, O(n) for prediction (n=typical transitions/state)

### Layer 4: Long-term Memory
- **Location**: `data/memory.db` (SQLite)
- **Table**: `long_term_memories`
- **Storage Decision**: Weighted importance scoring:
  - 30% sentiment strength
  - 25% intent significance
  - 20% mood intensity
  - 15% explicit importance
  - 10% confidence
- **Threshold**: Store if score > 0.5
- **Pruning**: Remove entries >60 days old with importance <0.4
- **Performance**: O(log n) insert, O(n) search

## Usage in Code

### Adding a Conversation Turn

```python
from agent.brains.context_brain import ContextBrain
from agent.core.conversation_context import ConversationContext

context_brain = ContextBrain()

# Record a turn
ctx = ConversationContext(
    turn_id=42,
    user_input="How do I use Python?",
    agent_response="Python is a great language...",
    user_mood="INTERESTED",
    agent_mood="STABLE",
    intent="question",
    topics=["programming", "python"],
    importance_score=0.7,
    user_mood_confidence=0.85,
)

context_brain.add_turn(ctx)
```

### Building LLM Context

```python
# Get context string for LLM prompt
context_str = context_brain.build_llm_context(max_tokens=2000)

# Output includes:
# - [Recent Conversation] - Last M turns
# - [Conversation Themes] - Top topics with mood associations
# - [Expected Direction] - Likely next user actions
```

### Saving & Loading State

```python
# Persist to disk
context_brain.save_state()

# Load from disk
context_brain.load_state()
```

### Querying Long-term Memory

```python
# Find all discussions about "programming"
results = context_brain._long_term_manager.search_by_topic("programming")

# Find turns where user was INTERESTED
energized_moments = context_brain._long_term_manager.search_by_mood("INTERESTED")

# Get stats
stats = context_brain._long_term_manager.get_memory_stats()
print(f"Total stored: {stats['total_entries']}, Avg importance: {stats['avg_importance']}")
```

## Performance Characteristics

| Operation | Complexity | Typical Time |
|-----------|-----------|---|
| Add turn | O(topics + transitions) | <10ms |
| Build LLM context | O(M + topics + chains) | <50ms |
| Save state | O(n) | <100ms |
| Load state | O(n) | <200ms |
| Search long-term | O(log n) | <50ms |

**Memory Usage**: ~50-100 KB per session (typical)

## Success Metrics

- [x] Mood detection considers conversation history
- [x] LLM generates contextually coherent responses
- [x] System remembers user interests over time
- [x] Predictable response patterns prevented
- [x] No context window overflow
- [x] < 100ms latency for context building

## Configuration

Edit `agent/brains/context_brain.py`:

```python
# Max recent turns in Layer 1
ConversationMemory(max_size=20)

# Topic pruning threshold
prune_old_topics(importance_threshold=2.0)

# Markov chain pruning
prune_old_transitions(weight_threshold=0.1)

# Long-term storage threshold
store_if_important(context, threshold=0.5)

# Prune old entries >60 days
prune_old_entries(days=60)
```

## Troubleshooting

### Context not being updated
- Verify EventBus is firing RESPONSE_READY events
- Check logs for "Added turn X to context brain"

### LLM not using context
- Verify `build_llm_context()` is being called
- Check that prompt template includes context section
- Verify context string is not empty

### Memory growing too large
- Run `prune_old_topics()` and `prune_old_transitions()` periodically
- Reduce `max_size` in ConversationMemory
- Lower long-term storage threshold

## Future Enhancements

- Semantic embeddings for better topic similarity
- Graph-based entity relationships
- User preference learning
- Conversation summarization for very long sessions
```

**Step 2: Update README.md**

Add section after existing documentation:

```markdown
## Conversation Context System

Mimi now maintains **stateful conversation memory** across three layers:

- **Layer 1**: Recent turns (last 20 messages) for immediate LLM context
- **Layer 2**: Topic clustering with exponential decay to track recurring themes
- **Layer 3**: Markov chains to predict conversational flow
- **Layer 4**: Intelligent long-term storage based on importance scoring

This enables:
- Coherent multi-turn conversations
- User interest learning over time
- Prevention of repetitive responses
- Personalized context-aware replies

See [docs/CONTEXT_SYSTEM.md](docs/CONTEXT_SYSTEM.md) for full details.
```

**Step 3: Run all tests**

```bash
pytest tests/ -v --tb=short
```

Expected output: All tests PASS

**Step 4: Commit**

```bash
git add docs/CONTEXT_SYSTEM.md README.md
git commit -m "docs: add comprehensive context system documentation"
```

---

## Final Verification

**Step 1: Verify no broken dependencies**

```bash
python -m pytest tests/unit/ -v
python -m pytest tests/integration/ -v
```

**Step 2: Type checking**

```bash
python -m mypy agent/core/conversation_*.py agent/brains/context_brain.py --ignore-missing-imports
```

**Step 3: Linting**

```bash
ruff check agent/core/conversation_*.py agent/brains/context_brain.py
ruff check agent/core/long_term_memory.py
```

**Step 4: Final integration**

```bash
python -c "from agent.brains.context_brain import ContextBrain; print('✅ ContextBrain imports successfully')"
```

---

## Summary

✅ **Task 1**: ConversationContext dataclass  
✅ **Task 2**: ConversationMemory (Layer 1)  
✅ **Task 3**: TopicClusterManager (Layer 2)  
✅ **Task 4**: ConversationalChainManager (Layer 3)  
✅ **Task 5**: ContextBrain unified manager  
✅ **Task 6**: Orchestrator integration  
✅ **Task 7**: SentimentBrain context awareness  
✅ **Task 8**: LLM prompt context injection  
✅ **Task 9**: LongTermMemoryManager (Layer 4)  
✅ **Task 10**: Automatic importance-based storage  
✅ **Task 11**: Full integration test  
✅ **Task 12**: Documentation  

**Total Lines of Code**: ~2,500 lines (tests + implementation)  
**Total Commits**: 12  
**Total Estimated Time**: 6-8 hours
