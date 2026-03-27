"""Piper TTS provider implementation."""
import asyncio
from typing import List, Union, AsyncIterator
from agent.output.config import PiperConfig
from agent.output.tts_provider import TTSProvider

try:
    import piper
except ImportError:
    piper = None


class PiperProvider(TTSProvider):
    """Piper TTS provider implementation."""

    def __init__(self, config: PiperConfig) -> None:
        """Initialize Piper provider.

        Args:
            config: PiperConfig instance.

        Raises:
            ImportError: If piper library is not installed.
        """
        super().__init__(config)
        if piper is None:
            raise ImportError(
                "piper library is required. "
                "Install with: pip install piper-tts"
            )
        self._requests = 0
        self._errors = 0
        self._audio_duration_sec = 0.0

    async def synthesize(
        self, text: str, stream: bool = False
    ) -> Union[bytes, AsyncIterator[bytes]]:
        """Synthesize text to speech using Piper.

        Args:
            text: Text to synthesize.
            stream: If True, return AsyncIterator. If False, return bytes.

        Returns:
            Audio bytes or AsyncIterator of audio chunks.

        Raises:
            ValueError: If text is empty.
            RuntimeError: If synthesis fails.
        """
        try:
            if not text or not text.strip():
                self._errors += 1
                raise ValueError("Text cannot be empty")

            self._requests += 1

            if stream:
                return self._synthesize_streaming(text)
            else:
                audio_data = await self._synthesize_to_bytes(text)
                return audio_data
        except ValueError:
            raise
        except RuntimeError:
            raise
        except Exception as e:
            self._errors += 1
            raise RuntimeError(f"Synthesis failed: {str(e)}") from e

    async def _synthesize_to_bytes(self, text: str) -> bytes:
        """Synthesize text to complete audio bytes.

        Args:
            text: Text to synthesize.

        Returns:
            Audio bytes.
        """
        await asyncio.sleep(0)
        
        result = piper.synthesize_args(
            text=text,
            speaker_id=self.config.speaker_id,
            model_name=self.config.model,
        )

        audio_data = result.get("audio_data", b"")
        sample_rate = result.get("sample_rate", 22050)

        if audio_data and sample_rate:
            duration = len(audio_data) / (sample_rate * 2)
            self._audio_duration_sec += duration

        return audio_data

    async def _synthesize_streaming(
        self, text: str
    ) -> AsyncIterator[bytes]:
        """Synthesize text as streaming audio chunks.

        Args:
            text: Text to synthesize.

        Yields:
            Audio data chunks.
        """
        audio_data = await self._synthesize_to_bytes(text)
        chunk_size = 1024
        for i in range(0, len(audio_data), chunk_size):
            yield audio_data[i : i + chunk_size]
            await asyncio.sleep(0)

    def set_voice(self, voice_id: str) -> None:
        """Set the voice for synthesis.

        Args:
            voice_id: Voice identifier or speaker_id.
        """
        try:
            self.config.speaker_id = int(voice_id)
        except (ValueError, TypeError):
            self.config.speaker_id = voice_id

    def get_available_voices(self) -> List[dict]:
        """Get available voices for the model.

        Returns:
            List of voice dictionaries with id and name.
        """
        voices = [
            {"id": 0, "name": "Default"},
        ]
        return voices

    def get_usage_stats(self) -> dict:
        """Get usage statistics.

        Returns:
            Dictionary with audio_duration_sec, requests, and errors.
        """
        return {
            "audio_duration_sec": self._audio_duration_sec,
            "requests": self._requests,
            "errors": self._errors,
        }
