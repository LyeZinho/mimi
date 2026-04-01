"""Unit tests for OrchestratorBridge."""
import asyncio
import pytest
from unittest.mock import Mock, AsyncMock
from agent.core.messaging import EventBus, EventType, AgentEvent


class MockWebAvatar:
    """Mock WebAvatar for testing."""
    def __init__(self):
        self.commands_sent = []
        self.message_callback = None
    
    async def send_command(self, data: dict):
        self.commands_sent.append(data)
    
    async def set_expression(self, name: str):
        self.commands_sent.append({"type": "set_expression", "expression": name})
    
    async def speak_start(self):
        self.commands_sent.append({"type": "set_speaking", "speaking": True})
    
    async def speak_end(self):
        self.commands_sent.append({"type": "set_speaking", "speaking": False})
    
    def set_message_callback(self, callback):
        self.message_callback = callback


@pytest.fixture
async def event_bus():
    bus = EventBus()
    await bus.start()
    yield bus
    await bus.stop()


@pytest.fixture
def mock_avatar():
    return MockWebAvatar()


@pytest.fixture
async def bridge(event_bus, mock_avatar):
    from agent.bridge import OrchestratorBridge
    b = OrchestratorBridge(avatar=mock_avatar, event_bus=event_bus)
    yield b


class TestBridgeInit:
    def test_bridge_creates(self, bridge):
        assert bridge is not None
    
    def test_bridge_has_avatar(self, bridge, mock_avatar):
        assert bridge.avatar is mock_avatar
    
    def test_bridge_has_event_bus(self, bridge, event_bus):
        assert bridge.event_bus is event_bus


class TestBridgeInbound:
    """Test WS message → EventBus event translation."""
    
    @pytest.mark.asyncio
    async def test_text_input_publishes_transcription_complete(self, bridge, event_bus):
        """When bridge receives text input, it publishes TRANSCRIPTION_COMPLETE."""
        await bridge.start()
        
        captured = []
        
        async def capture(event):
            captured.append(event)
        
        event_bus.subscribe(EventType.TRANSCRIPTION_COMPLETE)(capture)
        
        await bridge.handle_text_input("Olá Mimi")
        await asyncio.sleep(0.2)
        
        assert len(captured) == 1
        assert captured[0].payload["transcript"] == "Olá Mimi"
        assert captured[0].payload["confidence"] == 1.0
        assert captured[0].source_brain == "bridge"


class TestBridgeOutbound:
    """Test EventBus event → WS message translation."""
    
    @pytest.mark.asyncio
    async def test_response_ready_sends_agent_response(self, bridge, event_bus, mock_avatar):
        """When RESPONSE_READY fires, bridge sends agent_response via WebAvatar."""
        await bridge.start()
        
        event = AgentEvent(
            type=EventType.RESPONSE_READY,
            source_brain="reasoning_brain",
            payload={"response": "Olá! Como posso ajudar?"}
        )
        await event_bus.publish(event)
        await asyncio.sleep(0.2)
        
        response_cmds = [c for c in mock_avatar.commands_sent if c.get("type") == "agent_response"]
        assert len(response_cmds) == 1
        assert response_cmds[0]["text"] == "Olá! Como posso ajudar?"
    
    @pytest.mark.asyncio
    async def test_animation_queued_sends_avatar_control(self, bridge, event_bus, mock_avatar):
        """When ANIMATION_QUEUED fires, bridge sends avatar_control via WebAvatar."""
        await bridge.start()
        
        event = AgentEvent(
            type=EventType.ANIMATION_QUEUED,
            source_brain="avatar_brain",
            payload={"animation": "smile", "sentiment": "happy"}
        )
        await event_bus.publish(event)
        await asyncio.sleep(0.2)
        
        ctrl_cmds = [c for c in mock_avatar.commands_sent if c.get("type") == "avatar_control"]
        assert len(ctrl_cmds) == 1
        assert ctrl_cmds[0]["emotion"] == "happy"
    
    @pytest.mark.asyncio
    async def test_tts_started_calls_speak_start(self, bridge, event_bus, mock_avatar):
        """When TTS_STARTED fires, bridge calls speak_start."""
        await bridge.start()
        
        event = AgentEvent(
            type=EventType.TTS_STARTED,
            source_brain="output_brain",
            payload={"text": "Hello"}
        )
        await event_bus.publish(event)
        await asyncio.sleep(0.2)
        
        speak_cmds = [c for c in mock_avatar.commands_sent if c.get("type") == "set_speaking" and c.get("speaking")]
        assert len(speak_cmds) == 1
    
    @pytest.mark.asyncio
    async def test_audio_complete_calls_speak_end(self, bridge, event_bus, mock_avatar):
        """When AUDIO_COMPLETE fires, bridge calls speak_end."""
        await bridge.start()
        
        event = AgentEvent(
            type=EventType.AUDIO_COMPLETE,
            source_brain="output_brain",
            payload={"audio": b"", "duration_ms": 100}
        )
        await event_bus.publish(event)
        await asyncio.sleep(0.2)
        
        speak_cmds = [c for c in mock_avatar.commands_sent if c.get("type") == "set_speaking" and not c.get("speaking")]
        assert len(speak_cmds) == 1
