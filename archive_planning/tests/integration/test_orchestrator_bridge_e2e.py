"""
End-to-end test: text input → Bridge → EventBus → Brains → response.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock
from agent.orchestrator import AgentOrchestrator
from agent.bridge import OrchestratorBridge
from agent.core.messaging import EventBus, EventType, AgentEvent


class FakeAvatar:
    """Minimal fake avatar for E2E testing."""
    def __init__(self):
        self.commands_sent = []
        self.connected = True
        self.message_callback = None
    
    async def send_command(self, data):
        self.commands_sent.append(data)
    
    async def set_expression(self, name):
        self.commands_sent.append({"type": "set_expression", "expression": name})
    
    async def speak_start(self):
        self.commands_sent.append({"type": "set_speaking", "speaking": True})
    
    async def speak_end(self):
        self.commands_sent.append({"type": "set_speaking", "speaking": False})
    
    def set_message_callback(self, callback):
        self.message_callback = callback


@pytest.mark.asyncio
async def test_orchestrator_bridge_basic_creation():
    """Bridge and Orchestrator can be created and started together."""
    avatar = FakeAvatar()
    
    orchestrator = AgentOrchestrator(
        user_id="test", session_id="test_e2e",
        tts_provider=None,
        llm_provider=None,
    )
    
    bridge = OrchestratorBridge(
        avatar=avatar,
        event_bus=orchestrator.event_bus,
    )
    
    await orchestrator.initialize()
    await orchestrator.start()
    await bridge.start()
    
    assert orchestrator is not None
    assert bridge is not None
    assert avatar is not None
    
    await orchestrator.stop()


@pytest.mark.asyncio
async def test_bridge_translates_text_to_transcription_event():
    """Bridge translates text input to TRANSCRIPTION_COMPLETE EventBus event."""
    avatar = FakeAvatar()
    event_bus = EventBus()
    await event_bus.start()
    
    bridge = OrchestratorBridge(
        avatar=avatar,
        event_bus=event_bus,
    )
    
    captured_events = []
    
    async def capture_transcription(event: AgentEvent):
        captured_events.append(event)
    
    event_bus.subscribe(EventType.TRANSCRIPTION_COMPLETE)(capture_transcription)
    
    await bridge.handle_text_input("Olá Mimi")
    await asyncio.sleep(0.2)
    
    assert len(captured_events) == 1
    assert captured_events[0].payload["transcript"] == "Olá Mimi"
    
    await event_bus.stop()

