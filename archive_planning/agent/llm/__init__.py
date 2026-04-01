"""LLM: cliente e prompts."""

from .client import LLMClient
from .prompts import build_system_prompt, build_user_prompt
from .errors import (
    LLMProviderError,
    LLMConnectionError,
    LLMAuthError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMValidationError,
)

__all__ = [
    "LLMClient",
    "build_system_prompt",
    "build_user_prompt",
    "LLMProviderError",
    "LLMConnectionError",
    "LLMAuthError",
    "LLMRateLimitError",
    "LLMTimeoutError",
    "LLMValidationError",
]
