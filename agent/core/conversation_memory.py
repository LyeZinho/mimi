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
