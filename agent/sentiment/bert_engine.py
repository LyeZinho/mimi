"""
Sentiment analysis engine using FinBERT-PT-BR model.

Uses a pre-trained BERT model fine-tuned on Portuguese financial texts
for accurate sentiment classification (POSITIVE, NEGATIVE, NEUTRAL).
"""

import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class BertSentimentEngine:
    """BERT-based sentiment analyzer for Portuguese text."""

    MODEL_PATH = Path(__file__).parent.parent.parent / "sentiment-model"

    LABEL_MAP = {
        0: "happy",
        1: "sad",
        2: "neutral",
    }

    LABEL_NAMES = {
        "POSITIVE": "happy",
        "NEGATIVE": "sad",
        "NEUTRAL": "neutral",
    }

    def __init__(self, model_path: Optional[Path] = None, device: str = "cpu"):
        self.model_path = model_path or self.MODEL_PATH
        self.device = device
        self.tokenizer: Optional[Any] = None
        self.model: Optional[Any] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Load tokenizer and model from disk."""
        try:
            from transformers import AutoTokenizer, BertForSequenceClassification  # type: ignore
            import torch  # type: ignore
            
            logger.info(f"Loading FinBERT-PT-BR model from {self.model_path}...")

            self.tokenizer = AutoTokenizer.from_pretrained(
                str(self.model_path), local_files_only=True
            )
            self.model = BertForSequenceClassification.from_pretrained(
                str(self.model_path), local_files_only=True
            )

            self.model.to(self.device)  # type: ignore
            self.model.eval()  # type: ignore

            self._initialized = True
            logger.info("FinBERT-PT-BR model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load FinBERT-PT-BR model: {e}")
            self._initialized = False
            raise

    async def analyze(self, text: str) -> dict:
        """Analyze sentiment of text and return sentiment + confidence."""
        if not self._initialized or not self.model or not self.tokenizer:
            return {"sentiment": "neutral", "confidence": 0.0, "label": "NEUTRAL"}

        try:
            import torch  # type: ignore
            
            tokens = self.tokenizer(
                text,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512,
            )

            tokens = {k: v.to(self.device) for k, v in tokens.items()}

            with torch.no_grad():
                outputs = self.model(**tokens)

            logits = outputs.logits[0].cpu()
            probabilities = torch.softmax(logits, dim=0)
            predicted_label_id = torch.argmax(logits).item()
            confidence = probabilities[predicted_label_id].item()

            label_name = self.model.config.id2label.get(
                str(predicted_label_id), "NEUTRAL"
            )
            sentiment = self.LABEL_NAMES.get(label_name, "neutral")

            return {
                "sentiment": sentiment,
                "confidence": float(confidence),
                "label": label_name,
                "logits": logits.tolist(),
            }

        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}", exc_info=True)
            return {"sentiment": "neutral", "confidence": 0.0, "label": "NEUTRAL"}

    def is_ready(self) -> bool:
        """Check if engine is initialized and ready."""
        return self._initialized and self.model is not None
