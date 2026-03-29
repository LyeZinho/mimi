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
            0.3 * sentiment_strength +
            0.25 * intent_score +
            0.2 * mood_score +
            0.15 * context.importance_score +
            0.1 * (1.0 if context.user_mood_confidence > 0.8 else 0.5)
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
