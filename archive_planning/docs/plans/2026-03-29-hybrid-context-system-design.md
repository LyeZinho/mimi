# Hybrid Conversation Context System - Algorithm Design

## Problem Statement

Current system is stateless: each message analyzed independently without conversation history. Goal: implement stateful context that remembers conversation flow while staying within LLM context window limits.

## Solution: Hybrid Algorithm (Three-Layer Fusion)

### Layer 1: Sliding Window (Short-term Memory)
**Purpose:** Direct context for immediate LLM prompts  
**Storage:** File-based JSON (short_term_context.json)  
**Capacity:** Last M messages (configurable, ~15-20 turns)  
**Lifecycle:** FIFO deque - newest turns push oldest out  
**Decay:** None (uniform recency)

**Example structure:**
```json
{
  "current_turn": 42,
  "turns": [
    {
      "turn_id": 38,
      "timestamp": 1711788000.123,
      "user_input": "Como você se sente hoje?",
      "agent_response": "Meu dia tá como um loop infinito...",
      "user_mood": "INTERESTED",
      "user_mood_confidence": 0.78,
      "agent_mood": "ANALYTICAL",
      "intent": "question",
      "topics": ["feelings", "day", "state"],
      "entities": {"temporal": "today"},
      "importance_score": 0.6
    }
  ]
}
```

### Layer 2: Semantic Clustering (Pattern Recognition)
**Purpose:** Identify recurring topics/themes without storing every message  
**Algorithm:** Keyword frequency + co-occurrence analysis  
**Storage:** SQLite table `topic_clusters`  
**Lifecycle:** Persistent, updated incrementally with exponential decay

**What we track:**
- Topic: keyword (e.g., "feelings", "work", "technical")
- Frequency: how often mentioned
- Co-occurrences: what other topics appear together
- Last_seen: timestamp of last mention
- Mood_association: which moods correlate with this topic
- Importance_decay: `frequency * e^(-0.05 * hours_since_last_seen)`

**Example query result:**
```
Topic: "feelings"
  Frequency: 12
  Co-occurrences: ["emotions", "state", "day"] (4, 3, 2)
  Last_seen: 2 hours ago
  Mood_association: {INTERESTED: 0.8, ANALYTICAL: 0.6, DEPRESSED: 0.4}
  Decayed_importance: 0.78
```

**Why this works:**
- ✅ Captures recurring themes without storing full messages
- ✅ Identifies what matters to the user (high co-occurrence = user cares)
- ✅ Mood associations help generate contextually appropriate responses
- ❌ Loses nuance of individual messages (mitigated by Layer 1)

### Layer 3: Markov Chain Fragments (Conversational Patterns)
**Purpose:** Remember HOW conversations flow, not just WHAT topics exist  
**Algorithm:** N-gram chains (bigrams + trigrams) weighted by recency  
**Storage:** SQLite table `conversational_chains`  
**Lifecycle:** Persistent, pruned by importance

**What we store:**
- State: current conversation "state" (topic + mood combination)
- Transitions: list of next possible states (with frequency)
- Example: `(ANALYTICAL, "technical", "questions") -> (ENERGIZED, "technical", "answers")` = 5 times

**Example extraction:**
```
Turn 10: "Como usar Python?" (mood: ANALYTICAL, topic: "technical")
Turn 11: Agent responds about Python (mood: ANALYTICAL, topic: "technical")
Turn 12: User asks follow-up (mood: INTERESTED, topic: "technical")

Extract chains:
  (ANALYTICAL + technical) -> (ANALYTICAL + technical) [weight: 1.0]
  (ANALYTICAL + technical) -> (INTERESTED + technical) [weight: 0.7]
```

**Why this works:**
- ✅ Predicts likely next turns (what user will ask next)
- ✅ Prevents repeating same responses in similar contexts
- ✅ Very compact storage (just state transitions, not full text)
- ❌ Needs many examples to be accurate (mitigated by high-frequency topics)

---

## Unified Algorithm: Context Selection for LLM

When building LLM prompt, use this selection logic:

```
1. START with Layer 1: Add last M messages from sliding window
   - Current turn + recent history directly in prompt
   
2. LAYER 1 OVERFLOW CHECK: If approaching context limit:
   a. Remove oldest messages from window
   b. Extract SUMMARY of removed messages using Layer 2 topic data
   c. If still over-budget, go to step 3
   
3. LAYER 2 ENRICHMENT: Add topic context
   - Most important recurring topics (top 5 by decayed_importance)
   - Format: "In this conversation, you've discussed [topics] repeatedly"
   - Include mood associations: "User is often INTERESTED when discussing [topic]"
   
4. LAYER 3 PREDICTION: Use Markov chains to anticipate next turn
   - Current conversation state: (current_mood, main_topic)
   - Likely next user action from transition probabilities
   - Format: "User typically asks about X after Y. Be prepared."
   
5. FINAL PROMPT TEMPLATE:
   {system_prompt}
   
   [CONVERSATION HISTORY - Last M turns]
   {sliding_window_history}
   
   [RECURRING THEMES]
   Key topics: {topic_cluster_summary}
   You are usually {mood_from_chains} when discussing these.
   
   [PREDICTIVE HINT]
   User might follow up with: {next_likely_state}
   
   User: {current_input}
```

---

## Persistence & Decision Logic

### When to Store in Long-term (SQLite)?

Use weighted scoring:
```
importance_score = 
  0.3 * sentiment_strength +           # High emotion = memorable
  0.25 * intent_significance +         # Certain intents more important
  0.2 * topic_novelty +                # New topics > repeated ones
  0.15 * user_explicit_importance +    # User says "remember this"
  0.1 * temporal_significance           # First/last turns of session
```

**Store if:** `importance_score > 0.5`

**What gets stored:**
- Full turn record (user input, agent response, mood, intent, topics)
- Extracted topics + entities
- Importance score
- Relationships to existing topic clusters

### Decay & Pruning

**For topic clusters:**
```
every_hour:
  for each topic:
    decay = e^(-0.05 * hours_since_last_seen)
    if decay * frequency < 2.0:
      mark_for_pruning()
```

**For Markov chains:**
```
quarterly_pruning:
  for each chain transition:
    weight *= 0.8  # Gradual decay of old patterns
    if weight < 0.1:
      delete()
```

---

## Handling Edge Cases

### Context Window Overflow
1. Prioritize Layer 1 (recent turns) - drop oldest
2. Compress to topic summary + mood patterns
3. Maintain Markov chain hints separately
4. Never drop current turn or context in last 2 turns

### Mood Transitions
- Track transitions in Markov chain
- Detect abrupt shifts (depression spike = user unhappy with response)
- Adjust next response based on transition probability

### Topic Switching
- When new topic emerges (not in clusters):
  - Initialize with importance = current sentiment strength
  - Track co-occurrence with existing topics
  - If co-occurrence high: merge clusters (related topics)

### Conversation Restart
- Keep all long-term data
- Reset Layer 1 (new session = fresh sliding window)
- Decay Layer 2 & 3 by 10% when new session starts
- Extract summary of previous session as "context seed"

---

## Data Structures (Exact Schema)

### File: `data/short_term_context.json`
```python
{
  "current_turn": int,
  "max_size": int,
  "turns": [
    {
      "turn_id": int,
      "timestamp": float,
      "user_input": str,
      "agent_response": str,
      "user_mood": str,
      "user_mood_confidence": float,
      "agent_mood": str,
      "intent": str,
      "topics": list[str],
      "entities": dict[str, str],
      "importance_score": float,
    }
  ]
}
```

### SQLite: `topic_clusters` table
```sql
CREATE TABLE topic_clusters (
  id INTEGER PRIMARY KEY,
  topic_name TEXT UNIQUE,
  frequency INTEGER,
  last_seen REAL,
  importance_decay REAL,
  mood_association TEXT,  -- JSON: {MOOD: score}
  co_occurrences TEXT,    -- JSON: {topic: count}
  created_at REAL,
  updated_at REAL
);
```

### SQLite: `conversational_chains` table
```sql
CREATE TABLE conversational_chains (
  id INTEGER PRIMARY KEY,
  from_state TEXT,        -- JSON: {mood, topic}
  to_state TEXT,          -- JSON: {mood, topic}
  transition_count INTEGER,
  transition_weight REAL,
  last_seen REAL,
  created_at REAL,
  updated_at REAL
);
```

### SQLite: `turns_history` table (extension of existing `memories`)
```sql
CREATE TABLE turns_history (
  id INTEGER PRIMARY KEY,
  turn_id INTEGER UNIQUE,
  timestamp REAL,
  user_input TEXT,
  agent_response TEXT,
  user_mood TEXT,
  agent_mood TEXT,
  intent TEXT,
  topics TEXT,          -- JSON list
  entities TEXT,        -- JSON dict
  importance_score REAL,
  stored_reason TEXT    -- "high_emotion", "explicit_memory", etc
);
```

---

## Performance Considerations

| Operation | Cost | Mitigated By |
|-----------|------|--------------|
| Layer 1 (sliding window) | O(1) read, O(1) write | Fixed size deque |
| Layer 2 (topic updates) | O(topics) per turn | Pruning, limited clusters |
| Layer 3 (chain updates) | O(1) per transition | Fixed-size transition table |
| LLM context building | O(M + topics + chains) | Pre-computed summaries |
| Database persistence | O(log n) per write | Deferred writes, batching |

**Memory usage:** ~50-100 KB per conversation (typical)

---

## Success Criteria

- [x] Conversation history influences mood detection (Layer 1 context)
- [x] LLM generates contextually coherent responses (Layers 1+2 in prompt)
- [x] System remembers user interests over time (Layer 2 clustering)
- [x] Predictable response patterns (Layer 3 chains)
- [x] No context window overflow
- [x] < 100ms latency for context building
- [x] < 500 KB disk usage per conversation
