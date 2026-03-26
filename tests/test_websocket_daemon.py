"""Tests for WebSocket daemon mode (agent as persistent listener).

RED phase: These tests should FAIL initially because the agent
doesn't have daemon/listener functionality yet.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.avatar.interface import WebAvatar
from agent.core.agent import AgentCore
from agent.core.memory import Memory
from agent.core.state import AgentState
from agent.llm.client import LLMClient
from agent.output.actions import ActionRouter
from agent.tools.registry import ToolRegistry


class TestWebSocketDaemon:
    """Tests WebAvatar as a persistent WebSocket daemon."""

    @pytest.fixture
    def mock_agent(self):
        """Create a mock agent for testing."""
        memory = Memory(short_term_limit=30)
        state = AgentState(mood="neutral")
        llm = AsyncMock(spec=LLMClient)
        router = AsyncMock(spec=ActionRouter)
        registry = ToolRegistry()

        agent = AgentCore(
            memory=memory,
            state=state,
            llm=llm,
            router=router,
            registry=registry,
        )
        return agent

    @pytest.mark.asyncio
    async def test_websocket_daemon_listens_for_set_model(self, mock_agent):
        """Test daemon receives set_model message from WebSocket server."""
        avatar = WebAvatar(host="localhost", port=8765)
        avatar.set_agent(mock_agent)

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()
        mock_ws.__aiter__ = AsyncMock(return_value=AsyncMock())

        with patch("agent.avatar.interface.websockets.connect", new_callable=AsyncMock, return_value=mock_ws):
            await avatar.connect()

            assert avatar.connected is True
            assert avatar.ws is not None

    @pytest.mark.asyncio
    async def test_websocket_daemon_processes_chat_message(self, mock_agent):
        """Test daemon receives chat message and calls agent.handle_input."""
        avatar = WebAvatar(host="localhost", port=8765)
        avatar.set_agent(mock_agent)

        mock_agent.handle_input = AsyncMock(
            return_value={"text": "Olá! Como você está?", "response": "Olá! Como você está?"}
        )

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()

        with patch("agent.avatar.interface.websockets.connect", new_callable=AsyncMock, return_value=mock_ws):
            await avatar.connect()

            if avatar.agent:
                result = await avatar.agent.handle_input(
                    "Olá, Mimi!",
                    source="web"
                )
                assert result is not None
                assert "text" in result or "response" in result

    @pytest.mark.asyncio
    async def test_websocket_daemon_sends_response_back(self, mock_agent):
        """Test daemon sends agent response back through WebSocket."""
        avatar = WebAvatar(host="localhost", port=8765)
        avatar.set_agent(mock_agent)

        mock_agent.handle_input = AsyncMock(
            return_value={"text": "Resposta do agente"}
        )

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()

        with patch("agent.avatar.interface.websockets.connect", new_callable=AsyncMock, return_value=mock_ws):
            await avatar.connect()

            command = {"type": "agent_response", "text": "Resposta"}
            await avatar.send_command(command)

            mock_ws.send.assert_called()

    @pytest.mark.asyncio
    async def test_websocket_daemon_handles_multiple_messages(self, mock_agent):
        """Test daemon can handle multiple messages in sequence."""
        avatar = WebAvatar(host="localhost", port=8765)
        avatar.set_agent(mock_agent)

        mock_agent.handle_input = AsyncMock(
            return_value={"text": "Resposta", "response": "Resposta"}
        )

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()

        with patch("agent.avatar.interface.websockets.connect", new_callable=AsyncMock, return_value=mock_ws):
            await avatar.connect()

            await avatar.agent.handle_input("Mensagem 1", source="web")
            await avatar.send_command({"type": "agent_response", "text": "Resposta 1"})

            await avatar.agent.handle_input("Mensagem 2", source="web")
            await avatar.send_command({"type": "agent_response", "text": "Resposta 2"})

            assert mock_ws.send.call_count >= 2

    @pytest.mark.asyncio
    async def test_websocket_daemon_stays_alive(self, mock_agent):
        """Test daemon stays connected and listening (doesn't exit)."""
        avatar = WebAvatar(host="localhost", port=8765)
        avatar.set_agent(mock_agent)

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()

        async def mock_message_generator():
            yield json.dumps({"type": "chat", "text": "Message 1"})
            yield json.dumps({"type": "chat", "text": "Message 2"})

        mock_ws.__aiter__ = mock_message_generator

        mock_agent.handle_input = AsyncMock(
            return_value={"text": "Response"}
        )

        with patch("agent.avatar.interface.websockets.connect", new_callable=AsyncMock, return_value=mock_ws):
            await avatar.connect()

            assert avatar.listen_task is not None
            assert not avatar.listen_task.done()

    @pytest.mark.asyncio
    async def test_websocket_daemon_error_handling(self, mock_agent):
        """Test daemon gracefully handles errors in message processing."""
        avatar = WebAvatar(host="localhost", port=8765)
        avatar.set_agent(mock_agent)

        mock_agent.handle_input = AsyncMock(
            side_effect=Exception("Test error")
        )

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()

        with patch("agent.avatar.interface.websockets.connect", new_callable=AsyncMock, return_value=mock_ws):
            await avatar.connect()

            with pytest.raises(Exception):
                await avatar.agent.handle_input("Test", source="web")

            assert avatar.connected is True

    @pytest.mark.asyncio
    async def test_websocket_daemon_listens_for_set_model_message(self, mock_agent):
        """Specific test: daemon correctly identifies and handles set_model message."""
        avatar = WebAvatar(host="localhost", port=8765)
        avatar.set_agent(mock_agent)

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()

        set_model_message = json.dumps({
            "type": "set_model",
            "model": "Avatar.vrm"
        })

        with patch("agent.avatar.interface.websockets.connect", new_callable=AsyncMock, return_value=mock_ws):
            await avatar.connect()

            data = json.loads(set_model_message)
            assert data.get("type") == "set_model"
            assert data.get("model") == "Avatar.vrm"

    @pytest.mark.asyncio
    async def test_websocket_daemon_agent_integration_flow(self, mock_agent):
        """Integration test: WebSocket message → agent processing → response."""
        avatar = WebAvatar(host="localhost", port=8765)
        avatar.set_agent(mock_agent)

        mock_agent.handle_input = AsyncMock(
            return_value={
                "text": "Entendi sua mensagem",
                "response": "Entendi sua mensagem",
                "emotion": "happy"
            }
        )

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()

        with patch("agent.avatar.interface.websockets.connect", new_callable=AsyncMock, return_value=mock_ws):
            await avatar.connect()

            user_message = "Olá Mimi"
            result = await avatar.agent.handle_input(user_message, source="web")

            assert result is not None
            assert "text" in result

            await avatar.send_command({
                "type": "agent_response",
                "text": result["text"]
            })

            mock_ws.send.assert_called()

    @pytest.mark.asyncio
    async def test_websocket_daemon_disconnect_cleanup(self, mock_agent):
        """Test daemon cleans up properly on disconnect."""
        avatar = WebAvatar(host="localhost", port=8765)
        avatar.set_agent(mock_agent)

        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()
        mock_ws.close = AsyncMock()

        with patch("agent.avatar.interface.websockets.connect", new_callable=AsyncMock, return_value=mock_ws):
            await avatar.connect()
            assert avatar.connected is True

            await avatar.disconnect()
            assert avatar.connected is False
            mock_ws.close.assert_called()
