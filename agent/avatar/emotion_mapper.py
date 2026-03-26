"""
Emotion-to-gesture mapping system for avatar expressions and animations.

Maps emotion strings to avatar gestures, expressions, animations, and durations
based on configurable JSON schema. Supports case-insensitive lookups with fallback.
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class EmotionMapper:
    """Maps emotion strings to avatar behavior configurations.
    
    Loads emotion-to-gesture mappings from a JSON config file and provides
    methods to look up avatar behavior for a given emotion. Supports fallback
    to neutral emotion for unmapped emotions.
    
    Example config (emotion_map.json):
        {
            "version": "1.0",
            "emotions": {
                "happy": {
                    "expression": "smile",
                    "animation": "idle_happy",
                    "gesture": "wave",
                    "duration_ms": 2000
                }
            },
            "fallback_emotion": "neutral"
        }
    """

    def __init__(self, config_path: Path | str = "data/emotion_map.json") -> None:
        """Initialize EmotionMapper with config file.
        
        Args:
            config_path: Path to emotion map JSON file. Defaults to data/emotion_map.json.
                        If path is relative, it's resolved from current working directory.
        
        Raises:
            FileNotFoundError: If config file does not exist.
            json.JSONDecodeError: If config file is invalid JSON.
            KeyError: If required keys missing from config.
        """
        self.config_path = Path(config_path)
        self._config: dict[str, Any] = {}
        self._emotions: dict[str, dict[str, Any]] = {}
        self._fallback_emotion: str = "neutral"
        
        self.reload()
        logger.info(
            f"EmotionMapper initialized with {len(self._emotions)} emotions. "
            f"Fallback: {self._fallback_emotion}"
        )

    def reload(self) -> None:
        """Reload emotion map configuration from disk.
        
        Called automatically on init, but can be called manually to pick up
        changes to the config file without restarting.
        
        Raises:
            FileNotFoundError: If config file does not exist.
            json.JSONDecodeError: If config file is invalid JSON.
            KeyError: If required keys missing from config.
        """
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Emotion map config not found: {self.config_path.absolute()}"
            )

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._config = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {self.config_path}: {e}")
            raise

        # Validate required keys
        if "emotions" not in self._config:
            raise KeyError("'emotions' key missing from emotion map config")

        # Load emotions (lowercase keys for case-insensitive lookup)
        self._emotions = {
            emotion.lower(): config
            for emotion, config in self._config["emotions"].items()
        }

        # Set fallback emotion
        self._fallback_emotion = self._config.get("fallback_emotion", "neutral")
        if self._fallback_emotion.lower() not in self._emotions:
            logger.warning(
                f"Fallback emotion '{self._fallback_emotion}' not found in emotions. "
                f"Defaulting to 'neutral'"
            )
            self._fallback_emotion = "neutral"

        logger.info(
            f"Reloaded emotion map: {len(self._emotions)} emotions "
            f"(fallback: {self._fallback_emotion})"
        )

    def map_emotion(self, emotion: str) -> dict[str, Any]:
        """Map emotion string to avatar behavior configuration.
        
        Returns a dict with keys: expression, animation, gesture (or null),
        and duration_ms. Lookups are case-insensitive. If emotion not found,
        returns fallback emotion (neutral).
        
        Args:
            emotion: Emotion name (e.g., "happy", "HAPPY", "Confused")
        
        Returns:
            dict with keys: expression, animation, gesture, duration_ms
            
        Example:
            >>> mapper = EmotionMapper()
            >>> mapper.map_emotion("happy")
            {
                "expression": "smile",
                "animation": "idle_happy",
                "gesture": "wave",
                "duration_ms": 2000
            }
        """
        emotion_lower = emotion.lower().strip()

        # Try exact match first
        if emotion_lower in self._emotions:
            result = self._emotions[emotion_lower]
            logger.debug(f"Emotion '{emotion}' mapped to {result}")
            return result

        # Fall back to neutral
        logger.warning(
            f"Unknown emotion '{emotion}'. Using fallback: {self._fallback_emotion}"
        )
        result = self._emotions[self._fallback_emotion.lower()]
        return result

    def list_emotions(self) -> list[str]:
        """Return sorted list of available emotions.
        
        Returns:
            Sorted list of emotion names (lowercase).
            
        Example:
            >>> mapper = EmotionMapper()
            >>> mapper.list_emotions()
            ['confused', 'excited', 'happy', 'neutral', 'sad', 'thinking']
        """
        return sorted(self._emotions.keys())

    def get_fallback_emotion(self) -> str:
        """Return current fallback emotion name.
        
        Returns:
            Name of emotion used when unmapped emotion is requested.
        """
        return self._fallback_emotion.lower()

    def validate_emotion_config(self, emotion_dict: dict[str, Any]) -> bool:
        """Validate that emotion dict has required keys.
        
        Args:
            emotion_dict: Emotion config dict to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_keys = {"expression", "animation", "duration_ms"}
        optional_keys = {"gesture"}
        allowed_keys = required_keys | optional_keys

        # Check required keys
        if not required_keys.issubset(emotion_dict.keys()):
            missing = required_keys - set(emotion_dict.keys())
            logger.error(f"Emotion config missing required keys: {missing}")
            return False

        # Check no unexpected keys
        unexpected = set(emotion_dict.keys()) - allowed_keys
        if unexpected:
            logger.warning(f"Emotion config has unexpected keys: {unexpected}")

        # Type validation
        if not isinstance(emotion_dict.get("expression"), str):
            logger.error("'expression' must be string")
            return False
        if not isinstance(emotion_dict.get("animation"), str):
            logger.error("'animation' must be string")
            return False
        if not isinstance(emotion_dict.get("duration_ms"), int):
            logger.error("'duration_ms' must be integer")
            return False

        # gesture can be string or null
        gesture = emotion_dict.get("gesture")
        if gesture is not None and not isinstance(gesture, str):
            logger.error("'gesture' must be string or null")
            return False

        return True
