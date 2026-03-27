"""VAD (Voice Activity Detection) engine using energy-based detection."""

import numpy as np
import logging

logger = logging.getLogger(__name__)


class VADEngine:
    """Voice Activity Detection using energy-based method."""
    
    def __init__(self, aggressiveness: int = 2, sample_rate: int = 16000):
        """
        Initialize VAD engine.
        
        Args:
            aggressiveness: 0-3, higher = more aggressive filtering (default 2 is balanced)
            sample_rate: Audio sample rate (must be 8000, 16000, or 32000)
        """
        self.aggressiveness = max(0, min(3, aggressiveness))
        self.sample_rate = sample_rate
        self.frame_duration_ms = 20
        self.frame_size = int(self.sample_rate * self.frame_duration_ms / 1000)
        
        self.thresholds = [50, 100, 150, 200]
        self.threshold = self.thresholds[self.aggressiveness]
    
    def is_speech(self, audio_bytes: bytes) -> bool:
        """
        Detect if audio frame contains speech using energy-based method.
        
        Args:
            audio_bytes: Raw audio bytes (16-bit PCM)
            
        Returns:
            True if speech detected, False otherwise
        """
        try:
            audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
            
            if len(audio) < 2:
                return False
            
            energy = np.sqrt(np.mean(audio ** 2))
            is_active = energy > self.threshold
            
            return is_active
        except Exception as e:
            logger.error(f"VAD error: {e}")
            return False
    
    def get_frame_size(self) -> int:
        """Get required frame size in bytes for this VAD engine."""
        return self.frame_size * 2
