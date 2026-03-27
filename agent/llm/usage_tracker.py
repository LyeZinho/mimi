"""LLM usage statistics tracking and monitoring."""

from dataclasses import dataclass
import logging


logger = logging.getLogger(__name__)


@dataclass
class UsageStats:
    """Track LLM usage statistics for monitoring and analytics."""
    
    provider: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    requests: int = 0
    errors: int = 0
    total_latency_ms: float = 0.0

    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency per request in milliseconds."""
        if self.requests > 0:
            return self.total_latency_ms / self.requests
        return 0.0

    @property
    def total_tokens(self) -> int:
        """Calculate total tokens (input + output)."""
        return self.tokens_in + self.tokens_out

    @property
    def error_rate(self) -> float:
        """Calculate error rate as percentage."""
        if self.requests > 0:
            return (self.errors / self.requests) * 100
        return 0.0

    def get_summary(self) -> str:
        """Return formatted summary of usage statistics."""
        return (
            f"LLM Usage: {self.provider}/{self.model} | "
            f"Tokens: In={self.tokens_in} Out={self.tokens_out} Total={self.total_tokens} | "
            f"Requests={self.requests} Errors={self.errors} ({self.error_rate:.1f}% error rate) | "
            f"Avg Latency: {self.avg_latency_ms:.0f}ms"
        )

    def log(self) -> None:
        """Log the usage statistics summary."""
        logger.info(self.get_summary())
