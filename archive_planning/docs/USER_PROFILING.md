# User Profiling Brain - Architecture & Implementation

## Overview

The **User Profiling Brain** is a dedicated cognitive module that analyzes long-term conversational memory (Layer 4) to build comprehensive user personality profiles. These profiles enable personalized LLM responses, adaptive conversation flow, and informed support strategies.

The brain operates as an autonomous background process, periodically analyzing accumulated conversation data to maintain an accurate, confidence-weighted profile of the user's personality, interests, communication style, and support needs.

## Motivation

User profiling unlocks several critical capabilities:

- **Personalized Responses**: LLM can adapt tone, formality, depth, and emphasis based on user communication style
- **Proactive Support**: Detect crisis indicators, mood degradation patterns, and communication shifts
- **Adaptive Context**: Adjust Layer 1 window size and Layer 2 planning based on user communication patterns
- **Foundation Layer**: Enables trajectory analysis, semantic search improvements, and future mood-forecasting

## Architecture

### Components

```
UserProfileBrain (agent/brains/user_profile_brain.py)
    └─ UserProfileManager (agent/core/user_profile_manager.py)
        └─ LongTermMemoryManager (reads Layer 4 SQLite)
        └─ UserProfile Dataclasses (agent/core/user_profile.py)
```

### Data Model

#### UserProfile (Root)
```python
UserProfile(
    personality: PersonalityTraits,
    interests: InterestProfile,
    communication: CommunicationStyle,
    support_needs: SupportNeeds,
    confidence: float  # 0-1, based on data turnover
)
```

#### PersonalityTraits
```python
PersonalityTraits(
    dominant_mood: str,           # Most frequent mood from recent turns
    dominant_mood_frequency: float,  # 0-1 proportion
    emotional_range: float,       # Variance in mood (0-1)
    mood_resilience: float,       # Recovery time from negative moods (hours)
)
```

**Mood Resilience Algorithm**:
Tracks consecutive turns with negative mood (ANXIOUS, FRUSTRATED, ANGRY, CONFUSED) followed by recovery to neutral/positive mood. Computes average recovery duration in hours.

```
Anxious → Anxious → Energized = 2-turn recovery
Used to estimate: user bounces back from stress in ~N hours
```

#### InterestProfile
```python
InterestProfile(
    primary_topics: list[(topic: str, frequency: float, importance: float)],
    passion_level: float,           # How intensely user engages (0-1)
    recurring_concerns: list[(topic: str, count: int)],
)
```

**Extraction**:
- `primary_topics`: Extracted from Layer 4 `topics` field, weighted by `importance_score`
- `passion_level`: Frequency of high-importance turns divided by total turns
- `recurring_concerns`: Topics appearing in complaint/request intents, grouped and counted

#### CommunicationStyle
```python
CommunicationStyle(
    primary_intent: str,            # Most frequent intent (statement, question, etc.)
    intent_distribution: dict[str, float],  # All intents with proportions
    verbosity: float,               # 0-1 (short/concise vs. long/detailed)
    expressiveness: float,          # 0-1 (literal vs. emotional language)
)
```

**Calculation**:
- `primary_intent`: Mode of `intent` field
- `intent_distribution`: Normalized frequency of each intent type
- `verbosity`: Normalize average input length (min/max reference points)
- `expressiveness`: Proportion of inputs with high sentiment/entity count

#### SupportNeeds
```python
SupportNeeds(
    complaint_frequency: float,     # Proportion of complaint intents
    help_seeking_frequency: float,  # Proportion of request/question intents
    validation_preference: SupportStyle,  # EMOTIONAL / PRACTICAL / BALANCED
    crisis_indicators: list[str],   # Detected crisis topics/patterns
)
```

**Support Style Classification**:

| Style | Indicator | LLM Strategy |
|-------|-----------|--------------|
| **EMOTIONAL** | complaint_freq > help_seeking_freq & high expressiveness | Empathize, validate, use warm tone |
| **PRACTICAL** | help_seeking_freq > complaint_freq & low expressiveness | Direct solutions, structured steps |
| **BALANCED** | Roughly equal frequencies | Mix validation + solutions |

**Crisis Indicators**:
Predefined list of crisis keywords/patterns (e.g., "suicidal", "harm", "can't take this") detected in user inputs.

#### Confidence Score
```python
confidence = min(1.0, data_points / 20)  # Caps at 20 data points
```

Confidence increases as more conversation data is available. Threshold for LLM inclusion: **> 0.3**

### Lifecycle

```
Start
  ↓
UserProfileBrain subscribes to RESPONSE_READY events
  ↓
Every N turns (default 10):
  ├─ Queries Layer 4 SQLite
  ├─ Analyzes personality/interests/communication/support
  ├─ Calculates confidence score
  ├─ Updates profile instance
  └─ Persists to disk (user_profile.json)
  ↓
ReasoningBrain requests profile from UserProfileBrain
  ├─ Checks confidence > 0.3
  ├─ Injects profile summary into LLM prompt
  └─ LLM personalizes response
  ↓
Loop
```

### Event Integration

**UserProfileBrain subscribes to**:
- `EventType.RESPONSE_READY` - Increments turn counter, triggers analysis if threshold reached

**No events emitted** - Profile updates are internal; ReasoningBrain pulls on-demand

## Analysis Algorithms

### Personality Analysis

**Input**: All turns from Layer 4

**Output**: PersonalityTraits

```python
def _analyze_personality(self) -> PersonalityTraits:
    # Get all turns, extract mood column
    moods = [turn.user_mood for turn in turns]
    
    # Dominant mood
    dominant = max(moods, key=moods.count)  # Mode
    frequency = moods.count(dominant) / len(moods)
    
    # Emotional range (std dev of mood encoded as numeric)
    mood_values = encode_mood_to_numeric(moods)  # E.g., ANXIOUS=0, NEUTRAL=0.5, ENERGIZED=1
    emotional_range = np.std(mood_values) / np.std([0, 1])  # Normalize 0-1
    
    # Mood resilience
    recovery_hours = calculate_recovery_time(turns)
    
    return PersonalityTraits(
        dominant_mood=dominant,
        dominant_mood_frequency=frequency,
        emotional_range=emotional_range,
        mood_resilience=recovery_hours,
    )
```

### Interest Analysis

**Input**: All turns with topics, importance_score, intent

**Output**: InterestProfile

```python
def _analyze_interests(self) -> InterestProfile:
    topics_weighted = defaultdict(lambda: (freq=0, importance=0))
    
    for turn in turns:
        for topic in turn.topics:
            topics_weighted[topic]['freq'] += 1
            topics_weighted[topic]['importance'] += turn.importance_score
    
    # Top 5 topics by weighted importance
    primary_topics = sorted(
        topics_weighted.items(),
        key=lambda x: x[1]['importance'],
        reverse=True
    )[:5]
    
    # Passion level: proportion of high-importance turns
    high_importance_turns = sum(1 for t in turns if t.importance_score > 0.7)
    passion_level = high_importance_turns / len(turns)
    
    # Recurring concerns: topics appearing in complaints
    concerns = defaultdict(int)
    for turn in turns:
        if turn.intent == 'complaint':
            for topic in turn.topics:
                concerns[topic] += 1
    
    return InterestProfile(
        primary_topics=primary_topics,
        passion_level=passion_level,
        recurring_concerns=list(concerns.items()),
    )
```

### Communication Style Analysis

**Input**: All turns with intent, user_input text, sentiment

**Output**: CommunicationStyle

```python
def _analyze_communication(self) -> CommunicationStyle:
    # Primary intent
    intents = [turn.intent for turn in turns]
    primary = max(intents, key=intents.count)
    
    # Intent distribution
    intent_dist = {intent: intents.count(intent) / len(intents) for intent in set(intents)}
    
    # Verbosity: normalize input length
    input_lengths = [len(turn.user_input.split()) for turn in turns]
    avg_length = np.mean(input_lengths)
    verbosity = min(1.0, avg_length / 50)  # Normalize (50 words = max)
    
    # Expressiveness: entity/sentiment count per turn
    expressiveness_scores = []
    for turn in turns:
        entity_count = len(turn.entities)
        has_sentiment = turn.user_mood_confidence > 0.7
        expressiveness_scores.append(
            (entity_count + (1 if has_sentiment else 0)) / 10
        )
    expressiveness = np.mean(expressiveness_scores)
    
    return CommunicationStyle(
        primary_intent=primary,
        intent_distribution=intent_dist,
        verbosity=min(1.0, verbosity),
        expressiveness=min(1.0, expressiveness),
    )
```

### Support Needs Analysis

**Input**: All turns with intent, expressiveness, crisis indicators

**Output**: SupportNeeds

```python
def _analyze_support_needs(self) -> SupportNeeds:
    intents = [turn.intent for turn in turns]
    complaints = sum(1 for i in intents if i == 'complaint')
    requests = sum(1 for i in intents if i in ('request', 'question'))
    
    complaint_freq = complaints / len(intents)
    request_freq = requests / len(intents)
    
    # Support style
    if complaint_freq > request_freq and expressiveness > 0.6:
        style = SupportStyle.EMOTIONAL
    elif request_freq > complaint_freq and expressiveness < 0.4:
        style = SupportStyle.PRACTICAL
    else:
        style = SupportStyle.BALANCED
    
    # Crisis indicators
    crisis_keywords = ['suicidal', 'harm', 'can't take', 'hopeless', ...]
    indicators = []
    for turn in turns:
        for keyword in crisis_keywords:
            if keyword in turn.user_input.lower():
                indicators.append(keyword)
    
    return SupportNeeds(
        complaint_frequency=complaint_freq,
        help_seeking_frequency=request_freq,
        validation_preference=style,
        crisis_indicators=list(set(indicators)),
    )
```

### Confidence Calculation

```python
def _calculate_confidence(self) -> float:
    """
    Confidence grows with data availability.
    Caps at 20 data points (sufficient sample).
    """
    data_points = len(self.turns)
    return min(1.0, data_points / 20)
```

**Interpretation**:
- `< 0.3`: Too little data, profile unreliable (excluded from LLM)
- `0.3-0.7`: Emerging profile, moderate confidence
- `> 0.7`: Robust profile, high confidence

## Integration with LLM

### ReasoningBrain Integration

```python
def _generate_response(self, context: str) -> str:
    profile = self.user_profile_brain.get_profile()
    
    if profile.confidence > 0.3:
        profile_context = f"""
        ## User Profile
        Mood: {profile.personality.dominant_mood}
        Communication Style: {profile.communication.primary_intent} (Verbosity: {profile.communication.verbosity:.0%})
        Interests: {', '.join([t[0] for t in profile.interests.primary_topics[:3]])}
        Support Preference: {profile.support_needs.validation_preference.name}
        """
    else:
        profile_context = ""
    
    prompt = self.prompt_templates.response_generation_simple(
        context=context,
        user_profile=profile_context,
    )
    
    return self.llm.generate(prompt)
```

### Prompt Template Example

```python
def response_generation_simple(
    context: str,
    user_profile: str = "",
) -> str:
    system = f"""
    You are a helpful, empathetic AI assistant.
    
    {user_profile}
    
    Adapt your response to match the user's communication style and preferences.
    """
    
    user_message = f"""
    {context}
    """
    
    return build_prompt(system=system, user=user_message)
```

## File Structure

```
agent/
├── core/
│   ├── user_profile.py (187 lines)
│   │   └─ PersonalityTraits, InterestProfile, CommunicationStyle
│   │   └─ SupportNeeds, UserProfile dataclasses
│   │
│   └── user_profile_manager.py (378 lines)
│       └─ UserProfileManager: Layer 4 analysis engine
│
├── brains/
│   ├── user_profile_brain.py (74 lines)
│   │   └─ UserProfileBrain: Brain wrapper, event subscription
│   │
│   └── reasoning_brain.py (modified +40 lines)
│       └─ Integrated profile injection into LLM prompts
│
└── llm/
    └── prompt_templates.py (modified)
        └─ Added user_profile parameter

tests/
├── unit/
│   └── test_user_profile_manager.py (175 lines, 10 tests)
│
└── integration/
    └── test_user_profile_brain.py (345 lines, 11 tests)
```

## Configuration

### Tunable Parameters

| Parameter | Default | Location | Impact |
|-----------|---------|----------|--------|
| `analysis_interval` | 10 | UserProfileBrain.__init__ | Update profile every N turns |
| `profile_path` | `data/user_profile.json` | UserProfileManager.__init__ | Persistence location |
| `db_path` | `data/long_term_memory.db` | UserProfileManager.__init__ | Layer 4 source |
| `confidence_threshold` | 0.3 | ReasoningBrain._generate_response | Include profile if confidence > threshold |
| `top_topics_count` | 5 | UserProfileManager._analyze_interests | Number of top interests to track |

### Adjusting Analysis Frequency

```python
brain = UserProfileBrain(data_dir="data")
brain._analysis_interval = 5  # Update every 5 turns instead of 10
```

### Adjusting LLM Inclusion Threshold

```python
# In ReasoningBrain._generate_response()
if profile.confidence > 0.5:  # Require 50% confidence, not 30%
    include_profile_in_prompt()
```

## Testing

### Unit Tests (10 tests, tests/unit/test_user_profile_manager.py)

- Profile creation and serialization
- Personality trait extraction
- Interest analysis
- Communication style detection
- Support pattern analysis
- Confidence scoring
- Mood resilience calculation
- Disk persistence
- Human-readable summaries
- Graceful handling of empty data

**Status**: All passing ✅

### Integration Tests (11 tests, tests/integration/test_user_profile_brain.py)

- UserProfileBrain initialization
- Orchestrator integration (all 9 brains)
- Event subscription (RESPONSE_READY)
- Analysis interval triggering
- Profile retrieval and summary
- Disk persistence across instances
- ContextBrain + UserProfileBrain data flow
- Full orchestrator initialization with dependency injection
- Incremental profile updates
- Orchestrator brain type verification

**Status**: All passing ✅

### Running Tests

```bash
# Unit tests only
pytest tests/unit/test_user_profile_manager.py -v

# Integration tests only
pytest tests/integration/test_user_profile_brain.py -v

# All user profiling tests
pytest tests/unit/test_user_profile_manager.py tests/integration/test_user_profile_brain.py -v

# Full suite with coverage
pytest tests/ -v --cov=agent --cov-report=html
```

## Usage Examples

### Basic Profile Retrieval

```python
from agent.orchestrator import AgentOrchestrator

orch = AgentOrchestrator()
profile_brain = orch.user_profile_brain

profile = profile_brain.get_profile()

print(f"Dominant mood: {profile.personality.dominant_mood}")
print(f"Confidence: {profile.confidence:.0%}")
print(f"Primary interests: {[t[0] for t in profile.interests.primary_topics]}")
print(f"Preferred support: {profile.support_needs.validation_preference.name}")
```

### Profile Summary

```python
summary = profile_brain.get_profile_summary()
print(summary)
```

Output example:
```
User Profile Summary
====================
Dominant Mood: ANXIOUS (frequency: 60%)
Emotional Range: 0.65 (varied)
Mood Resilience: 2.5 hours

Primary Interests: stress management, work deadlines, personal growth
Passion Level: 0.75 (highly engaged)

Communication Style: Direct, practical (verbosity: 0.6, expressiveness: 0.55)
Primary Intent: complaint (60%), request (40%)

Support Preference: BALANCED (validation + solutions)
Confidence: 65% (11 data points)
```

### Manual Profile Analysis

```python
from agent.core.user_profile_manager import UserProfileManager

manager = UserProfileManager(
    db_path="data/long_term_memory.db",
    profile_path="data/user_profile.json",
)

manager.analyze()  # Query Layer 4 and build profile
profile = manager.profile

print(f"Profile confidence: {profile.confidence:.0%}")
```

### Persistence

```python
# Save profile to disk
profile_brain.save_profile()

# Load profile from disk (e.g., on startup)
profile_brain.load_profile()
profile = profile_brain.get_profile()
```

## Future Extensions

### Short-term (Foundation)
1. **Mood Trajectory Analysis** - Trend detection (user improving/worsening)
2. **Semantic Interest Mapping** - Use embeddings to find topic relationships
3. **Communication Evolution** - Track style changes over time

### Medium-term (Personalization)
4. **Adaptive Context Window** - Adjust Layer 1 based on communication verbosity
5. **Adaptive Planning** - Tailor Layer 2 reasoning depth to user's help-seeking frequency
6. **Proactive Crisis Detection** - Alert system when crisis indicators spike

### Long-term (Forecasting)
7. **Mood Forecasting** - Predict user's mood state before turn (enable preemptive support)
8. **Interest Forecasting** - Predict emerging topics user will discuss
9. **Support Need Forecasting** - Predict shift from emotional to practical support needs

## Constraints & Limitations

### Current Scope
- **Passive analysis only** - No real-time intervention or alerts
- **Historical data only** - No predictive forecasting
- **Single-user only** - No multi-user or collaborative profiling
- **Periodic updates** - 10-turn intervals, not continuous

### Data Quality Assumptions
- Layer 4 `importance_score` is reliable (0-1 range)
- `user_mood_confidence` reflects annotation quality
- `topics` field is consistently populated
- `entities` field contains meaningful metadata

### Performance Characteristics
- **Analysis time**: ~50ms for 100 turns (single-threaded)
- **Memory footprint**: ~1MB per profile
- **Persistence**: ~5KB per JSON file
- **No indexing**: Full table scan on each analysis (acceptable for < 1000 turns)

## Troubleshooting

### Profile Confidence Too Low
**Symptom**: Profile confidence < 0.3, excluded from LLM

**Causes**:
- Insufficient conversation data (< 6 turns)
- Layer 4 data not being stored properly

**Solution**:
```python
# Check data availability
profile = profile_brain.get_profile()
print(f"Confidence: {profile.confidence}")
print(f"Data points: {len(profile_brain._profile_manager._turns)}")

# Manually trigger analysis
profile_brain._profile_manager.analyze()
```

### Profile Not Updating
**Symptom**: Profile stale after many turns

**Causes**:
- Analysis interval too high
- RESPONSE_READY events not firing
- Profile manager not connected to Layer 4

**Solution**:
```python
# Check interval
print(f"Turns since analysis: {profile_brain._turns_since_analysis}")
print(f"Interval: {profile_brain._analysis_interval}")

# Force analysis
profile_brain._profile_manager.analyze()
```

### Crisis Indicators Not Detected
**Symptom**: Crisis keyword in input but not flagged

**Causes**:
- Keyword not in predefined list
- Input preprocessing removing context

**Solution**:
```python
# Add custom keywords
keywords = profile.support_needs.crisis_indicators
# Review detected keywords
print(keywords)
```

## References

- Layer 4 Memory: `agent/core/long_term_memory.py`
- Brain Base Class: `agent/core/messaging/brain_base.py`
- Event Bus: `agent/core/messaging/event_bus.py`
- ReasoningBrain Integration: `agent/brains/reasoning_brain.py`
