"""
Simple Word2Vec implementation without gensim dependency.
Uses numpy for vector operations.
"""

import json
import logging
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class SimpleWord2Vec:
    """Minimal Word2Vec implementation using co-occurrence matrices."""
    
    def __init__(
        self,
        vector_size: int = 200,
        window: int = 4,
        min_count: int = 2,
        learning_rate: float = 0.025,
        epochs: int = 10,
    ):
        self.vector_size = vector_size
        self.window = window
        self.min_count = min_count
        self.lr = learning_rate
        self.epochs = epochs
        
        self.vocabulary: Dict[str, int] = {}
        self.vectors: Optional[np.ndarray] = None
        self.word_counts: Counter = Counter()
    
    def tokenize(self, text: str) -> List[str]:
        """Simple tokenization for Portuguese."""
        text = text.lower()
        text = re.sub(r'[^\w\sáàâãéèêíìîóòôõúùûç]', ' ', text)
        return text.split()
    
    def fit(self, sentences: List[str]) -> None:
        """Train the model on sentences."""
        logger.info(f"Training on {len(sentences)} sentences")
        
        # Count words and build vocabulary
        tokenized = []
        for sentence in sentences:
            tokens = self.tokenize(sentence)
            self.word_counts.update(tokens)
            tokenized.append(tokens)
        
        # Filter by min_count
        vocab = {w: i for i, (w, c) in enumerate(
            sorted(self.word_counts.items(), key=lambda x: -x[1])
        ) if c >= self.min_count}
        
        self.vocabulary = vocab
        vocab_size = len(vocab)
        logger.info(f"Vocabulary: {vocab_size} words")
        
        if vocab_size == 0:
            logger.error("No words meet min_count threshold")
            return
        
        # Initialize vectors randomly
        np.random.seed(42)
        self.vectors = np.random.randn(vocab_size, self.vector_size) * 0.01
        
        # Build co-occurrence matrix
        logger.info("Building co-occurrence matrix...")
        cooccur = defaultdict(float)
        
        for tokens in tokenized:
            indices = [vocab.get(t) for t in tokens]
            indices = [i for i in indices if i is not None]
            
            for i, center_idx in enumerate(indices):
                for j in range(max(0, i - self.window), min(len(indices), i + self.window + 1)):
                    if i != j:
                        dist = abs(i - j)
                        cooccur[(center_idx, indices[j])] += 1.0 / dist
        
        # Simple training using co-occurrence
        logger.info(f"Training for {self.epochs} epochs...")
        for epoch in range(self.epochs):
            total_loss = 0
            
            for (i, j), count in cooccur.items():
                # Simple update rule
                diff = self.vectors[i] - self.vectors[j]
                gradient = 2 * count * diff
                self.vectors[i] -= self.lr * gradient / (epoch + 1)
            
            if epoch % 5 == 0:
                logger.info(f"  Epoch {epoch} complete")
        
        # L2 normalize
        norms = np.linalg.norm(self.vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1
        self.vectors = self.vectors / norms
        
        logger.info("Training complete")
    
    def get_vector(self, word: str) -> Optional[np.ndarray]:
        """Get vector for a word."""
        idx = self.vocabulary.get(word.lower())
        if idx is None or self.vectors is None:
            return None
        return self.vectors[idx]
    
    def similarity(self, word1: str, word2: str) -> float:
        """Cosine similarity between two words."""
        v1 = self.get_vector(word1)
        v2 = self.get_vector(word2)
        if v1 is None or v2 is None:
            return 0.0
        return float(np.dot(v1, v2))
    
    def most_similar(self, word: str, topn: int = 10) -> List[Tuple[str, float]]:
        """Find most similar words."""
        vec = self.get_vector(word)
        if vec is None or self.vectors is None:
            return []
        
        sims = self.vectors @ vec
        indices = np.argsort(-sims)[:topn + 1]
        
        idx_to_word = {i: w for w, i in self.vocabulary.items()}
        return [(idx_to_word[i], float(sims[i])) 
                for i in indices if idx_to_word.get(i) != word][:topn]
    
    def save(self, path: str) -> None:
        """Save model to JSON."""
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        
        idx_to_word = {i: w for w, i in self.vocabulary.items()}
        
        data = {
            "config": {
                "vector_size": self.vector_size,
                "window": self.window,
                "min_count": self.min_count,
            },
            "vocabulary": {w: i for w, i in self.vocabulary.items()},
            "vectors": self.vectors.tolist() if self.vectors is not None else [],
            "word_counts": dict(self.word_counts),
        }
        
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        
        logger.info(f"Model saved to {output}")
    
    @classmethod
    def load(cls, path: str) -> 'SimpleWord2Vec':
        """Load model from JSON."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        model = cls(
            vector_size=data["config"]["vector_size"],
            window=data["config"]["window"],
            min_count=data["config"]["min_count"],
        )
        model.vocabulary = data["vocabulary"]
        model.vectors = np.array(data["vectors"])
        model.word_counts = Counter(data["word_counts"])
        
        return model


def main():
    """Train and save model."""
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-dir", default="./data/corpus")
    parser.add_argument("--output", default="./data/models/embeddings.json")
    parser.add_argument("--dimensions", type=int, default=200)
    parser.add_argument("--window", type=int, default=4)
    parser.add_argument("--min-count", type=int, default=2)
    parser.add_argument("--epochs", type=int, default=10)
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    # Load corpus
    corpus_dir = Path(args.corpus_dir)
    sentences = []
    for txt_file in corpus_dir.glob("*.txt"):
        with open(txt_file, 'r', encoding='utf-8') as f:
            sentences.extend(f.readlines())
    
    logger.info(f"Loaded {len(sentences)} sentences")
    
    # Train
    model = SimpleWord2Vec(
        vector_size=args.dimensions,
        window=args.window,
        min_count=args.min_count,
        epochs=args.epochs,
    )
    model.fit(sentences)
    
    # Save
    model.save(args.output)
    logger.info(f"Vocabulary size: {len(model.vocabulary)}")


if __name__ == "__main__":
    main()
