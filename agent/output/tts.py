"""Text-to-Speech engine interface."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class TTSEngine(ABC):
    """Interface abstrata para motores TTS."""

    @abstractmethod
    async def speak(self, text: str, emotion: str = "neutral") -> None:
        """Sintetiza e reproduz o texto."""
        ...


class DummyTTS(TTSEngine):
    """TTS placeholder que apenas imprime o texto."""

    async def speak(self, text: str, emotion: str = "neutral") -> None:
        logger.info("[TTS:%s] %s", emotion, text)
        print(f"🔊 [{emotion}] {text}")


class EdgeTTS(TTSEngine):
    """Motor TTS usando Microsoft Edge TTS (Online)."""

    def __init__(self, voice: str = "pt-BR-FranciscaNeural") -> None:
        self.voice = voice

    async def speak(self, text: str, emotion: str = "neutral") -> None:
        """Gera áudio e reproduz (usando mpv ou similar, ou apenas salva)."""
        logger.info("[EdgeTTS] Gerando áudio: %s", text)
        
        try:
            import edge_tts
            import os
            import subprocess
            
            communicate = edge_tts.Communicate(text, self.voice)
            output_file = "output.mp3"
            
            await communicate.save(output_file)
            
            # Reproduzir áudio (Cross-platform way is tricky without heavy deps)
            # For Windows (PowerShell/cmd)
            if os.name == 'nt':
                 # Start-Process with hidden window style might be cleaner but os.system is simple
                 # or use a library like playsound (but it blocks).
                 # Ideally we send the audio path or bytes to the frontend? 
                 # But the request was for "speech model base".
                 # Let's try to play it locally for now using standard available tools.
                 # Using a simple powershell command to play audio
                 subprocess.run(
                     ["powershell", "-c", f"(New-Object Media.SoundPlayer '{os.path.abspath(output_file)}').PlaySync()"],
                     check=False
                 )
            else:
                 # MacOS/Linux
                 subprocess.run(["afplay", output_file], check=False) # Mac
                 # subprocess.run(["aplay", output_file], check=False) # Linux (alsa)

        except Exception as e:
            logger.error("Erro no EdgeTTS: %s", e)
            print(f"❌ Erro TTS: {e}")
