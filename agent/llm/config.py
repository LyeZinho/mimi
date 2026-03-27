"""LLM provider configuration dataclasses."""
from dataclasses import dataclass


@dataclass
class LLMConfig:
    """Base configuration for LLM providers."""

    provider: str
    model: str
    timeout_sec: float = 30.0
    max_retries: int = 0


@dataclass
class OllamaConfig(LLMConfig):
    """Configuration for Ollama provider."""

    host: str = "http://localhost:11434"
    temperature: float = 0.7
    top_p: float = 0.9


@dataclass
class GeminiConfig(LLMConfig):
    """Configuration for Google Gemini provider."""

    api_key: str = ""


@dataclass
class OpenAIConfig(LLMConfig):
    """Configuration for OpenAI provider."""

    api_key: str = ""
    temperature: float = 0.7
    max_tokens: int = 2048
