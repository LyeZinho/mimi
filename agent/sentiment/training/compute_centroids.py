"""
Phase 3: Centroid Computation for Emotional States

Computes centroids (average vectors) for Mimi's 7 emotional states using
seed words and expanding via cosine similarity.

Usage:
    python -m agent.sentiment.training.compute_centroids \
        --model ./data/models/mimi_embeddings_word2vec.model \
        --output ./data/models/state_centroids.npz
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Mimi's 7 emotional states with seed words
# These should be refined based on desired personality
STATE_SEED_WORDS = {
    "ENERGIZED": [
        # Energy, motivation, excitement
        "energia", "motivação", "excitado", "empolgado", "ação", "vibrante",
        "dinâmico", "ativo", "rápido", "intenso", "poderoso", "forte",
        "coragem", "determinação", "foco", "impulso", "accelerar", "push",
        "run", "execute", "deploy", "ship", "launch", "create", "build",
        "amazing", "awesome", "fantastic", "perfect", "excellent",
    ],
    "DEPRESSED": [
        # Low energy, sadness, difficulty
        "cansado", "triste", "desanimado", "pesado", "lento", "difícil",
        "problema", "falha", "erro", "crash", "bug", "frustrante",
        "impossível", "desistir", "fim", "perda", "fracasso", "empty",
        "failed", "broken", "wrong", "bad", "terrible", "awful",
        "suffering", "pain", "hurt", "loss", "defeat",
    ],
    "STABLE": [
        # Neutral, balanced, calm
        "normal", "comum", "regular", "ok", "bem", "certo", "calmo",
        "equilibrado", "padrão", "default", "fine", "alright", "steady",
        "balanced", "consistent", "reliable", "stable", "maintained",
        "ongoing", "routine", "standard", "typical", "usual",
    ],
    "ANALYTICAL": [
        # Logic, code, technical thinking
        "análise", "lógica", "código", "debug", "implementação", "função",
        "variável", "algoritmo", "complexidade", "otimização", "refatorar",
        "testar", "verificar", "validar", "documentação", "technical",
        "architect", "pattern", "framework", "api", "endpoint", "async",
        "compile", "execute", "evaluate", "compute", "process", "transform",
        "systematic", "methodical", "precise", "accurate", "efficient",
    ],
    "DISSOCIATED": [
        # Distant, unfocused, waiting
        "distante", "longe", "esquecer", "perdido", "vago", "indefinido",
        "nevoa", "soneca", "descansar", "pausa", "break", "afk",
        "thinking", "processing", "loading", "buffer", "wait", "pending",
        "idle", "sleeping", "hibernate", "standby", "offline",
        "unclear", "vague", "abstract", "theoretical", "hypothetical",
    ],
    "INTERESTED": [
        # Curiosity, learning, exploration
        "curioso", "interessante", "novidade", "descobrir", "aprender",
        "explorar", "investigar", "pesquisar", "entender", "como",
        "porquê", "what", "why", "how", "interesting", "cool", "wow",
        "fascinating", "intriguing", "compelling", "engaging", "absorbing",
        "discover", "explore", "learn", "study", "examine", "investigate",
    ],
    "UNINTERESTED": [
        # Bored, dismissive, low engagement
        "entediado", "chato", "repetitivo", "monótono", "sem graça",
        "irrelevante", "desnecessário", "boring", "meh", "whatever",
        "tanto faz", "foda-se", "nah", "nope", "bored", "tired",
        "redundant", "obvious", "trivial", "pointless", "meaningless",
        "skip", "ignore", "forget", "dismiss", "discard",
    ],
}


class CentroidComputer:
    """Compute and manage emotional state centroids from word embeddings."""
    
    def __init__(self, expansion_threshold: float = 0.6, max_expansion: int = 50):
        """
        Args:
            expansion_threshold: Cosine similarity threshold for word expansion
            max_expansion: Maximum words to add per state during expansion
        """
        self.expansion_threshold = expansion_threshold
        self.max_expansion = max_expansion
        
        self.centroids: Dict[str, np.ndarray] = {}
        self.state_words: Dict[str, List[str]] = {}
        
    def compute_from_seeds(
        self,
        word_vectors,
        seed_words: Optional[Dict[str, List[str]]] = None,
    ) -> Dict[str, np.ndarray]:
        """
        Compute initial centroids from seed words.
        
        Args:
            word_vectors: Gensim Word2Vec/FastText model.wv
            seed_words: Dict mapping state names to seed word lists.
                       Defaults to STATE_SEED_WORDS.
        
        Returns:
            Dict mapping state names to centroid vectors
        """
        seeds = seed_words or STATE_SEED_WORDS
        
        for state, words in seeds.items():
            vectors = []
            valid_words = []
            
            for word in words:
                try:
                    vec = word_vectors[word]
                    vectors.append(vec)
                    valid_words.append(word)
                except KeyError:
                    logger.debug(f"Seed word '{word}' not in vocabulary, skipping")
            
            if not vectors:
                logger.warning(f"No valid seed words for state '{state}'")
                continue
            
            centroid = np.mean(vectors, axis=0)
            self.centroids[state] = centroid
            self.state_words[state] = valid_words
            
            logger.info(
                f"Computed centroid for '{state}' from {len(valid_words)} words"
            )
        
        return self.centroids
    
    def expand_by_proximity(
        self,
        word_vectors,
        vocabulary: List[str],
        seed_words: Optional[Dict[str, List[str]]] = None,
    ) -> Dict[str, List[str]]:
        """
        Expand state word lists by cosine similarity to centroids.
        
        Finds additional words that orbit each centroid and assigns them
        influence weights based on proximity.
        
        Args:
            word_vectors: Gensim Word2Vec/FastText model.wv
            vocabulary: List of all words in model vocabulary
            seed_words: Original seed words (to avoid re-adding)
        
        Returns:
            Dict mapping state names to expanded word lists with weights
        """
        seeds = seed_words or STATE_SEED_WORDS
        expanded = {}
        
        for state, centroid in self.centroids.items():
            state_set = set(seeds.get(state, []))
            word_scores = []
            
            for word in vocabulary:
                if word in state_set:
                    continue
                
                try:
                    vec = word_vectors[word]
                    similarity = np.dot(centroid, vec) / (
                        np.linalg.norm(centroid) * np.linalg.norm(vec)
                    )
                    
                    if similarity >= self.expansion_threshold:
                        word_scores.append((word, float(similarity)))
                except KeyError:
                    continue
            
            # Sort by similarity and take top N
            word_scores.sort(key=lambda x: x[1], reverse=True)
            expanded_words = [
                (word, score) for word, score in word_scores[:self.max_expansion]
            ]
            
            # Store expanded word list
            expanded[state] = expanded_words
            logger.info(
                f"Expanded '{state}' to {len(expanded_words)} additional words"
            )
        
        return expanded
    
    def compute_affinity(self, text_vector: np.ndarray) -> Dict[str, float]:
        """
        Compute affinity scores between a text vector and all state centroids.
        
        Args:
            text_vector: Vector representation of input text
        
        Returns:
            Dict mapping state names to affinity scores (0-1)
        """
        scores = {}
        
        for state, centroid in self.centroids.items():
            # Cosine similarity
            similarity = np.dot(text_vector, centroid) / (
                np.linalg.norm(text_vector) * np.linalg.norm(centroid)
            )
            # Normalize to 0-1 range
            scores[state] = float((similarity + 1) / 2)
        
        return scores
    
    def get_best_state(self, text_vector: np.ndarray) -> Tuple[str, float]:
        """Get the state with highest affinity for given text vector."""
        scores = self.compute_affinity(text_vector)
        best_state = max(scores, key=scores.get)
        return best_state, scores[best_state]
    
    def save(self, output_path: str) -> None:
        """Save centroids to compressed numpy file."""
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        
        # Save centroids
        np.savez_compressed(
            str(output),
            centroids=np.array([self.centroids[k] for k in sorted(self.centroids)]),
            state_names=np.array(sorted(self.centroids.keys())),
        )
        
        # Also save as JSON for easy inspection
        json_path = output.with_suffix('.json')
        centroids_json = {
            state: vec.tolist() for state, vec in self.centroids.items()
        }
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(centroids_json, f, indent=2)
        
        logger.info(f"Centroids saved to {output} and {json_path}")
    
    def load(self, model_path: str) -> None:
        """Load centroids from saved file."""
        data = np.load(model_path, allow_pickle=True)
        
        state_names = data['state_names']
        centroids_array = data['centroids']
        
        self.centroids = {
            name: vec for name, vec in zip(state_names, centroids_array)
        }
        
        logger.info(f"Loaded {len(self.centroids)} centroids from {model_path}")
    
    def get_state_info(self) -> Dict[str, Dict]:
        """Get information about each state's centroid."""
        info = {}
        for state, centroid in self.centroids.items():
            info[state] = {
                "dimension": len(centroid),
                "norm": float(np.linalg.norm(centroid)),
                "seed_word_count": len(self.state_words.get(state, [])),
            }
        return info


def compute_word_influence(
    word_vector: np.ndarray,
    centroids: Dict[str, np.ndarray],
) -> Dict[str, float]:
    """
    Compute influence weights for a word across all states.
    
    Returns normalized weights summing to 1.
    """
    scores = {}
    
    for state, centroid in centroids.items():
        similarity = np.dot(word_vector, centroid) / (
            np.linalg.norm(word_vector) * np.linalg.norm(centroid)
        )
        scores[state] = max(0, float(similarity))  # Clip negative values
    
    # Normalize to sum to 1
    total = sum(scores.values())
    if total > 0:
        scores = {k: v / total for k, v in scores.items()}
    
    return scores


def main():
    """Main entry point for centroid computation."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Compute emotional state centroids from word embeddings"
    )
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        help="Path to trained embedding model (.model file)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="./data/models/state_centroids.npz",
        help="Output path for centroids file",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.6,
        help="Cosine similarity threshold for word expansion",
    )
    parser.add_argument(
        "--max-expand",
        type=int,
        default=50,
        help="Maximum words to add per state during expansion",
    )
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    
    from gensim.models import Word2Vec, FastText
    
    # Load model
    logger.info(f"Loading model from {args.model}...")
    if 'fasttext' in args.model.lower():
        model = FastText.load(args.model)
    else:
        model = Word2Vec.load(args.model)
    
    # Compute centroids
    computer = CentroidComputer(
        expansion_threshold=args.threshold,
        max_expansion=args.max_expand,
    )
    
    # Phase 3a: Compute from seeds
    centroids = computer.compute_from_seeds(model.wv)
    logger.info(f"Computed {len(centroids)} centroids")
    
    # Phase 3b: Expand by proximity
    vocabulary = list(model.wv.key_to_index.keys())
    expanded = computer.expand_by_proximity(model.wv, vocabulary)
    
    # Save
    computer.save(args.output)
    
    # Print summary
    info = computer.get_state_info()
    logger.info("\nState Centroids Summary:")
    for state, data in info.items():
        logger.info(f"  {state}: {data}")


if __name__ == "__main__":
    main()
