"""Abstract base class for TTS providers using Strategy Pattern."""
from abc import ABC, abstractmethod
from typing import List, Union, AsyncIterator
from agent.output.config import TTSConfig


class TTSProvider(ABC):
    """Abstract base class for TTS providers."""

    def __init__(self, config: TTSConfig) -> None:
        """Initialize TTS provider with configuration.

        Args:
            config: TTSConfig instance with provider settings.
        """
        self.config = config

    @abstractmethod
    async def synthesize(
        self, text: str, stream: bool = False
    ) -> Union[bytes, AsyncIterator[bytes]]:
        """Synthesize text to speech.

        Args:
            text: Text to synthesize.
            stream: If True, return AsyncIterator for streaming audio.
                   If False, return complete audio bytes.

        Returns:
            Either bytes of complete audio or AsyncIterator yielding audio chunks.

        Raises:
            ValueError: If text is empty or invalid.
            RuntimeError: If synthesis fails.
        """
        pass

    @abstractmethod
    def set_voice(self, voice_id: str) -> None:
        """Set the voice for synthesis.

        Args:
            voice_id: Identifier of the voice to use.
        """
        pass

    @abstractmethod
    def get_available_voices(self) -> List[dict]:
        """Get list of available voices.

        Returns:
            List of dictionaries containing voice information.
            Each dict should contain 'id' and/or 'name' keys.
        """
        pass

    @abstractmethod
    def get_usage_stats(self) -> dict:
        """Get usage statistics.

        Returns:
            Dictionary with keys:
            - audio_duration_sec: Total audio duration synthesized (float)
            - requests: Number of synthesis requests (int)
            - errors: Number of errors encountered (int)
        """
        pass
