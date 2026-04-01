"""
Phase 5: Export to Hash Table for Production

Exports trained model data to JSON hash table format for O(1) lookups
in production without requiring heavy ML libraries.

Usage:
    python -m agent.sentiment.training.export_hash_table \
        --model ./data/models/mimi_embeddings_word2vec.model \
        --centroids ./data/models/state_centroids.npz \
        --output ./data/models/sentiment_hash.json
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class HashTableExporter:
    """Export sentiment model to optimized JSON hash table for production."""
    
    def __init__(
        self,
        min_weight: float = 0.1,
        max_words: int = 5000,
        include_neutral: bool = True,
    ):
        self.min_weight = min_weight
        self.max_words = max_words
        self.include_neutral = include_neutral
    
    def export_from_model(
        self,
        word_vectors,
        centroids: Dict[str, np.ndarray],
        output_path: str,
    ) -> None:
        """
        Export complete hash table from trained model and centroids.
        
        Args:
            word_vectors: Gensim Word2Vec/FastText model.wv
            centroids: Dict mapping state names to centroid vectors
            output_path: Output JSON file path
        """
        vocabulary = list(word_vectors.key_to_index.keys())
        logger.info(f"Processing {len(vocabulary)} words from vocabulary")
        
        # Compute word influences
        word_states: Dict[str, Dict[str, float]] = {}
        
        for word in vocabulary:
            try:
                vec = word_vectors[word]
                influences = self._compute_influences(vec, centroids)
                
                # Filter by minimum weight
                filtered = {
                    state: round(weight, 4)
                    for state, weight in influences.items()
                    if weight >= self.min_weight
                }
                
                if filtered:
                    word_states[word] = filtered
            except KeyError:
                continue
        
        # Sort and limit
        if len(word_states) > self.max_words:
            # Keep words with highest max weight
            word_weights = {
                word: max(states.values())
                for word, states in word_states.items()
            }
            top_words = sorted(
                word_weights.keys(),
                key=lambda w: word_weights[w],
                reverse=True,
            )[:self.max_words]
            word_states = {w: word_states[w] for w in top_words}
        
        # Build export structure
        export_data = {
            "version": "1.0",
            "description": "Mimi sentiment hash table for fast O(1) lookups",
            "states": list(centroids.keys()),
            "word_count": len(word_states),
            "config": {
                "min_weight": self.min_weight,
                "fallback_state": "STABLE",
            },
            "words": word_states,
        }
        
        # Save
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, separators=(',', ':'))
        
        logger.info(
            f"Exported {len(word_states)} words to {output} "
            f"({output.stat().st_size / 1024:.1f} KB)"
        )
    
    def export_from_centroids(
        self,
        centroids: Dict[str, np.ndarray],
        word_list: List[str],
        output_path: str,
    ) -> None:
        """
        Export hash table using just centroids and a word list.
        
        For when full word vectors are not available at runtime.
        
        Args:
            centroids: Dict mapping state names to centroid vectors
            word_list: List of words to include
            output_path: Output JSON file path
        """
        # This requires pre-computed word vectors
        # For production, use export_from_model instead
        raise NotImplementedError(
            "Use export_from_model with full word vectors"
        )
    
    def _compute_influences(
        self,
        word_vector: np.ndarray,
        centroids: Dict[str, np.ndarray],
    ) -> Dict[str, float]:
        """Compute normalized influence weights for a word across states."""
        scores = {}
        
        for state, centroid in centroids.items():
            try:
                similarity = np.dot(word_vector, centroid) / (
                    np.linalg.norm(word_vector) * np.linalg.norm(centroid)
                )
                # Convert to 0-1 range
                scores[state] = max(0, float((similarity + 1) / 2))
            except (ValueError, ZeroDivisionError):
                scores[state] = 0.0
        
        # Normalize to sum to 1
        total = sum(scores.values())
        if total > 0:
            scores = {k: v / total for k, v in scores.items()}
        
        return scores
    
    def export_minimal(
        self,
        seed_words: Dict[str, List[str]],
        output_path: str,
    ) -> None:
        """
        Export minimal hash table with just seed words.
        
        Useful for testing or when no trained model is available.
        Each seed word gets weight 1.0 for its state.
        """
        word_states = {}
        
        for state, words in seed_words.items():
            for word in words:
                word_lower = word.lower()
                if word_lower not in word_states:
                    word_states[word_lower] = {}
                word_states[word_lower][state] = 1.0
        
        export_data = {
            "version": "1.0",
            "description": "Mimi sentiment hash table (minimal, seed words only)",
            "states": list(seed_words.keys()),
            "word_count": len(word_states),
            "config": {
                "min_weight": 0.1,
                "fallback_state": "STABLE",
            },
            "words": word_states,
        }
        
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Exported minimal hash table with {len(word_states)} words")


def load_hash_table(path: str) -> Dict:
    """Load hash table from JSON file."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def query_hash_table(
    hash_table: Dict,
    text: str,
) -> Dict[str, float]:
    """
    Query hash table with text, return state scores.
    
    Args:
        hash_table: Loaded hash table dict
        text: Input text to analyze
    
    Returns:
        Dict mapping state names to aggregated scores
    """
    words = hash_table.get("words", {})
    tokens = text.lower().split()
    
    state_scores: Dict[str, float] = {}
    
    for token in tokens:
        if token in words:
            for state, weight in words[token].items():
                state_scores[state] = state_scores.get(state, 0) + weight
    
    return state_scores


def main():
    """Main entry point for hash table export."""
    parser = argparse.ArgumentParser(
        description="Export sentiment model to JSON hash table"
    )
    parser.add_argument(
        "--model",
        type=str,
        help="Path to trained embedding model (.model file)",
    )
    parser.add_argument(
        "--centroids",
        type=str,
        help="Path to centroids file (.npz)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="./data/models/sentiment_hash.json",
        help="Output path for hash table JSON",
    )
    parser.add_argument(
        "--min-weight",
        type=float,
        default=0.1,
        help="Minimum weight threshold for word inclusion",
    )
    parser.add_argument(
        "--max-words",
        type=int,
        default=5000,
        help="Maximum number of words to include",
    )
    parser.add_argument(
        "--minimal",
        action="store_true",
        help="Export minimal hash table with seed words only",
    )
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    
    exporter = HashTableExporter(
        min_weight=args.min_weight,
        max_words=args.max_words,
    )
    
    if args.minimal:
        from agent.sentiment.training.compute_centroids import STATE_SEED_WORDS
        exporter.export_minimal(STATE_SEED_WORDS, args.output)
    elif args.model and args.centroids:
        from gensim.models import Word2Vec, FastText
        
        # Load model
        logger.info(f"Loading model from {args.model}...")
        if 'fasttext' in args.model.lower():
            model = FastText.load(args.model)
        else:
            model = Word2Vec.load(args.model)
        
        # Load centroids
        centroids_data = np.load(args.centroids, allow_pickle=True)
        centroids = {
            name: vec
            for name, vec in zip(
                centroids_data['state_names'],
                centroids_data['centroids'],
            )
        }
        
        exporter.export_from_model(model.wv, centroids, args.output)
    else:
        parser.error("Either --minimal or both --model and --centroids required")


if __name__ == "__main__":
    main()
