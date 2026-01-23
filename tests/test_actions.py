"""Tests for ActionRouter."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from agent.output.actions import ActionRouter
from agent.core.agent import AgentCore

@pytest.fixture
def mock_agent():
    agent = MagicMock(spec=AgentCore)
    agent.state = MagicMock()
    agent.update_state = MagicMock()
    return agent

@pytest.fixture
def action_router():
    tts = AsyncMock()
    return ActionRouter(tts=tts)

@pytest.mark.asyncio
async def test_handle_speak(action_router, mock_agent):
    intent = {"intent": "speak", "text": "Hello world", "emotion": "happy"}
    result = await action_router.execute(intent, mock_agent)
    
    assert result["status"] == "spoken"
    assert result["text"] == "Hello world"
    action_router.tts.speak.assert_called_once_with("Hello world", "happy")
    # Verify speaking state toggled
    assert mock_agent.state.speaking is False

@pytest.mark.asyncio
async def test_handle_change_state(action_router, mock_agent):
    intent = {"intent": "change_state", "target": "mood", "value": "excited"}
    result = await action_router.execute(intent, mock_agent)
    
    assert result["status"] == "state_changed"
    assert result["target"] == "mood"
    assert result["value"] == "excited"
    mock_agent.update_state.assert_called_once_with("mood", "excited")

@pytest.mark.asyncio
async def test_handle_unknown(action_router, mock_agent):
    intent = {"intent": "fly_to_moon"}
    result = await action_router.execute(intent, mock_agent)
    
    assert result["status"] == "unknown_intent"
    assert result["intent"] == intent
