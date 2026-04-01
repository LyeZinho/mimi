"""Exceptions for LLM provider errors."""


class LLMProviderError(Exception):
    """Base exception for all LLM provider errors."""
    pass


class LLMConnectionError(LLMProviderError):
    """Provider unreachable (connection refused, DNS error, etc.)."""
    pass


class LLMAuthError(LLMProviderError):
    """Authentication failed (invalid API key, unauthorized, etc.)."""
    pass


class LLMRateLimitError(LLMProviderError):
    """Rate limit exceeded by provider."""
    pass


class LLMTimeoutError(LLMProviderError):
    """Request timeout (exceeded max wait time)."""
    pass


class LLMValidationError(LLMProviderError):
    """Response validation failed (malformed response, missing fields)."""
    pass
