"""Factory for creating and managing LLM providers."""
import logging
from typing import Type, Dict
from agent.llm.config import LLMConfig
from agent.llm.provider import LLMProvider
from agent.llm.errors import LLMValidationError


logger = logging.getLogger(__name__)


class LLMProviderFactory:
    """Factory for instantiating and managing LLM providers with validation."""

    _PROVIDERS: Dict[str, Type[LLMProvider]] = {}

    @classmethod
    def _initialize_providers(cls) -> None:
        """Initialize default providers mapping."""
        if not cls._PROVIDERS:
            from agent.llm.ollama_provider import OllamaProvider
            cls._PROVIDERS['ollama'] = OllamaProvider

    @staticmethod
    async def create(config: LLMConfig) -> LLMProvider:
        """Create and validate a provider instance.

        Args:
            config: LLMConfig instance specifying provider and model.

        Returns:
            Instantiated LLMProvider configured and validated.

        Raises:
            LLMValidationError: If provider type unknown or connection invalid.
        """
        LLMProviderFactory._initialize_providers()

        provider_name = config.provider
        if provider_name not in LLMProviderFactory._PROVIDERS:
            raise LLMValidationError(
                f"Unknown provider '{provider_name}'. "
                f"Available providers: {list(LLMProviderFactory._PROVIDERS.keys())}"
            )

        provider_class = LLMProviderFactory._PROVIDERS[provider_name]
        provider = provider_class(config)

        is_valid = await provider.validate_connection()
        if not is_valid:
            logger.warning(
                f"Provider '{provider_name}' connection validation failed, "
                f"but continuing anyway. Model: {config.model}"
            )

        return provider

    @staticmethod
    def register_provider(name: str, provider_class: Type[LLMProvider]) -> None:
        """Register a new provider class for factory instantiation.

        Args:
            name: String identifier for the provider.
            provider_class: LLMProvider subclass to register.
        """
        LLMProviderFactory._initialize_providers()
        LLMProviderFactory._PROVIDERS[name] = provider_class
