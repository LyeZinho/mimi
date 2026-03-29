"""
Sentiment analysis module with FSM-based emotional state detection.

Supports:
- BERT-based sentiment (happy/sad/neutral)
- Word embedding-based analysis (7 states)
- Keyword hash table for fast production lookups
"""

from agent.sentiment.state_machine import (
    EmotionalFSM,
    KeywordFSM,
    FSMConfig,
    EmotionalState,
)

__all__ = [
    "EmotionalFSM",
    "KeywordFSM",
    "FSMConfig",
    "EmotionalState",
]


def create_fsm_from_hash_table(
    hash_table_path: str,
    config=None,
) -> KeywordFSM:
    """Create a KeywordFSM from a hash table JSON file."""
    return KeywordFSM(hash_table_path=hash_table_path, config=config)
