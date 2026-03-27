"""
Unit tests for LLM configuration dataclasses.
Following TDD approach: tests first, implementation after.
"""
import pytest
from dataclasses import asdict
from agent.llm.config import LLMConfig, OllamaConfig, GeminiConfig, OpenAIConfig


class TestLLMConfigDefaults:
    """Test base LLMConfig class defaults."""

    def test_llm_config_defaults(self):
        """Test that LLMConfig has required defaults."""
        config = LLMConfig(provider="test", model="test-model")
        
        assert config.provider == "test"
        assert config.model == "test-model"
        assert config.timeout_sec == 30.0
        assert config.max_retries == 0


class TestOllamaConfigDefaults:
    """Test OllamaConfig class defaults."""

    def test_ollama_config_defaults(self):
        """Test that OllamaConfig has all required defaults."""
        config = OllamaConfig(provider="ollama", model="llama2")
        
        assert config.provider == "ollama"
        assert config.model == "llama2"
        assert config.timeout_sec == 30.0
        assert config.max_retries == 0
        assert config.host == "http://localhost:11434"
        assert config.temperature == 0.7
        assert config.top_p == 0.9


class TestGeminiConfigRequiresApiKey:
    """Test GeminiConfig class api_key requirement."""

    def test_gemini_config_requires_api_key(self):
        """Test that GeminiConfig can be created with api_key."""
        config = GeminiConfig(
            provider="gemini",
            model="gemini-pro",
            api_key="test-api-key"
        )
        
        assert config.provider == "gemini"
        assert config.model == "gemini-pro"
        assert config.api_key == "test-api-key"
        assert config.timeout_sec == 30.0
        assert config.max_retries == 0


class TestOpenAIConfigHasModelParams:
    """Test OpenAIConfig class model parameters."""

    def test_openai_config_has_model_params(self):
        """Test that OpenAIConfig has temperature and max_tokens."""
        config = OpenAIConfig(
            provider="openai",
            model="gpt-4",
            api_key="sk-test-key"
        )
        
        assert config.provider == "openai"
        assert config.model == "gpt-4"
        assert config.api_key == "sk-test-key"
        assert config.timeout_sec == 30.0
        assert config.max_retries == 0
        assert config.temperature == 0.7
        assert config.max_tokens == 2048


class TestConfigFromDict:
    """Test configuration instantiation from dictionaries."""

    def test_llm_config_from_dict(self):
        """Test creating LLMConfig from dictionary."""
        config_dict = {
            "provider": "test",
            "model": "test-model",
            "timeout_sec": 60.0,
            "max_retries": 3
        }
        config = LLMConfig(**config_dict)
        
        assert config.provider == "test"
        assert config.model == "test-model"
        assert config.timeout_sec == 60.0
        assert config.max_retries == 3

    def test_ollama_config_from_dict(self):
        """Test creating OllamaConfig from dictionary."""
        config_dict = {
            "provider": "ollama",
            "model": "mistral",
            "host": "http://192.168.1.100:11434",
            "temperature": 0.5,
            "top_p": 0.8
        }
        config = OllamaConfig(**config_dict)
        
        assert config.provider == "ollama"
        assert config.model == "mistral"
        assert config.host == "http://192.168.1.100:11434"
        assert config.temperature == 0.5
        assert config.top_p == 0.8

    def test_gemini_config_from_dict(self):
        """Test creating GeminiConfig from dictionary."""
        config_dict = {
            "provider": "gemini",
            "model": "gemini-pro-vision",
            "api_key": "AIzaSy...",
            "timeout_sec": 45.0
        }
        config = GeminiConfig(**config_dict)
        
        assert config.provider == "gemini"
        assert config.model == "gemini-pro-vision"
        assert config.api_key == "AIzaSy..."
        assert config.timeout_sec == 45.0

    def test_openai_config_from_dict(self):
        """Test creating OpenAIConfig from dictionary."""
        config_dict = {
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "api_key": "sk-...",
            "temperature": 0.9,
            "max_tokens": 1024,
            "max_retries": 2
        }
        config = OpenAIConfig(**config_dict)
        
        assert config.provider == "openai"
        assert config.model == "gpt-3.5-turbo"
        assert config.api_key == "sk-..."
        assert config.temperature == 0.9
        assert config.max_tokens == 1024
        assert config.max_retries == 2
