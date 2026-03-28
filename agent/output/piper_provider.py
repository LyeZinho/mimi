"""Piper TTS provider implementation."""
import asyncio
import io
from pathlib import Path
from typing import List, Union, AsyncIterator
from agent.output.config import PiperConfig
from agent.output.tts_provider import TTSProvider

try:
    from piper.voice import PiperVoice, PiperConfig as PiperVoiceConfig, SynthesisConfig
    import wave
except ImportError:
    PiperVoice = None
    PiperVoiceConfig = None
    SynthesisConfig = None
    wave = None


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
        if PiperVoice is None:
            raise ImportError(
                "piper library is required. "
                "Install with: pip install piper-tts"
            )
        self._requests = 0
        self._errors = 0
        self._audio_duration_sec = 0.0
        self._voice = None

    def _load_voice(self) -> PiperVoice:
        """Lazy load the Piper voice model."""
        if self._voice is None:
            model_path = Path(self.config.model_path).expanduser()
            self._voice = PiperVoice.load(str(model_path))
        return self._voice

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
            Audio bytes (WAV format).
        """
        await asyncio.sleep(0)
        
        try:
            voice = self._load_voice()
            
            syn_config = SynthesisConfig(
                speaker_id=self.config.speaker_id,
                length_scale=1.0 / self.config.speed if self.config.speed else 1.0,
            )
            
            audio_chunks = []
            sample_rate = 22050
            
            for audio_chunk in voice.synthesize(text, syn_config):
                audio_chunks.append(audio_chunk.audio_int16_bytes)
                sample_rate = audio_chunk.sample_rate
            
            if not audio_chunks:
                return b""
            
            audio_data = b"".join(audio_chunks)
            
            if audio_data and sample_rate:
                duration = len(audio_data) / (sample_rate * 2)
                self._audio_duration_sec += duration
            
            return audio_data
            
        except Exception as e:
            raise RuntimeError(f"Piper synthesis error: {str(e)}") from e

    async def _synthesize_streaming(
        self, text: str
    ) -> AsyncIterator[bytes]:
        """Synthesize text as streaming audio chunks.

        Args:
            text: Text to synthesize.

        Yields:
            Audio data chunks (bytes).
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
