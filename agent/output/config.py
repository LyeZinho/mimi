"""TTS configuration dataclasses."""
from dataclasses import dataclass


@dataclass
class TTSConfig:
    """Base configuration for TTS providers."""
    provider: str
    model: str
    timeout_sec: float = 30.0


@dataclass
class PiperConfig(TTSConfig):
    """Configuration for Piper TTS provider."""
    model_path: str = "~/.cache/piper/pt_BR/pt_BR-faber-medium.onnx"
    speaker_id: int = 0
    speed: float = 1.0
    noise_scale: float = 0.667

