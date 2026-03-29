"""
Phase 4: Finite State Machine for Emotional State Transitions

Implements state transitions with inertia and threshold-based filtering
for smooth, natural mood changes in Mimi.

Usage:
    fsm = EmotionalFSM(inertia=0.15, persistence=3)
    state, confidence = fsm.process_text("isso está muito interessante!")
"""

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class EmotionalState(Enum):
    """Mimi's 7 emotional states."""
    ENERGIZED = "ENERGIZED"
    DEPRESSED = "DEPRESSED"
    STABLE = "STABLE"
    ANALYTICAL = "ANALYTICAL"
    DISSOCIATED = "DISSOCIATED"
    INTERESTED = "INTERESTED"
    UNINTERESTED = "UNINTERESTED"


@dataclass
class StateTransition:
    """Records a state transition event."""
    from_state: str
    to_state: str
    confidence: float
    timestamp: float
    trigger_text: str


@dataclass
class FSMConfig:
    """Configuration for the emotional FSM."""
    # Threshold for state change (must exceed current by this margin)
    inertia: float = 0.15
    
    # How many consistent inputs before confirming state
    persistence: int = 3
    
    # Decay factor for affinity scores over time
    decay_factor: float = 0.95
    
    # Minimum confidence to trigger a state change
    min_confidence: float = 0.3
    
    # Default state when uncertain
    default_state: str = "STABLE"


class EmotionalFSM:
    """
    Finite State Machine for Mimi's emotional states.
    
    Features:
    - Inertia: State changes require margin over current state
    - Persistence: Multiple consistent inputs before confirming change
    - Decay: Affinity scores decay over time for natural transitions
    """
    
    def __init__(
        self,
        centroids: Optional[Dict[str, np.ndarray]] = None,
        config: Optional[FSMConfig] = None,
        word_vectors=None,
    ):
        self.centroids = centroids or {}
        self.config = config or FSMConfig()
        self.word_vectors = word_vectors
        
        # Current state
        self.current_state: str = self.config.default_state
        self.state_confidence: float = 1.0
        
        # Transition tracking
        self.state_scores: Dict[str, float] = {s.value: 0.5 for s in EmotionalState}
        self.consistent_inputs: int = 0
        self.pending_state: Optional[str] = None
        
        # History
        self.history: List[StateTransition] = []
        self.last_update: float = time.time()
    
    def process_text(self, text: str) -> Tuple[str, float]:
        """
        Process input text and return updated emotional state.
        
        Args:
            text: Input text to analyze
        
        Returns:
            Tuple of (state_name, confidence)
        """
        # Compute text vector
        text_vector = self._text_to_vector(text)
        if text_vector is None:
            return self.current_state, self.state_confidence
        
        # Compute affinity scores
        affinity = self._compute_affinity(text_vector)
        
        # Apply state machine logic
        new_state, confidence = self._apply_fsm_logic(affinity, text)
        
        return new_state, confidence
    
    def _text_to_vector(self, text: str) -> Optional[np.ndarray]:
        """Convert text to vector using word embeddings."""
        if self.word_vectors is None:
            return None
        
        # Tokenize and get vectors
        tokens = text.lower().split()
        vectors = []
        
        for token in tokens:
            try:
                vec = self.word_vectors[token]
                vectors.append(vec)
            except KeyError:
                continue
        
        if not vectors:
            return None
        
        # Average vector
        return np.mean(vectors, axis=0)
    
    def _compute_affinity(self, text_vector: np.ndarray) -> Dict[str, float]:
        """Compute affinity scores between text and all state centroids."""
        scores = {}
        
        for state, centroid in self.centroids.items():
            try:
                similarity = np.dot(text_vector, centroid) / (
                    np.linalg.norm(text_vector) * np.linalg.norm(centroid)
                )
                scores[state] = float((similarity + 1) / 2)  # Normalize to 0-1
            except (ValueError, ZeroDivisionError):
                scores[state] = 0.5
        
        return scores
    
    def _apply_fsm_logic(
        self,
        affinity: Dict[str, float],
        text: str,
    ) -> Tuple[str, float]:
        """
        Apply FSM logic with inertia and persistence.
        
        Returns:
            Tuple of (state, confidence)
        """
        # Apply decay to existing scores
        self._apply_decay()
        
        # Update scores with new affinity (exponential moving average)
        for state, score in affinity.items():
            if state in self.state_scores:
                self.state_scores[state] = (
                    0.7 * score + 0.3 * self.state_scores.get(state, 0.5)
                )
        
        # Find best candidate state
        sorted_states = sorted(
            self.state_scores.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        best_state, best_score = sorted_states[0]
        second_state, second_score = sorted_states[1] if len(sorted_states) > 1 else ("", 0)
        
        # Check inertia: must exceed current by margin
        current_score = self.state_scores.get(self.current_state, 0.5)
        margin = best_score - current_score
        
        # Check if we need a state change
        if best_state != self.current_state:
            # Check if margin exceeds inertia threshold
            if margin >= self.config.inertia and best_score >= self.config.min_confidence:
                # Check persistence
                if self.pending_state == best_state:
                    self.consistent_inputs += 1
                else:
                    self.pending_state = best_state
                    self.consistent_inputs = 1
                
                # Confirm state change after persistence
                if self.consistent_inputs >= self.config.persistence:
                    self._transition_to(best_state, best_score, text)
            else:
                # Reset persistence
                self.pending_state = None
                self.consistent_inputs = 0
        
        return self.current_state, self.state_confidence
    
    def _apply_decay(self) -> None:
        """Apply temporal decay to state scores."""
        current_time = time.time()
        elapsed = current_time - self.last_update
        
        # Decay factor per second (configurable)
        decay = self.config.decay_factor ** (elapsed / 10.0)
        
        for state in self.state_scores:
            self.state_scores[state] *= decay
            # Drift towards STABLE
            if state != "STABLE":
                self.state_scores[state] = (
                    self.state_scores[state] * 0.95 + 0.5 * 0.05
                )
        
        self.last_update = current_time
    
    def _transition_to(self, new_state: str, confidence: float, text: str) -> None:
        """Execute state transition."""
        old_state = self.current_state
        
        transition = StateTransition(
            from_state=old_state,
            to_state=new_state,
            confidence=confidence,
            timestamp=time.time(),
            trigger_text=text[:100],  # Truncate long texts
        )
        self.history.append(transition)
        
        logger.info(
            f"State transition: {old_state} -> {new_state} "
            f"(confidence: {confidence:.2f})"
        )
        
        self.current_state = new_state
        self.state_confidence = confidence
        self.pending_state = None
        self.consistent_inputs = 0
    
    def get_state(self) -> Dict:
        """Get current FSM state as dict."""
        return {
            "state": self.current_state,
            "confidence": self.state_confidence,
            "scores": self.state_scores.copy(),
            "pending_state": self.pending_state,
            "consistent_inputs": self.consistent_inputs,
        }
    
    def get_history(self, limit: int = 10) -> List[Dict]:
        """Get recent state transition history."""
        recent = self.history[-limit:] if self.history else []
        return [
            {
                "from": t.from_state,
                "to": t.to_state,
                "confidence": t.confidence,
                "timestamp": t.timestamp,
                "text": t.trigger_text,
            }
            for t in recent
        ]
    
    def reset(self, initial_state: str = "STABLE") -> None:
        """Reset FSM to initial state."""
        self.current_state = initial_state
        self.state_confidence = 1.0
        self.state_scores = {s.value: 0.5 for s in EmotionalState}
        self.pending_state = None
        self.consistent_inputs = 0
        self.history.clear()
        self.last_update = time.time()
    
    def save_state(self, output_path: str) -> None:
        """Save FSM state to JSON file."""
        state = self.get_state()
        state["history"] = self.get_history(limit=100)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)
    
    def load_state(self, state_path: str) -> None:
        """Load FSM state from JSON file."""
        with open(state_path, 'r', encoding='utf-8') as f:
            state = json.load(f)
        
        self.current_state = state.get("state", "STABLE")
        self.state_confidence = state.get("confidence", 1.0)
        self.state_scores = state.get("scores", {})
        self.pending_state = state.get("pending_state")
        self.consistent_inputs = state.get("consistent_inputs", 0)


class KeywordFSM:
    """
    Lightweight FSM using keyword matching instead of word vectors.
    
    Fallback for when word embeddings are not available.
    Uses the hash table export for O(1) lookups.
    """
    
    def __init__(self, hash_table_path: Optional[str] = None, config: Optional[FSMConfig] = None):
        self.config = config or FSMConfig()
        self.hash_table: Dict[str, Dict[str, float]] = {}
        
        if hash_table_path:
            self.load_hash_table(hash_table_path)
        
        # FSM state
        self.current_state: str = self.config.default_state
        self.state_confidence: float = 1.0
        self.state_scores: Dict[str, float] = {s.value: 0.5 for s in EmotionalState}
        self.pending_state: Optional[str] = None
        self.consistent_inputs: int = 0
    
    def load_hash_table(self, path: str) -> None:
        """Load word->state mapping from JSON hash table."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.hash_table = data.get("words", {})
        logger.info(f"Loaded hash table with {len(self.hash_table)} words")
    
    def process_text(self, text: str) -> Tuple[str, float]:
        """Process text using keyword matching."""
        tokens = text.lower().split()
        
        # Accumulate state scores from matched words
        state_accum: Dict[str, float] = {s.value: 0.0 for s in EmotionalState}
        match_count = 0
        
        for token in tokens:
            if token in self.hash_table:
                word_states = self.hash_table[token]
                for state, weight in word_states.items():
                    if state in state_accum:
                        state_accum[state] += weight
                match_count += 1
        
        if match_count == 0:
            return self.current_state, self.state_confidence
        
        # Normalize
        total = sum(state_accum.values())
        if total > 0:
            affinity = {k: v / total for k, v in state_accum.items()}
        else:
            affinity = {k: 0.5 for k in state_accum.keys()}
        
        # Apply same FSM logic
        return self._apply_fsm_logic(affinity, text)
    
    def _apply_fsm_logic(
        self,
        affinity: Dict[str, float],
        text: str,
    ) -> Tuple[str, float]:
        """Apply FSM logic (same as EmotionalFSM)."""
        for state, score in affinity.items():
            if state in self.state_scores:
                self.state_scores[state] = (
                    0.7 * score + 0.3 * self.state_scores.get(state, 0.5)
                )
        
        sorted_states = sorted(
            self.state_scores.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        best_state, best_score = sorted_states[0]
        current_score = self.state_scores.get(self.current_state, 0.5)
        margin = best_score - current_score
        
        if best_state != self.current_state:
            if margin >= self.config.inertia and best_score >= self.config.min_confidence:
                if self.pending_state == best_state:
                    self.consistent_inputs += 1
                else:
                    self.pending_state = best_state
                    self.consistent_inputs = 1
                
                if self.consistent_inputs >= self.config.persistence:
                    old_state = self.current_state
                    logger.info(f"State transition: {old_state} -> {best_state}")
                    self.current_state = best_state
                    self.state_confidence = best_score
                    self.pending_state = None
                    self.consistent_inputs = 0
            else:
                self.pending_state = None
                self.consistent_inputs = 0
        
        return self.current_state, self.state_confidence
    
    def get_state(self) -> Dict:
        """Get current FSM state."""
        return {
            "state": self.current_state,
            "confidence": self.state_confidence,
            "scores": self.state_scores.copy(),
        }
