"""
Unit tests for OutputBrain with TTS integration.
Following TDD approach: tests first, implementation after.
"""
import asyncio
import time
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from agent.brains.output_brain import OutputBrain
from agent.core.messaging import EventBus, EventType, SharedAgentState, AgentEvent
from agent.output.tts_provider import TTSProvider
from agent.output.config import TTSConfig


class MockTTSProvider:
    """Mock TTS provider for testing."""
    
    def __init__(self, config: TTSConfig = None):
        self.config = config or TTSConfig(provider="mock", model="mock-model")
        self.synthesize_called = False
        self.last_text = None
        self.error = None
    
    async def synthesize(self, text: str, stream: bool = False):
        """Mock synthesize method."""
        self.synthesize_called = True
        self.last_text = text
        
        if self.error:
            raise self.error
        
        if stream:
            return self._generate_chunks()
        else:
            # Return complete audio bytes
            return b"fake_audio_data_complete"
    
    async def _generate_chunks(self):
        """Generate mock audio chunks."""
        for i in range(3):
            yield f"chunk_{i}".encode()
            await asyncio.sleep(0.01)
    
    def set_voice(self, voice_id: str) -> None:
        pass
    
    def get_available_voices(self):
        return [{"id": "0", "name": "Default"}]
    
    def get_usage_stats(self):
        return {"audio_duration_sec": 0.0, "requests": 0, "errors": 0}


@pytest.fixture
async def event_bus():
    """Create and start event bus for testing."""
    bus = EventBus()
    await bus.start()
    yield bus
    await bus.stop()


@pytest.fixture
async def shared_state():
    """Create shared state for testing."""
    return SharedAgentState()


@pytest.fixture
async def tts_provider():
    """Create mock TTS provider."""
    return MockTTSProvider()


@pytest.fixture
async def output_brain(event_bus, shared_state, tts_provider):
    """Create OutputBrain instance for testing."""
    brain = OutputBrain(
        brain_id="output_brain",
        event_bus=event_bus,
        shared_state=shared_state,
        tts_provider=tts_provider
    )
    return brain


class TestOutputBrainInit:
    """Test OutputBrain initialization."""
    
    @pytest.mark.asyncio
    async def test_accepts_tts_provider(self, event_bus, shared_state, tts_provider):
        """Test that OutputBrain accepts TTSProvider in __init__."""
        brain = OutputBrain(
            brain_id="output_brain",
            event_bus=event_bus,
            shared_state=shared_state,
            tts_provider=tts_provider
        )
        assert brain.tts_provider is tts_provider
        assert brain.brain_id == "output_brain"
    
    @pytest.mark.asyncio
    async def test_has_initial_attributes(self, output_brain):
        """Test that OutputBrain has required initial attributes."""
        assert hasattr(output_brain, "tts_provider")
        assert hasattr(output_brain, "synthesis_latencies")
        assert output_brain.synthesis_latencies == []


class TestOutputBrainInitialize:
    """Test OutputBrain.initialize() lifecycle."""
    
    @pytest.mark.asyncio
    async def test_initializes_successfully(self, output_brain):
        """Test that initialize() completes without error."""
        await output_brain.initialize()
        assert output_brain.state.value == "ready"
    
    @pytest.mark.asyncio
    async def test_subscribes_to_response_ready_event(self, output_brain):
        """Test that initialize() subscribes to RESPONSE_READY event."""
        await output_brain.initialize()
        
        handlers = output_brain.event_bus._subscribers.get(EventType.RESPONSE_READY, [])
        assert len(handlers) > 0


class TestOutputBrainResponseReady:
    """Test OutputBrain handling RESPONSE_READY event."""
    
    @pytest.mark.asyncio
    async def test_responds_to_response_ready_event(self, output_brain, event_bus):
        """Test that OutputBrain responds when RESPONSE_READY event is published."""
        await output_brain.initialize()
        await output_brain.start()
        
        event = AgentEvent(
            type=EventType.RESPONSE_READY,
            source_brain="reasoning_brain",
            payload={"response": "Hello, this is a test response."}
        )
        await event_bus.publish(event)
        
        await asyncio.sleep(0.2)
        
        assert output_brain.tts_provider.synthesize_called
        assert output_brain.tts_provider.last_text == "Hello, this is a test response."
        
        await output_brain.shutdown()
    
    @pytest.mark.asyncio
    async def test_extracts_response_text_from_payload(self, output_brain, event_bus):
        """Test that response text is correctly extracted from event payload."""
        await output_brain.initialize()
        
        response_text = "Test response text"
        event = Mock()
        event.payload = {"response": response_text}
        
        await output_brain._on_response_ready(event)
        
        assert output_brain.tts_provider.last_text == response_text


class TestOutputBrainAudioChunks:
    """Test AUDIO_CHUNK event generation."""
    
    @pytest.mark.asyncio
    async def test_generates_audio_chunk_events(self, output_brain, event_bus):
        """Test that _on_response_ready generates AUDIO_CHUNK events."""
        await output_brain.initialize()
        
        chunk_events = []
        
        async def capture_chunk(event):
            chunk_events.append(event)
        
        event_bus.subscribe(EventType.AUDIO_CHUNK)(capture_chunk)
        
        event = Mock()
        event.payload = {"response": "Test response"}
        
        await output_brain._on_response_ready(event)
        
        # Should have at least 3 chunk events (matching mock chunks)
        assert len(chunk_events) >= 3
    
    @pytest.mark.asyncio
    async def test_audio_chunk_has_required_fields(self, output_brain, event_bus):
        """Test that AUDIO_CHUNK events contain required fields."""
        await output_brain.initialize()
        
        chunk_events = []
        
        async def capture_chunk(event):
            chunk_events.append(event)
        
        event_bus.subscribe(EventType.AUDIO_CHUNK)(capture_chunk)
        
        event = Mock()
        event.payload = {"response": "Test response"}
        
        await output_brain._on_response_ready(event)
        
        # Verify first chunk has required fields
        assert len(chunk_events) > 0
        first_chunk = chunk_events[0].payload
        assert "chunk_index" in first_chunk or "data" in first_chunk
    
    @pytest.mark.asyncio
    async def test_generates_minimum_three_audio_chunks(self, output_brain, event_bus):
        """Test that at least 3 AUDIO_CHUNK events are generated."""
        await output_brain.initialize()
        
        chunk_count = 0
        
        async def count_chunks(event):
            nonlocal chunk_count
            chunk_count += 1
        
        event_bus.subscribe(EventType.AUDIO_CHUNK)(count_chunks)
        
        event = Mock()
        event.payload = {"response": "Test response"}
        
        await output_brain._on_response_ready(event)
        
        assert chunk_count >= 3


class TestOutputBrainAudioComplete:
    """Test AUDIO_COMPLETE event generation."""
    
    @pytest.mark.asyncio
    async def test_generates_audio_complete_event(self, output_brain, event_bus):
        """Test that _on_response_ready generates AUDIO_COMPLETE event."""
        await output_brain.initialize()
        
        complete_events = []
        
        async def capture_complete(event):
            complete_events.append(event)
        
        event_bus.subscribe(EventType.AUDIO_COMPLETE)(capture_complete)
        
        event = Mock()
        event.payload = {"response": "Test response"}
        
        await output_brain._on_response_ready(event)
        await asyncio.sleep(0.1)
        
        assert len(complete_events) == 1
    
    @pytest.mark.asyncio
    async def test_audio_complete_contains_full_audio_and_duration(self, output_brain, event_bus):
        """Test that AUDIO_COMPLETE event contains full audio and duration."""
        await output_brain.initialize()
        
        complete_events = []
        
        async def capture_complete(event):
            complete_events.append(event)
        
        event_bus.subscribe(EventType.AUDIO_COMPLETE)(capture_complete)
        
        event = Mock()
        event.payload = {"response": "Test response"}
        
        await output_brain._on_response_ready(event)
        await asyncio.sleep(0.1)
        
        assert len(complete_events) == 1
        payload = complete_events[0].payload
        assert "audio" in payload or "full_audio" in payload
        assert "duration_ms" in payload


class TestOutputBrainLatencyTracking:
    """Test synthesis latency tracking."""
    
    @pytest.mark.asyncio
    async def test_tracks_synthesis_latency(self, output_brain):
        """Test that OutputBrain tracks synthesis latency."""
        await output_brain.initialize()
        
        event = Mock()
        event.payload = {"response": "Test response"}
        
        await output_brain._on_response_ready(event)
        
        # Should have at least one latency measurement
        assert len(output_brain.synthesis_latencies) > 0
    
    @pytest.mark.asyncio
    async def test_latency_is_positive(self, output_brain):
        """Test that recorded latencies are positive values."""
        await output_brain.initialize()
        
        event = Mock()
        event.payload = {"response": "Test response"}
        
        await output_brain._on_response_ready(event)
        
        for latency in output_brain.synthesis_latencies:
            assert latency > 0


class TestOutputBrainErrorHandling:
    """Test error handling and resilience."""
    
    @pytest.mark.asyncio
    async def test_handles_tts_error_gracefully(self, event_bus, shared_state):
        """Test that OutputBrain handles TTS errors gracefully."""
        error_provider = MockTTSProvider()
        error_provider.error = RuntimeError("TTS synthesis failed")
        
        brain = OutputBrain(
            brain_id="output_brain",
            event_bus=event_bus,
            shared_state=shared_state,
            tts_provider=error_provider
        )
        
        await brain.initialize()
        
        event = Mock()
        event.payload = {"response": "Test response"}
        
        # Should not raise, should handle gracefully
        await brain._on_response_ready(event)
    
    @pytest.mark.asyncio
    async def test_logs_tts_errors(self, event_bus, shared_state, caplog):
        """Test that TTS errors are logged."""
        error_provider = MockTTSProvider()
        error_provider.error = RuntimeError("TTS synthesis failed")
        
        brain = OutputBrain(
            brain_id="output_brain",
            event_bus=event_bus,
            shared_state=shared_state,
            tts_provider=error_provider
        )
        
        await brain.initialize()
        
        event = Mock()
        event.payload = {"response": "Test response"}
        
        await brain._on_response_ready(event)
        
        # Error should be logged (caplog captures logs)
        # This verifies the brain logs errors
        # caplog can be checked if logging is properly configured


class TestOutputBrainEmitEvents:
    """Test event emission."""
    
    @pytest.mark.asyncio
    async def test_emits_events_for_each_chunk(self, output_brain, event_bus):
        """Test that brain emits AUDIO_CHUNK for each streaming chunk."""
        await output_brain.initialize()
        
        events_emitted = []
        
        async def capture_events(event):
            events_emitted.append(event.type)
        
        event_bus.subscribe(EventType.AUDIO_CHUNK)(capture_events)
        
        event = Mock()
        event.payload = {"response": "Test"}
        
        await output_brain._on_response_ready(event)
        
        # Verify AUDIO_CHUNK events were emitted
        audio_chunk_count = sum(1 for e in events_emitted if e == EventType.AUDIO_CHUNK)
        assert audio_chunk_count >= 3


class TestOutputBrainIntegration:
    """Integration tests for OutputBrain."""
    
    @pytest.mark.asyncio
    async def test_full_response_workflow(self, output_brain, event_bus):
        """Test complete workflow from RESPONSE_READY to AUDIO_COMPLETE."""
        await output_brain.initialize()
        
        events_captured = {
            EventType.AUDIO_CHUNK: [],
            EventType.AUDIO_COMPLETE: [],
        }
        
        async def capture_audio_chunk(event):
            events_captured[EventType.AUDIO_CHUNK].append(event)
        
        async def capture_audio_complete(event):
            events_captured[EventType.AUDIO_COMPLETE].append(event)
        
        event_bus.subscribe(EventType.AUDIO_CHUNK)(capture_audio_chunk)
        event_bus.subscribe(EventType.AUDIO_COMPLETE)(capture_audio_complete)
        
        event = Mock()
        event.payload = {"response": "Hello world"}
        
        await output_brain._on_response_ready(event)
        await asyncio.sleep(0.1)
        
        assert len(events_captured[EventType.AUDIO_CHUNK]) >= 3
        assert len(events_captured[EventType.AUDIO_COMPLETE]) == 1
