"""Tests for LLM provider error hierarchy."""

import pytest
from agent.llm.errors import (
    LLMProviderError,
    LLMConnectionError,
    LLMAuthError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMValidationError,
)


def test_error_hierarchy():
    """All errors inherit from LLMProviderError."""
    errors = [
        LLMConnectionError("test"),
        LLMAuthError("test"),
        LLMRateLimitError("test"),
        LLMTimeoutError("test"),
        LLMValidationError("test"),
    ]
    
    for error in errors:
        assert isinstance(error, LLMProviderError)


def test_error_messages_preserved():
    """Error messages are preserved through instantiation."""
    msg = "Connection refused on localhost:11434"
    error = LLMConnectionError(msg)
    assert str(error) == msg


def test_error_can_wrap_original():
    """Errors can wrap original exceptions."""
    original = ConnectionError("original error")
    error = LLMConnectionError(f"Failed to connect: {original}")
    assert "original error" in str(error)
