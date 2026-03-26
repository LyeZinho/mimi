"""Unit tests for ActionRouter emotion mapping integration."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agent.output.actions import ActionRouter


class TestActionRouterEmotionMapping:
    """Tests for ActionRouter emotion-to-gesture mapping."""

    @pytest.fixture
    def router(self):
        """Provide ActionRouter with mock avatar."""
        avatar_mock = AsyncMock()
        return ActionRouter(tts=AsyncMock(), avatar=avatar_mock)

    @pytest.fixture
    def mock_agent(self):
        """Provide mock AgentCore."""
        agent = MagicMock()
        agent.state.speaking = False
        return agent

    @pytest.mark.asyncio
    async def test_handle_speak_maps_emotion_to_expression(self, router, mock_agent):
        """Test that _handle_speak uses emotion mapper to set expression."""
        intent = {
            "intent": "speak",
            "text": "I'm happy!",
            "emotion": "happy",
        }

        result = await router._handle_speak(intent, mock_agent)

        assert result["status"] == "spoken"
        assert result["text"] == "I'm happy!"
        assert result["emotion"] == "happy"
        assert result["expression"] == "smile"
        assert result["animation"] == "idle_happy"
        assert result["gesture"] == "wave"
        assert result["duration_ms"] == 2000
        
        router.avatar.set_expression.assert_called_once_with("smile")

    @pytest.mark.asyncio
    async def test_handle_speak_fallback_unknown_emotion(self, router, mock_agent):
        """Test that unknown emotion falls back to neutral."""
        intent = {
            "intent": "speak",
            "text": "Hmm...",
            "emotion": "unknown_emotion",
        }

        result = await router._handle_speak(intent, mock_agent)

        assert result["status"] == "spoken"
        assert result["emotion"] == "unknown_emotion"
        assert result["expression"] == "neutral"
        assert result["animation"] == "idle_neutral"
        assert result["gesture"] is None
        assert result["duration_ms"] == 1000

    @pytest.mark.asyncio
    async def test_handle_speak_case_insensitive_emotion(self, router, mock_agent):
        """Test that emotion lookup is case-insensitive."""
        intent = {
            "intent": "speak",
            "text": "I'm excited!",
            "emotion": "EXCITED",
        }

        result = await router._handle_speak(intent, mock_agent)

        assert result["emotion"] == "EXCITED"
        assert result["expression"] == "smile"
        assert result["animation"] == "idle_excited"
        assert result["gesture"] == "jump"

    @pytest.mark.asyncio
    async def test_handle_speak_default_emotion_neutral(self, router, mock_agent):
        """Test that missing emotion defaults to neutral."""
        intent = {
            "intent": "speak",
            "text": "Hello",
        }

        result = await router._handle_speak(intent, mock_agent)

        assert result["emotion"] == "neutral"
        assert result["expression"] == "neutral"

    @pytest.mark.asyncio
    async def test_handle_speak_calls_avatar_methods_in_order(self, router, mock_agent):
        """Test that avatar methods are called in correct order."""
        intent = {
            "intent": "speak",
            "text": "Testing avatar flow",
            "emotion": "happy",
        }

        await router._handle_speak(intent, mock_agent)

        assert router.avatar.set_expression.called
        assert router.avatar.speak_start.called
        assert router.avatar.speak_end.called
        
        call_order = [call[0] for call in router.avatar.method_calls]
        assert call_order == ["set_expression", "speak_start", "speak_end"]

    @pytest.mark.asyncio
    async def test_handle_speak_updates_agent_speaking_state(self, router, mock_agent):
        """Test that agent.state.speaking is toggled correctly."""
        intent = {
            "intent": "speak",
            "text": "Testing state",
            "emotion": "neutral",
        }

        mock_agent.state.speaking = False
        await router._handle_speak(intent, mock_agent)

        assert mock_agent.state.speaking is False

    @pytest.mark.asyncio
    async def test_handle_speak_returns_complete_emotion_data(self, router, mock_agent):
        """Test that result includes all emotion mapping data."""
        intent = {
            "intent": "speak",
            "text": "Complete data test",
            "emotion": "thinking",
        }

        result = await router._handle_speak(intent, mock_agent)

        required_fields = {
            "status",
            "text",
            "emotion",
            "expression",
            "animation",
            "gesture",
            "duration_ms",
        }
        assert required_fields.issubset(set(result.keys()))

    @pytest.mark.asyncio
    async def test_handle_speak_sad_emotion_no_gesture(self, router, mock_agent):
        """Test emotion with null gesture (sad)."""
        intent = {
            "intent": "speak",
            "text": "I'm sad",
            "emotion": "sad",
        }

        result = await router._handle_speak(intent, mock_agent)

        assert result["expression"] == "sad"
        assert result["animation"] == "idle_sad"
        assert result["gesture"] is None
        assert result["duration_ms"] == 1500
