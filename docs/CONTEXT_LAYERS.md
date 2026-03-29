## Mimi's 4-Layer Hybrid Conversation Context System

Mimi uses an intelligent 4-layer context architecture to maintain stateful understanding of conversations while optimizing for token efficiency and response quality.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    LLM Reasoning Brain                  │
│              (Receives unified context prompt)           │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│              ContextBrain (Unified Manager)              │
│  Combines all 4 layers into optimized LLM context       │
└─┬──────────┬───────────────┬──────────────┬─────────────┘
  │          │               │              │
  ▼          ▼               ▼              ▼
┌────────┐ ┌────────┐ ┌────────────┐ ┌──────────────┐
│ Layer1 │ │ Layer2 │ │  Layer3    │ │   Layer4     │
│Sliding │ │ Topic  │ │  Markov    │ │ Long-term    │
│Window  │ │Cluster │ │  Chains    │ │  Memory      │
└────────┘ └────────┘ └────────────┘ └──────────────┘
```

### Layer 1: Sliding Window (Recent Turns)

**Purpose**: Provide immediate conversation context within LLM token limits.

**How it works**:
- Stores the last 20 conversation turns (configurable)
- Each turn contains: user_input, agent_response, moods, intent, topics
- FIFO buffer - oldest turns are automatically discarded when limit reached
- Persisted to `short_term_context.json`

**Benefits**:
- Constant memory overhead (fixed 20 turns)
- Always includes the most recent context
- Fast access (list-based)
- Prevents hallucination by grounding in recent history

**When used**:
- Every LLM prompt includes Layer 1 as `[Recent Conversation]` section
- Provides direct conversation history

**Files**:
- Implementation: `agent/core/conversation_memory.py` (ConversationMemory)
- Test: `tests/unit/test_conversation_memory.py`

---

### Layer 2: Topic Clustering (Recurring Themes)

**Purpose**: Track recurring conversation topics and user interests over time.

**How it works**:
- Automatically extracts topics from each turn (e.g., "stress", "work", "career")
- Groups them into clusters based on co-occurrence patterns
- Applies exponential decay to old topics (fresher topics weighted higher)
- Associates moods with topics (e.g., "work" → ANXIOUS 0.8, ENERGIZED 0.2)
- Persisted to `topic_clusters.json`

**Importance Calculation** (per cluster):
```
importance = frequency * e^(-DECAY_RATE * hours_since_seen)
```
- Cluster importance decays over time
- Frequent topics maintain high importance
- New topics get boost on first occurrence

**Benefits**:
- Captures user interests and concerns
- Mood associations help predict emotional context
- Identifies topic trends (what the user talks about most)
- Enables proactive support (e.g., "I know work stress has been on your mind...")

**When used**:
- LLM prompt includes Layer 2 as `[Conversation Themes]` (if space available)
- Provides topic summary and co-occurrence patterns
- Used in importance scoring for Layer 4

**Files**:
- Implementation: `agent/core/topic_clustering.py` (TopicClusterManager)
- Test: `tests/unit/test_topic_clustering.py`

---

### Layer 3: Conversational Flow (Markov Chains)

**Purpose**: Predict conversation direction and maintain coherent dialogue flow.

**How it works**:
- Tracks state transitions: (current_mood, current_topic) → (next_mood, next_topic)
- Stores transition probabilities (weighted by frequency)
- Models conversation as Markov chain (memoryless state transitions)
- Persisted to `conversation_chains.json`

**State Definition**:
```python
ConversationState(
    mood="ANXIOUS" | "ENERGIZED" | "STABLE" | ...,
    topic="work" | "relationships" | ...
)
```

**Transition Learning**:
- After each turn: record transition from previous state to current state
- Weight = 1.0 on first occurrence, incremented on repeat
- Normalization applied (weights become probabilities)

**Benefits**:
- Predicts likely conversation direction
- Helps avoid abrupt topic/mood changes
- Enables smoother transitions in agent responses
- Captures conversation patterns (e.g., "worried about work" → "feeling better")

**When used**:
- LLM prompt includes Layer 3 as `[Expected Direction]` (if space available)
- Lists 3 most likely next states with probabilities
- Influences response generation strategy

**Files**:
- Implementation: `agent/core/conversational_chains.py` (ConversationalChainManager)
- Test: `tests/unit/test_conversational_chains.py`

---

### Layer 4: Long-Term Memory (Important Moments)

**Purpose**: Preserve significant moments for long-term personalization and recall.

**How it works**:
- SQLite database (`long_term_memory.db`) stores selective conversation history
- Only stores turns that exceed importance threshold (default 0.5)
- Importance evaluated using weighted formula
- Auto-prunes entries >60 days old with low importance (<0.4)
- Searchable by topic, mood, or intent

**Importance Scoring Algorithm**:
```
importance = 
  0.30 * sentiment_strength +
  0.25 * intent_score +
  0.20 * topic_novelty +
  0.15 * context_importance +
  0.10 * high_confidence_flag
```

**Importance Factors**:

| Factor | Weight | Values |
|--------|--------|--------|
| Sentiment Strength | 30% | user_mood_confidence (0-1) |
| Intent Score | 25% | complaint=0.9, request=0.8, question=0.7, etc. |
| Topic Novelty | 20% | 1.0 if new topic, 0.0 if repeated |
| Context Importance | 15% | Explicit importance_score from turn |
| High Confidence | 10% | 1.0 if confidence >0.8, else 0.5 |

**Example Stored Turns**:
- ✓ "I got promoted!" (high sentiment + celebration intent)
- ✓ "I'm really worried about the deadline" (high confidence + complaint)
- ✓ "How do I deal with impostor syndrome?" (high novelty + question)
- ✗ "How's the weather?" (low importance + small talk)
- ✗ "What time is it?" (low importance + information)

**Storage Metadata**:
```
{
  "turn_id": 42,
  "timestamp": 1704067200,
  "user_input": "...",
  "agent_response": "...",
  "user_mood": "ENERGIZED",
  "agent_mood": "HAPPY",
  "intent": "celebration",
  "topics": ["career", "achievement"],
  "importance_score": 0.92,
  "storage_reason": "high_confidence, significant_intent"
}
```

**Pruning Strategy**:
- Runs automatically every background cycle (in ContextBrain.process())
- Threshold: days_threshold=60, importance_threshold=0.4
- Preserves recent important moments
- Cleans old low-value data

**Query Operations**:
- `search_by_topic(topic, limit=10)` - Find related conversations
- `search_by_mood(mood, limit=10)` - Find turns with specific mood
- `get_count()` / `get_count(days=7)` - Memory statistics
- `get_memory_stats()` - Full database statistics

**Benefits**:
- Personalization over months/years
- Recall important user context (promotions, challenges, preferences)
- Long-term emotional tracking
- Privacy-conscious (selective storage, pruning)

**Files**:
- Implementation: `agent/core/long_term_memory.py` (LongTermMemoryManager)
- Test: `tests/unit/test_long_term_memory.py`

---

## Integration: ContextBrain

**File**: `agent/brains/context_brain.py` (ContextBrain class)

ContextBrain is the unified manager that coordinates all 4 layers. Key methods:

### `add_turn(context: ConversationContext) → None`

Called when a new conversation turn is ready. Updates all layers:
1. **Layer 1**: Add to sliding window
2. **Layer 2**: Update topic clusters with new topics
3. **Layer 3**: Record state transition (if history exists)
4. **Layer 4**: Evaluate importance and store if needed

### `build_llm_context(max_tokens: int = 2000) → str`

Constructs the LLM context prompt combining all layers intelligently:
1. Start with Layer 1 (recent turns) - highest priority
2. Add Layer 2 (topics) if space available (70% of max_tokens)
3. Add Layer 3 (predicted direction) if space available (85% of max_tokens)
4. Layer 4 data informs importance scoring but isn't directly embedded (too large)

**Output format**:
```
[Recent Conversation]
User: <recent turn 1>
You: <response 1>

[Conversation Themes]
Topics: stress, work (frequency: 12x, mood: ANXIOUS)
Co-occurring with: deadline, performance

[Expected Direction]
Based on patterns, user might:
- Continue discussing work (67% likely)
- Express concern about deadline (45% likely)
- Shift to feelings of capability (38% likely)
```

### `get_memory_stats() → dict`

Returns statistics for all 4 layers:
```python
{
    "layer1_short_term": {
        "count": 15,      # current turns
        "max_size": 20    # capacity
    },
    "layer2_topics": {
        "clusters": 8,     # unique topics
        "total_occurrences": 34  # total mentions
    },
    "layer3_chains": {
        "transitions": 7   # unique state transitions
    },
    "layer4_long_term": {
        "total_memories": 142,     # all-time important moments
        "recent_memories": 12      # from last 7 days
    }
}
```

### `search_long_term_by_topic(topic: str, limit: int = 10) → list[dict]`

Query long-term memory for specific topic (Layer 4 query interface).

### `save_state() / load_state() → None`

Persist/restore all 4 layers to disk:
- Layer 1: `short_term_context.json` (JSON)
- Layer 2: `topic_clusters.json` (JSON)
- Layer 3: `conversation_chains.json` (JSON)
- Layer 4: `long_term_memory.db` (SQLite)

---

## Event Integration

ContextBrain subscribes to EventBus events:

- **RESPONSE_READY**: When agent generates a response, ContextBrain receives the event payload and extracts:
  - user_input, response (agent_response)
  - user_mood, agent_mood
  - intent, topics, entities
  - user_mood_confidence
  - importance_score (from SentimentBrain)

---

## Data Flow Example

**Scenario**: User mentions stress about a work deadline

**Turn 1 Processing**:
```
User: "I'm really worried about the deadline tomorrow"
  ↓
SentimentBrain: intent=complaint, user_mood=ANXIOUS, confidence=0.92
  ↓
InputBrain: topics=["work", "deadline"], entities={"time": "tomorrow"}
  ↓
RESPONSE_READY event → ContextBrain.add_turn()
  │
  ├─ Layer 1: Store (user_input, response, moods, intent, topics)
  ├─ Layer 2: Add/update topics: "work"(freq++, mood→ANXIOUS), "deadline"(new)
  ├─ Layer 3: Transition STABLE→ANXIOUS (work) recorded
  └─ Layer 4: Evaluate importance = 0.92 (high) → STORE
       Storage reason: high_confidence, significant_intent, strong_emotion
  
ReasoningBrain receives LLM context:
  [Recent Conversation]
  User: I'm really worried about the deadline tomorrow
  You: That sounds challenging. Tell me more.
  
  [Conversation Themes]
  Recent topics: deadline (frequency: 1x), work (frequency: 7x)
  Moods associated: work→ANXIOUS(0.89), ENERGIZED(0.11)
  
  [Expected Direction]
  Based on patterns, user might:
  - Continue discussing work (78% likely)
  - Express need for help (52% likely)
```

---

## Performance Characteristics

| Layer | Memory | Lookup | Storage | Notes |
|-------|--------|--------|---------|-------|
| 1 | ~50 KB | O(1) | JSON (10 KB) | Fixed 20 turns |
| 2 | ~20 KB | O(1) | JSON (5 KB) | ~8 clusters typical |
| 3 | ~10 KB | O(1) | JSON (2 KB) | ~7 transitions typical |
| 4 | Unbounded | O(log N) | SQLite (grows) | Only important turns |
| **Total** | **~100 KB + DB** | **All O(1-log N)** | **~20 KB + DB** | **Highly efficient** |

### Token Usage

**LLM context (typical)**:
- Layer 1: 400-600 tokens (10 recent turns)
- Layer 2: 100-200 tokens (topic summary)
- Layer 3: 50-100 tokens (predicted direction)
- **Total**: ~600-900 tokens (~3-5% of typical context window)

---

## Testing

### Unit Tests
- `tests/unit/test_conversation_memory.py` - Layer 1 sliding window
- `tests/unit/test_topic_clustering.py` - Layer 2 topic clustering
- `tests/unit/test_conversational_chains.py` - Layer 3 Markov chains
- `tests/unit/test_long_term_memory.py` - Layer 4 long-term storage
- `tests/unit/test_context_brain.py` - ContextBrain integration

### Integration Tests
- `tests/integration/test_context_integration.py` - Orchestrator + ContextBrain
- `tests/integration/test_llm_context_integration.py` - LLM context prompt building
- `tests/integration/test_full_context_layers.py` - Complete 4-layer flow:
  - Full flow: add turns → evaluate → store → retrieve → combine
  - Layer 1 sliding window behavior
  - Layer 2 topic clustering with mood decay
  - Layer 3 conversation state transitions
  - Layer 4 importance filtering
  - Persistence across sessions
  - Background pruning

**Test Coverage**: 17 tests, 100% passing

---

## Configuration

### Adjustable Parameters

In `agent/brains/context_brain.py`:

```python
# Layer 1
ConversationMemory(max_size=20)  # Adjust recent turn buffer

# Layer 2
TopicClusterManager.DECAY_RATE = 0.05  # Exponential decay rate (lower = slower decay)

# Layer 3
ConversationalChainManager.MIN_WEIGHT_THRESHOLD = 0.1  # Minimum transition weight

# Layer 4
LongTermMemoryManager.IMPORTANCE_THRESHOLD = 0.5  # Storage threshold
LongTermMemoryManager.PRUNE_DAYS = 60  # Age threshold for pruning
LongTermMemoryManager.PRUNE_IMPORTANCE = 0.4  # Importance threshold for pruning
```

---

## Future Enhancements

1. **Semantic Embeddings** - Use vector embeddings to find semantically similar past conversations
2. **User Profiles** - Build long-term user personality models from Layer 4 data
3. **Emotion Trajectories** - Track emotional arcs (e.g., depression recovery, celebration)
4. **Relationship Memory** - Link related topics (e.g., "work stress" ↔ "sleep issues")
5. **Adaptive Thresholds** - Adjust importance thresholds based on user preferences
6. **Multi-Session Continuity** - Resume conversations across days/weeks with full context
7. **Privacy Controls** - User-configurable Layer 4 retention policies
8. **Knowledge Integration** - Connect Layer 4 with external knowledge base

---

## Troubleshooting

**Q: LLM context too long?**
- A: Reduce Layer 1 max_size or Layer 2/3 token allocation in build_llm_context()

**Q: Too much being stored to Layer 4?**
- A: Increase IMPORTANCE_THRESHOLD to be more selective

**Q: Old memories not being deleted?**
- A: Check prune_old_memories() is called (should auto-run in process())

**Q: Topic clustering not working?**
- A: Ensure topics are being extracted in InputBrain and passed to ContextBrain

**Q: Memory database growing too large?**
- A: Run manual pruning or reduce retention period (PRUNE_DAYS)

---

## API Reference

See `agent/brains/context_brain.py` for complete ContextBrain API.
See `agent/core/long_term_memory.py` for LongTermMemoryManager query interface.
