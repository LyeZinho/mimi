"""
Word2Vec training using co-occurrence matrix + SVD for embeddings.
Works without gensim (pure numpy/scipy).

Usage:
    python -m agent.sentiment.training.train_word2vec \
        --corpus-dir ./data/corpus \
        --output ./data/models/word2vec.npz \
        --dimensions 150 \
        --window 5
"""

import json
import logging
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import svds

logger = logging.getLogger(__name__)

# Portuguese stopwords (keep emotional/technical terms)
STOPWORDS_PT = {
    "a", "o", "e", "é", "de", "do", "da", "dos", "das", "em", "no", "na",
    "nos", "nas", "um", "uma", "uns", "umas", "por", "para", "com", "sem",
    "sob", "sobre", "que", "se", "como", "mas", "ou", "ao", "à", "às",
    "pelo", "pela", "este", "esta", "esse", "essa", "aquele", "aquela",
    "isto", "isso", "aquilo", "eu", "tu", "ele", "ela", "nós", "vós",
    "eles", "elas", "meu", "minha", "teu", "tua", "seu", "sua", "nosso",
    "nossa", "vosso", "vossa", "me", "te", "se", "lhe", "lhes",
    "foi", "ser", "ter", "está", "são", "era", "foram", "será",
    "não", "sim", "já", "ainda", "também", "só", "até", "mesmo",
}


def tokenize(text: str, remove_stopwords: bool = False) -> List[str]:
    """Tokenize Portuguese text."""
    text = text.lower()
    text = re.sub(r'[^\w\sáàâãéèêíìîóòôõúùûç]', ' ', text)
    tokens = text.split()
    
    if remove_stopwords:
        tokens = [t for t in tokens if t not in STOPWORDS_PT and len(t) > 1]
    
    return tokens


class Word2VecTrainer:
    """Train word embeddings using co-occurrence + SVD."""
    
    def __init__(
        self,
        vector_size: int = 150,
        window: int = 5,
        min_count: int = 3,
        remove_stopwords: bool = False,
    ):
        self.vector_size = vector_size
        self.window = window
        self.min_count = min_count
        self.remove_stopwords = remove_stopwords
        
        self.vocabulary: Dict[str, int] = {}
        self.vectors: np.ndarray = None
        self.word_counts: Counter = Counter()
    
    def fit(self, sentences: List[str]) -> None:
        """Train embeddings on sentences."""
        logger.info(f"Training on {len(sentences)} sentences")
        
        # Tokenize and count
        tokenized = []
        for sentence in sentences:
            tokens = tokenize(sentence, self.remove_stopwords)
            self.word_counts.update(tokens)
            tokenized.append(tokens)
        
        # Build vocabulary
        vocab_words = [
            w for w, c in self.word_counts.most_common() 
            if c >= self.min_count
        ]
        self.vocabulary = {w: i for i, w in enumerate(vocab_words)}
        vocab_size = len(self.vocabulary)
        
        logger.info(f"Vocabulary: {vocab_size} words (min_count={self.min_count})")
        
        if vocab_size < 10:
            logger.error("Vocabulary too small")
            return
        
        # Build co-occurrence matrix
        logger.info("Building co-occurrence matrix...")
        cooccur = self._build_cooccurrence(tokenized)
        
        # Apply SVD to get embeddings
        logger.info("Computing SVD embeddings...")
        self._compute_embeddings_svd(cooccur)
        
        # L2 normalize
        norms = np.linalg.norm(self.vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1
        self.vectors = self.vectors / norms
        
        logger.info(f"Training complete: {self.vectors.shape}")
    
    def _build_cooccurrence(self, tokenized: List[List[str]]) -> np.ndarray:
        """Build weighted co-occurrence matrix."""
        vocab_size = len(self.vocabulary)
        
        # Use sparse matrix for efficiency
        cooccur = sparse.lil_matrix((vocab_size, vocab_size), dtype=np.float32)
        
        for tokens in tokenized:
            indices = [self.vocabulary.get(t) for t in tokens]
            indices = [i for i in indices if i is not None]
            
            for i, center_idx in enumerate(indices):
                for j in range(max(0, i - self.window), min(len(indices), i + self.window + 1)):
                    if i != j:
                        dist = abs(i - j)
                        weight = 1.0 / dist  # Closer words have more weight
                        cooccur[center_idx, indices[j]] += weight
        
        # Symmetric
        cooccur = cooccur + cooccur.T
        
        return cooccur.tocsr()
    
    def _compute_embeddings_svd(self, cooccur) -> None:
        """Compute embeddings using truncated SVD."""
        # Add context scaling (log co-occurrence works better)
        cooccur.data = np.log1p(cooccur.data)
        
        # Truncated SVD
        k = min(self.vector_size, min(cooccur.shape) - 1)
        U, Sigma, Vt = svds(cooccur, k=k)
        
        # Use U * sqrt(Sigma) as embeddings
        self.vectors = U * np.sqrt(Sigma)
    
    def get_vector(self, word: str) -> np.ndarray:
        """Get vector for a word."""
        idx = self.vocabulary.get(word.lower())
        if idx is None or self.vectors is None:
            return None
        return self.vectors[idx]
    
    def similarity(self, word1: str, word2: str) -> float:
        """Cosine similarity between words."""
        v1 = self.get_vector(word1)
        v2 = self.get_vector(word2)
        if v1 is None or v2 is None:
            return 0.0
        return float(np.dot(v1, v2))
    
    def most_similar(self, word: str, topn: int = 10) -> List[Tuple[str, float]]:
        """Find most similar words."""
        vec = self.get_vector(word)
        if vec is None:
            return []
        
        sims = self.vectors @ vec
        top_indices = np.argsort(-sims)[:topn + 1]
        
        idx_to_word = {i: w for w, i in self.vocabulary.items()}
        return [
            (idx_to_word[i], float(sims[i]))
            for i in top_indices
            if idx_to_word.get(i, '').lower() != word.lower()
        ][:topn]
    
    def find_in_state(self, word: str, centroids: Dict[str, np.ndarray]) -> Dict[str, float]:
        """Find which state a word belongs to based on centroid similarity."""
        vec = self.get_vector(word)
        if vec is None:
            return {}
        
        scores = {}
        for state, centroid in centroids.items():
            similarity = np.dot(vec, centroid) / (
                np.linalg.norm(vec) * np.linalg.norm(centroid) + 1e-8
            )
            scores[state] = float((similarity + 1) / 2)  # Normalize to 0-1
        
        return scores
    
    def save(self, output_path: str) -> None:
        """Save model to compressed numpy file."""
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        
        idx_to_word = {i: w for w, i in self.vocabulary.items()}
        
        np.savez_compressed(
            str(output),
            vectors=self.vectors,
            vocabulary=np.array(list(self.vocabulary.keys())),
            word_counts=np.array([self.word_counts[w] for w in self.vocabulary.keys()]),
        )
        
        logger.info(f"Model saved to {output}")
    
    @classmethod
    def load(cls, path: str) -> 'Word2VecTrainer':
        """Load model from numpy file."""
        data = np.load(path, allow_pickle=True)
        
        model = cls()
        model.vectors = data['vectors']
        vocab_list = data['vocabulary']
        model.vocabulary = {w: i for i, w in enumerate(vocab_list)}
        model.word_counts = Counter(dict(zip(vocab_list, data['word_counts'])))
        
        return model


def compute_centroids(
    model: Word2VecTrainer,
    seed_words: Dict[str, List[str]],
    expand_threshold: float = 0.4,
    max_expand: int = 100,
) -> Tuple[Dict[str, np.ndarray], Dict[str, List[Tuple[str, float]]]]:
    """Compute centroids from seed words and expand by similarity."""
    centroids = {}
    expanded = {}
    
    for state, seeds in seed_words.items():
        vectors = []
        for word in seeds:
            vec = model.get_vector(word)
            if vec is not None:
                vectors.append(vec)
        
        if not vectors:
            logger.warning(f"No vectors for state {state}")
            continue
        
        centroid = np.mean(vectors, axis=0)
        # Normalize
        centroid = centroid / (np.linalg.norm(centroid) + 1e-8)
        centroids[state] = centroid
        
        # Expand by similarity
        expanded_words = []
        for word in model.vocabulary.keys():
            if word in seeds:
                continue
            
            vec = model.get_vector(word)
            if vec is None:
                continue
            
            similarity = np.dot(vec, centroid) / (
                np.linalg.norm(vec) * np.linalg.norm(centroid) + 1e-8
            )
            
            if similarity >= expand_threshold:
                expanded_words.append((word, float(similarity)))
        
        # Sort by similarity and take top N
        expanded_words.sort(key=lambda x: -x[1])
        expanded[state] = expanded_words[:max_expand]
        
        logger.info(f"State '{state}': centroid + {len(expanded_words)} expanded words")
    
    return centroids, expanded


def export_hash_table(
    centroids: Dict[str, np.ndarray],
    expanded: Dict[str, List[Tuple[str, float]]],
    seed_words: Dict[str, List[str]],
    output_path: str,
) -> None:
    """Export enriched hash table."""
    hash_table = {}
    
    # Add seed words with weight 1.0
    for state, seeds in seed_words.items():
        for word in seeds:
            w = word.lower()
            if w not in hash_table:
                hash_table[w] = {}
            hash_table[w][state] = 1.0
    
    # Add expanded words
    for state, word_list in expanded.items():
        for word, similarity in word_list:
            w = word.lower()
            if w not in hash_table:
                hash_table[w] = {}
            # Only add if not already a seed word
            if state not in hash_table[w]:
                hash_table[w][state] = round(similarity, 4)
    
    export = {
        "version": "3.0",
        "description": "Mimi sentiment hash table - trained on literary corpus",
        "states": list(centroids.keys()),
        "word_count": len(hash_table),
        "config": {"min_weight": 0.3, "fallback_state": "STABLE"},
        "words": hash_table,
    }
    
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(export, f, ensure_ascii=False, separators=(',', ':'))
    
    logger.info(f"Hash table exported: {len(hash_table)} words to {output}")


def main():
    """Main training pipeline."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Train Word2Vec and export hash table")
    parser.add_argument("--corpus-dir", default="./data/corpus")
    parser.add_argument("--output", default="./data/models/word2vec.npz")
    parser.add_argument("--hash-output", default="./data/models/sentiment_hash_v3.json")
    parser.add_argument("--dimensions", type=int, default=150)
    parser.add_argument("--window", type=int, default=5)
    parser.add_argument("--min-count", type=int, default=3)
    parser.add_argument("--remove-stopwords", action="store_true")
    parser.add_argument("--expand-threshold", type=float, default=0.35)
    parser.add_argument("--max-expand", type=int, default=150)
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    
    # Load corpus
    corpus_dir = Path(args.corpus_dir)
    sentences = []
    for txt_file in corpus_dir.glob("*.txt"):
        with open(txt_file, 'r', encoding='utf-8') as f:
            lines = [l.strip() for l in f if len(l.strip()) > 10]
            sentences.extend(lines)
    
    logger.info(f"Loaded {len(sentences)} sentences from {corpus_dir}")
    
    # Train embeddings
    model = Word2VecTrainer(
        vector_size=args.dimensions,
        window=args.window,
        min_count=args.min_count,
        remove_stopwords=args.remove_stopwords,
    )
    model.fit(sentences)
    
    # Save embeddings
    model.save(args.output)
    
    # Compute centroids
    from agent.sentiment.training.compute_centroids import STATE_SEED_WORDS
    
    centroids, expanded = compute_centroids(
        model,
        STATE_SEED_WORDS,
        expand_threshold=args.expand_threshold,
        max_expand=args.max_expand,
    )
    
    # Export hash table
    export_hash_table(centroids, expanded, STATE_SEED_WORDS, args.hash_output)
    
    logger.info("Training pipeline complete!")


if __name__ == "__main__":
    main()
