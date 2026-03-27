"""Abstract base class for LLM providers."""
from abc import ABC, abstractmethod
from agent.llm.config import LLMConfig


class LLMProvider(ABC):
    """Abstract base class for LLM providers with usage tracking."""

    def __init__(self, config: LLMConfig):
        """Initialize provider with configuration.
        
        Args:
            config: LLMConfig instance with provider settings.
        """
        self.config = config
        self.token_count_in = 0
        self.token_count_out = 0
        self.request_count = 0
        self.error_count = 0
        self.total_latency_ms = 0.0

    @abstractmethod
    async def generate(self, prompt, stream=False):
        """Generate response from prompt.
        
        Args:
            prompt: Input prompt text.
            stream: Whether to stream response.
            
        Returns:
            Generated response text.
        """
        pass

    @abstractmethod
    def count_tokens(self, text):
        """Count tokens in text.
        
        Args:
            text: Input text to count.
            
        Returns:
            Number of tokens.
        """
        pass

    @abstractmethod
    async def validate_connection(self):
        """Validate connection to provider.
        
        Returns:
            True if connection valid, False otherwise.
        """
        pass

    def get_usage_stats(self):
        """Get usage statistics dictionary.
        
        Returns:
            Dict with usage stats: provider, model, tokens_in, tokens_out,
            requests, errors, avg_latency_ms.
        """
        avg_latency = (
            self.total_latency_ms / self.request_count
            if self.request_count > 0
            else 0.0
        )
        
        return {
            'provider': self.config.provider,
            'model': self.config.model,
            'tokens_in': self.token_count_in,
            'tokens_out': self.token_count_out,
            'requests': self.request_count,
            'errors': self.error_count,
            'avg_latency_ms': avg_latency,
        }
