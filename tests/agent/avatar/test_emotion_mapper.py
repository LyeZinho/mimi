"""Unit tests for EmotionMapper emotion-to-gesture mapping system."""

import json
import tempfile
from pathlib import Path

import pytest

from agent.avatar.emotion_mapper import EmotionMapper


class TestEmotionMapperInit:
    """Tests for EmotionMapper initialization."""

    def test_init_loads_default_config(self, tmp_path):
        """Test that EmotionMapper loads config file on init."""
        config_path = tmp_path / "emotions.json"
        config_path.write_text(
            json.dumps(
                {
                    "version": "1.0",
                    "emotions": {
                        "happy": {
                            "expression": "smile",
                            "animation": "idle_happy",
                            "gesture": "wave",
                            "duration_ms": 2000,
                        },
                        "neutral": {
                            "expression": "neutral",
                            "animation": "idle",
                            "gesture": None,
                            "duration_ms": 1000,
                        },
                    },
                    "fallback_emotion": "neutral",
                }
            )
        )

        mapper = EmotionMapper(config_path)
        assert len(mapper.list_emotions()) == 2
        assert "happy" in mapper.list_emotions()
        assert "neutral" in mapper.list_emotions()

    def test_init_raises_on_missing_file(self):
        """Test that EmotionMapper raises FileNotFoundError if config missing."""
        with pytest.raises(FileNotFoundError):
            EmotionMapper("/nonexistent/path/emotions.json")

    def test_init_raises_on_invalid_json(self, tmp_path):
        """Test that EmotionMapper raises JSONDecodeError on invalid JSON."""
        config_path = tmp_path / "emotions.json"
        config_path.write_text("{ invalid json }")

        with pytest.raises(json.JSONDecodeError):
            EmotionMapper(config_path)

    def test_init_raises_on_missing_emotions_key(self, tmp_path):
        """Test that EmotionMapper raises KeyError if 'emotions' key missing."""
        config_path = tmp_path / "emotions.json"
        config_path.write_text(json.dumps({"version": "1.0"}))

        with pytest.raises(KeyError):
            EmotionMapper(config_path)


class TestEmotionMapperMapping:
    """Tests for emotion mapping functionality."""

    @pytest.fixture
    def mapper(self, tmp_path):
        """Provide configured EmotionMapper for tests."""
        config_path = tmp_path / "emotions.json"
        config_path.write_text(
            json.dumps(
                {
                    "version": "1.0",
                    "emotions": {
                        "happy": {
                            "expression": "smile",
                            "animation": "idle_happy",
                            "gesture": "wave",
                            "duration_ms": 2000,
                        },
                        "sad": {
                            "expression": "frown",
                            "animation": "idle_sad",
                            "gesture": None,
                            "duration_ms": 1500,
                        },
                        "confused": {
                            "expression": "uncertain",
                            "animation": "idle_confused",
                            "gesture": "head_tilt",
                            "duration_ms": 2000,
                        },
                        "neutral": {
                            "expression": "neutral",
                            "animation": "idle",
                            "gesture": None,
                            "duration_ms": 1000,
                        },
                    },
                    "fallback_emotion": "neutral",
                }
            )
        )
        return EmotionMapper(config_path)

    def test_map_emotion_happy(self, mapper):
        """Test mapping happy emotion returns correct config."""
        result = mapper.map_emotion("happy")
        assert result["expression"] == "smile"
        assert result["animation"] == "idle_happy"
        assert result["gesture"] == "wave"
        assert result["duration_ms"] == 2000

    def test_map_emotion_sad(self, mapper):
        """Test mapping sad emotion with null gesture."""
        result = mapper.map_emotion("sad")
        assert result["expression"] == "frown"
        assert result["animation"] == "idle_sad"
        assert result["gesture"] is None
        assert result["duration_ms"] == 1500

    def test_map_emotion_case_insensitive_uppercase(self, mapper):
        """Test that emotion mapping is case-insensitive (uppercase)."""
        result = mapper.map_emotion("HAPPY")
        assert result["expression"] == "smile"

    def test_map_emotion_case_insensitive_mixed(self, mapper):
        """Test that emotion mapping is case-insensitive (mixed case)."""
        result = mapper.map_emotion("CoNfUsEd")
        assert result["expression"] == "uncertain"

    def test_map_emotion_case_insensitive_with_spaces(self, mapper):
        """Test that emotion mapping strips whitespace."""
        result = mapper.map_emotion("  happy  ")
        assert result["expression"] == "smile"

    def test_map_emotion_unknown_uses_fallback(self, mapper):
        """Test that unknown emotion returns fallback (neutral)."""
        result = mapper.map_emotion("unknown_emotion")
        assert result["expression"] == "neutral"
        assert result["animation"] == "idle"

    def test_map_emotion_empty_string_uses_fallback(self, mapper):
        """Test that empty string emotion uses fallback."""
        result = mapper.map_emotion("")
        assert result["expression"] == "neutral"


class TestEmotionMapperList:
    """Tests for listing available emotions."""

    @pytest.fixture
    def mapper(self, tmp_path):
        """Provide configured EmotionMapper for tests."""
        config_path = tmp_path / "emotions.json"
        config_path.write_text(
            json.dumps(
                {
                    "version": "1.0",
                    "emotions": {
                        "happy": {
                            "expression": "smile",
                            "animation": "idle_happy",
                            "gesture": None,
                            "duration_ms": 2000,
                        },
                        "sad": {
                            "expression": "frown",
                            "animation": "idle_sad",
                            "gesture": None,
                            "duration_ms": 1500,
                        },
                        "neutral": {
                            "expression": "neutral",
                            "animation": "idle",
                            "gesture": None,
                            "duration_ms": 1000,
                        },
                    },
                    "fallback_emotion": "neutral",
                }
            )
        )
        return EmotionMapper(config_path)

    def test_list_emotions_returns_sorted_list(self, mapper):
        """Test that list_emotions returns sorted list of emotions."""
        emotions = mapper.list_emotions()
        assert emotions == ["happy", "neutral", "sad"]

    def test_list_emotions_not_empty(self, mapper):
        """Test that list_emotions returns non-empty list."""
        emotions = mapper.list_emotions()
        assert len(emotions) == 3

    def test_list_emotions_all_lowercase(self, mapper):
        """Test that all emotions in list are lowercase."""
        emotions = mapper.list_emotions()
        assert all(e == e.lower() for e in emotions)


class TestEmotionMapperReload:
    """Tests for reloading emotion map configuration."""

    def test_reload_picks_up_config_changes(self, tmp_path):
        """Test that reload() picks up changes to config file."""
        config_path = tmp_path / "emotions.json"

        # Write initial config
        initial_config = {
            "version": "1.0",
            "emotions": {
                "happy": {
                    "expression": "smile",
                    "animation": "idle_happy",
                    "gesture": None,
                    "duration_ms": 2000,
                },
                "neutral": {
                    "expression": "neutral",
                    "animation": "idle",
                    "gesture": None,
                    "duration_ms": 1000,
                },
            },
            "fallback_emotion": "neutral",
        }
        config_path.write_text(json.dumps(initial_config))
        mapper = EmotionMapper(config_path)
        assert len(mapper.list_emotions()) == 2

        # Modify config
        updated_config = initial_config.copy()
        updated_config["emotions"]["excited"] = {
            "expression": "smile",
            "animation": "idle_excited",
            "gesture": "jump",
            "duration_ms": 2500,
        }
        config_path.write_text(json.dumps(updated_config))

        # Reload and verify
        mapper.reload()
        assert len(mapper.list_emotions()) == 3
        assert "excited" in mapper.list_emotions()

    def test_reload_raises_on_invalid_json(self, tmp_path):
        """Test that reload raises JSONDecodeError on invalid JSON."""
        config_path = tmp_path / "emotions.json"
        config_path.write_text(
            json.dumps(
                {
                    "version": "1.0",
                    "emotions": {
                        "happy": {
                            "expression": "smile",
                            "animation": "idle_happy",
                            "gesture": None,
                            "duration_ms": 2000,
                        },
                        "neutral": {
                            "expression": "neutral",
                            "animation": "idle",
                            "gesture": None,
                            "duration_ms": 1000,
                        },
                    },
                    "fallback_emotion": "neutral",
                }
            )
        )
        mapper = EmotionMapper(config_path)

        # Corrupt file
        config_path.write_text("{ invalid json }")

        with pytest.raises(json.JSONDecodeError):
            mapper.reload()


class TestEmotionMapperFallback:
    """Tests for fallback emotion behavior."""

    def test_get_fallback_emotion(self, tmp_path):
        """Test get_fallback_emotion returns current fallback."""
        config_path = tmp_path / "emotions.json"
        config_path.write_text(
            json.dumps(
                {
                    "version": "1.0",
                    "emotions": {
                        "happy": {
                            "expression": "smile",
                            "animation": "idle_happy",
                            "gesture": None,
                            "duration_ms": 2000,
                        },
                        "neutral": {
                            "expression": "neutral",
                            "animation": "idle",
                            "gesture": None,
                            "duration_ms": 1000,
                        },
                    },
                    "fallback_emotion": "neutral",
                }
            )
        )
        mapper = EmotionMapper(config_path)
        assert mapper.get_fallback_emotion() == "neutral"


class TestEmotionMapperValidation:
    """Tests for emotion config validation."""

    @pytest.fixture
    def mapper(self, tmp_path):
        """Provide configured EmotionMapper for tests."""
        config_path = tmp_path / "emotions.json"
        config_path.write_text(
            json.dumps(
                {
                    "version": "1.0",
                    "emotions": {
                        "neutral": {
                            "expression": "neutral",
                            "animation": "idle",
                            "gesture": None,
                            "duration_ms": 1000,
                        },
                    },
                    "fallback_emotion": "neutral",
                }
            )
        )
        return EmotionMapper(config_path)

    def test_validate_emotion_config_valid(self, mapper):
        """Test validate_emotion_config accepts valid config."""
        valid_config = {
            "expression": "smile",
            "animation": "idle_happy",
            "gesture": "wave",
            "duration_ms": 2000,
        }
        assert mapper.validate_emotion_config(valid_config) is True

    def test_validate_emotion_config_null_gesture(self, mapper):
        """Test validate_emotion_config accepts null gesture."""
        valid_config = {
            "expression": "smile",
            "animation": "idle_happy",
            "gesture": None,
            "duration_ms": 2000,
        }
        assert mapper.validate_emotion_config(valid_config) is True

    def test_validate_emotion_config_missing_expression(self, mapper):
        """Test validate_emotion_config rejects missing expression."""
        invalid_config = {
            "animation": "idle_happy",
            "gesture": "wave",
            "duration_ms": 2000,
        }
        assert mapper.validate_emotion_config(invalid_config) is False

    def test_validate_emotion_config_invalid_duration_type(self, mapper):
        """Test validate_emotion_config rejects non-integer duration."""
        invalid_config = {
            "expression": "smile",
            "animation": "idle_happy",
            "gesture": "wave",
            "duration_ms": "2000",
        }
        assert mapper.validate_emotion_config(invalid_config) is False

    def test_validate_emotion_config_invalid_gesture_type(self, mapper):
        """Test validate_emotion_config rejects invalid gesture type."""
        invalid_config = {
            "expression": "smile",
            "animation": "idle_happy",
            "gesture": 123,
            "duration_ms": 2000,
        }
        assert mapper.validate_emotion_config(invalid_config) is False
