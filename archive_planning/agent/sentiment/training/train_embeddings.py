"""
Phase 1 & 2: Corpus Acquisition, Preprocessing and Word Embedding Training

Trains FastText/Word2Vec models on hybrid corpus for Mimi's sentiment analysis.

Usage:
    python -m agent.sentiment.training.train_embeddings \
        --corpus-dir ./data/corpus \
        --output-dir ./data/models \
        --model-type word2vec \
        --dimensions 200 \
        --window 4 \
        --min-count 2
"""

import argparse
import logging
import os
import re
import sys
from pathlib import Path
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Portuguese stop words (minimal set - keep technical terms and modern slang)
STOP_WORDS_PT = {
    "a", "o", "e", "é", "de", "do", "da", "dos", "das", "em", "no", "na",
    "nos", "nas", "um", "uma", "uns", "umas", "por", "para", "com", "sem",
    "sob", "sobre", "que", "se", "como", "mas", "ou", "ao", "à", "às",
    "pelo", "pela", "este", "esta", "esse", "essa", "aquele", "aquela",
    "isto", "isso", "aquilo", "eu", "tu", "ele", "ela", "nós", "vós",
    "eles", "elas", "meu", "minha", "teu", "tua", "seu", "sua", "nosso",
    "nossa", "vosso", "vossa", "me", "te", "se", "lhe", "lhes", "nos",
    "vos", "lhe", "lhes",
}


def clean_text(text: str, keep_technical: bool = True) -> str:
    """Clean and normalize text for training.
    
    Preserves: technical terms, modern slang, emoticons.
    Removes: URLs, HTML tags, excessive punctuation.
    """
    text = text.lower()
    
    emoticon_pattern = r'[:;][\-\^]?[)D(|/\\PpOo]'
    emoticons = re.findall(emoticon_pattern, text)
    
    text = re.sub(r'https?://\S+', ' ', text)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'[^\w\s\'\-]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    if emoticons:
        text += ' ' + ' '.join(emoticons)
    
    return text


def tokenize(text: str, remove_stopwords: bool = False) -> List[str]:
    """
    Tokenize text into words.
    
    Preserves:
    - Technical terms (with underscores)
    - Contractions (não, tá, etc.)
    - Internet slang
    """
    # Split on whitespace
    tokens = text.split()
    
    # Remove stop words if requested (but be conservative)
    if remove_stopwords:
        tokens = [t for t in tokens if t not in STOP_WORDS_PT]
    
    return tokens


class CorpusLoader:
    """Load and preprocess text corpus from various sources."""
    
    # File extensions to process
    TEXT_EXTENSIONS = {'.txt', '.md', '.log', '.json', '.csv'}
    
    def __init__(self, corpus_dir: str, min_line_length: int = 5):
        self.corpus_dir = Path(corpus_dir)
        self.min_line_length = min_line_length
        
    def load_all(self) -> List[str]:
        """Load all text files from corpus directory."""
        sentences = []
        
        if not self.corpus_dir.exists():
            logger.warning(f"Corpus directory not found: {self.corpus_dir}")
            return sentences
        
        for file_path in self.corpus_dir.rglob('*'):
            if file_path.suffix.lower() in self.TEXT_EXTENSIONS:
                sentences.extend(self._load_file(file_path))
        
        logger.info(f"Loaded {len(sentences)} sentences from {self.corpus_dir}")
        return sentences
    
    def _load_file(self, file_path: Path) -> List[str]:
        """Load sentences from a single file."""
        sentences = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if len(line) >= self.min_line_length:
                        cleaned = clean_text(line)
                        if cleaned:
                            sentences.append(cleaned)
        except Exception as e:
            logger.warning(f"Error loading {file_path}: {e}")
        
        return sentences


class EmbeddingTrainer:
    """Train word embeddings using Gensim Word2Vec or FastText."""
    
    def __init__(
        self,
        model_type: str = "word2vec",
        dimensions: int = 200,
        window: int = 4,
        min_count: int = 2,
        workers: int = 4,
        epochs: int = 10,
        sg: int = 1,  # Skip-gram (1) vs CBOW (0)
    ):
        self.model_type = model_type.lower()
        self.dimensions = dimensions
        self.window = window
        self.min_count = min_count
        self.workers = workers
        self.epochs = epochs
        self.sg = sg
        
        self.model = None
        
    def train(self, sentences: List[str]) -> None:
        """Train embeddings on tokenized sentences."""
        from gensim.models import Word2Vec, FastText
        
        # Tokenize sentences
        tokenized = [tokenize(s) for s in sentences]
        
        # Filter empty tokenizations
        tokenized = [t for t in tokenized if len(t) >= 2]
        
        logger.info(f"Training {self.model_type} with {len(tokenized)} sentences")
        logger.info(f"Params: dim={self.dimensions}, window={self.window}, "
                    f"min_count={self.min_count}, sg={self.sg}")
        
        if self.model_type == "word2vec":
            self.model = Word2Vec(
                sentences=tokenized,
                vector_size=self.dimensions,
                window=self.window,
                min_count=self.min_count,
                workers=self.workers,
                epochs=self.epochs,
                sg=self.sg,  # Skip-gram for rare words and slang
            )
        elif self.model_type == "fasttext":
            self.model = FastText(
                sentences=tokenized,
                vector_size=self.dimensions,
                window=self.window,
                min_count=self.min_count,
                workers=self.workers,
                epochs=self.epochs,
                sg=self.sg,
            )
        else:
            raise ValueError(f"Unknown model type: {self.model_type}")
        
        logger.info(f"Training complete. Vocabulary size: {len(self.model.wv)}")
        
    def save(self, output_path: str) -> None:
        """Save trained model to disk."""
        if self.model is None:
            raise ValueError("Model not trained yet")
        
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        
        self.model.save(str(output))
        logger.info(f"Model saved to {output}")
        
    def load(self, model_path: str) -> None:
        """Load pre-trained model from disk."""
        from gensim.models import Word2Vec, FastText
        
        if self.model_type == "word2vec":
            self.model = Word2Vec.load(model_path)
        elif self.model_type == "fasttext":
            self.model = FastText.load(model_path)
        else:
            raise ValueError(f"Unknown model type: {self.model_type}")
        
        logger.info(f"Model loaded from {model_path}")
        
    def get_word_vector(self, word: str) -> Optional[np.ndarray]:
        """Get vector for a word, return None if not in vocabulary."""
        if self.model is None:
            return None
        
        try:
            return self.model.wv[word]
        except KeyError:
            return None
            
    def get_similarity(self, word1: str, word2: str) -> float:
        """Get cosine similarity between two words."""
        if self.model is None:
            return 0.0
        
        try:
            return self.model.wv.similarity(word1, word2)
        except KeyError:
            return 0.0
            
    def most_similar(self, word: str, topn: int = 10) -> List[tuple]:
        """Get most similar words to a given word."""
        if self.model is None:
            return []
        
        try:
            return self.model.wv.most_similar(word, topn=topn)
        except KeyError:
            return []
            
    def is_in_vocabulary(self, word: str) -> bool:
        """Check if word is in vocabulary."""
        if self.model is None:
            return False
        return word in self.model.wv


def generate_synthetic_corpus(output_dir: str, num_sentences: int = 10000) -> None:
    """
    Generate synthetic training corpus with emotional and technical content.
    
    This is a fallback for when real corpus data is not available.
    Should be supplemented with real data for production use.
    """
    import random
    
    # Emotional seed words for each state
    emotional_words = {
        "energized": [
            "energia", "motivação", "excitado", "empolgado", "ação", "vibrante",
            "dinâmico", "ativo", "rápido", "intenso", "poderoso", "forte",
            "coragem", "determinação", "foco", "impulso", "accelerar", "push",
        ],
        "depressed": [
            "cansado", "triste", "desanimado", "pesado", "lento", "difícil",
            "problema", "falha", "erro", "crash", "bug", "frustrante",
            "impossível", "desistir", "fim", "perda", "fracasso", "empty",
        ],
        "stable": [
            "normal", "comum", "regular", "ok", "bem", "certo", "calmo",
            "equilibrado", "padrão", "default", "ok", "fine", "alright",
        ],
        "analytical": [
            "análise", "lógica", "código", "debug", "implementação", "função",
            "variável", "algoritmo", "complexidade", "otimização", "refatorar",
            "testar", "verificar", "validar", "documentação", "technical",
            "architect", "pattern", "framework", "api", "endpoint", "async",
        ],
        "dissociated": [
            "distante", "longe", "esquecer", "perdido", "vago", "indefinido",
            "nevoa", "soneca", "descansar", "pausa", "break", "afk",
            "thinking", "processing", "loading", "buffer", "wait",
        ],
        "interested": [
            "curioso", "interessante", "novidade", "descobrir", "aprender",
            "explorar", "investigar", "pesquisar", "entender", "como",
            "porquê", "what", "why", "how", "interesting", "cool",
        ],
        "uninterested": [
            "entediado", "chato", "repetitivo", "monótono", "sem graça",
            "irrelevante", "desnecessário", "boring", "meh", "whatever",
            "tanto faz", "foda-se", "nah", "nope",
        ],
    }
    
    # Technical context words
    tech_words = [
        "python", "javascript", "rust", "c++", "lua", "typescript",
        "react", "vue", "angular", "flask", "django", "fastapi",
        "docker", "kubernetes", "aws", "gcp", "azure",
        "database", "redis", "postgresql", "mongodb",
        "api", "rest", "graphql", "websocket", "grpc",
        "null", "undefined", "overflow", "segmentation", "core dump",
        "stack trace", "exception", "error", "warning", "info",
    ]
    
    # Sentence templates
    templates = [
        "isso é {adj} porque {reason}",
        "estou {adj} com {topic}",
        "preciso {action} o {topic}",
        "o {topic} está {adj}",
        "{action} o código {tech}",
        "isso parece {adj}",
        "não gosto de {topic}",
        "gosto de {topic}",
        "o que você acha de {topic}",
        "como fazer {action} no {tech}",
        "isso é muito {adj}",
        "{tech} é {adj}",
    ]
    
    sentences = []
    for _ in range(num_sentences):
        # Pick random emotional category
        category = random.choice(list(emotional_words.keys()))
        adj = random.choice(emotional_words[category])
        tech = random.choice(tech_words)
        
        # Fill template
        template = random.choice(templates)
        sentence = template.format(
            adj=adj,
            reason=random.choice(emotional_words[category]),
            topic=random.choice(["isso", "aquilo", "o projeto", "o código", "a API"]),
            action=random.choice(["corrigir", "implementar", "testar", "revisar", "fazer"]),
            tech=tech,
        )
        
        sentences.append(clean_text(sentence))
    
    # Save corpus
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    
    corpus_file = output / "synthetic_corpus.txt"
    with open(corpus_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(sentences))
    
    logger.info(f"Generated {len(sentences)} sentences to {corpus_file}")


def main():
    """Main entry point for training script."""
    parser = argparse.ArgumentParser(
        description="Train word embeddings for Mimi sentiment analysis"
    )
    parser.add_argument(
        "--corpus-dir",
        type=str,
        default="./data/corpus",
        help="Directory containing training corpus files",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./data/models",
        help="Directory to save trained models",
    )
    parser.add_argument(
        "--model-type",
        type=str,
        choices=["word2vec", "fasttext"],
        default="word2vec",
        help="Type of embedding model to train",
    )
    parser.add_argument(
        "--dimensions",
        type=int,
        default=200,
        help="Vector dimensions (100-300 recommended)",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=4,
        help="Context window size (3-5 recommended)",
    )
    parser.add_argument(
        "--min-count",
        type=int,
        default=2,
        help="Minimum word frequency",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=10,
        help="Training epochs",
    )
    parser.add_argument(
        "--generate-synthetic",
        action="store_true",
        help="Generate synthetic corpus for training",
    )
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    
    # Generate synthetic corpus if requested
    if args.generate_synthetic:
        logger.info("Generating synthetic corpus...")
        generate_synthetic_corpus(args.corpus_dir, num_sentences=10000)
    
    # Load corpus
    loader = CorpusLoader(args.corpus_dir)
    sentences = loader.load_all()
    
    if not sentences:
        logger.error("No training data found. Use --generate-synthetic to create data.")
        sys.exit(1)
    
    # Train embeddings
    trainer = EmbeddingTrainer(
        model_type=args.model_type,
        dimensions=args.dimensions,
        window=args.window,
        min_count=args.min_count,
        epochs=args.epochs,
    )
    
    trainer.train(sentences)
    
    # Save model
    output_path = Path(args.output_dir) / f"mimi_embeddings_{args.model_type}.model"
    trainer.save(str(output_path))
    
    logger.info("Training complete!")
    logger.info(f"Model saved to: {output_path}")
    logger.info(f"Vocabulary size: {len(trainer.model.wv)}")


if __name__ == "__main__":
    main()
