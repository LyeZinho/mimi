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
