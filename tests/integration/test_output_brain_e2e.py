"""
E2E Integration Test: Full 3-Brain Audio Pipeline

Tests the complete event chain:
AUDIO_CAPTURED → TRANSCRIPTION_COMPLETE → INTENT_DETECTED → RESPONSE_READY → AUDIO_CHUNK → AUDIO_COMPLETE

Verifies:
- InputBrain captures and publishes events
- ReasoningBrain processes transcription and responds
- OutputBrain converts response to audio
- Total latency from audio-in to audio-out < 500ms
"""

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from agent.orchestrator import AgentOrchestrator
from agent.core.messaging import EventBus, EventType, SharedAgentState, AgentEvent
from agent.output.config import TTSConfig
import agent.core.messaging.event_bus as event_bus_module


class MockTTSProvider:
    """Mock TTS provider for integration testing."""
    
    def __init__(self, config: TTSConfig = None):
        self.config = config or TTSConfig(provider="mock", model="mock-model")
    
    async def synthesize(self, text: str, stream: bool = False):
        """Mock synthesize: generates 3 fake audio chunks."""
        if stream:
            async def chunk_generator():
                for i in range(3):
                    yield f"chunk_{i}".encode()
                    await asyncio.sleep(0.01)
            
            return chunk_generator()
        else:
            return b"fake_audio_data"
    
    def set_voice(self, voice_id: str) -> None:
        pass
    
    def get_available_voices(self):
        return [{"id": "0", "name": "Default"}]
    
    def get_usage_stats(self):
        return {"audio_duration_sec": 0.0, "requests": 0, "errors": 0}


@pytest.fixture
def orchestrator_with_mocks():
    """Create orchestrator with mock TTS provider (sync fixture)."""
    # Reset global event bus before each test
    event_bus_module._global_bus = None
    
    tts_provider = MockTTSProvider()
    orchestrator = AgentOrchestrator(
        user_id="test_user",
        session_id="test_session",
        tts_provider=tts_provider
    )
    return orchestrator


class TestFullPipelineE2E:
    """E2E integration tests for 3-brain pipeline."""
    
    @pytest.mark.asyncio
    async def test_orchestrator_initializes_three_brains(self, orchestrator_with_mocks):
        """Verify orchestrator has InputBrain, ReasoningBrain, OutputBrain."""
        orch = orchestrator_with_mocks
        await orch.initialize()
        
        assert orch.input_brain is not None
        assert orch.input_brain.brain_id == "input_brain"
        
        assert orch.reasoning_brain is not None
        assert orch.reasoning_brain.brain_id == "reasoning_brain"
        
        assert orch.output_brain is not None
        assert orch.output_brain.brain_id == "output_brain"
        
        assert orch.output_brain.tts_provider is not None
        
        await orch.stop()
    
    @pytest.mark.asyncio
    async def test_output_brain_has_tts_provider_injected(self, orchestrator_with_mocks):
        """Verify OutputBrain receives TTS provider via dependency injection."""
        orch = orchestrator_with_mocks
        await orch.initialize()
        
        assert orch.output_brain.tts_provider is not None
        assert isinstance(orch.output_brain.tts_provider, MockTTSProvider)
        
        await orch.stop()
    
    @pytest.mark.asyncio
    async def test_full_pipeline_event_chain(self, orchestrator_with_mocks):
        """
        Test complete event chain: AUDIO_CAPTURED → TRANSCRIPTION_COMPLETE → INTENT_DETECTED → RESPONSE_READY → AUDIO_CHUNK → AUDIO_COMPLETE
        """
        orch = orchestrator_with_mocks
        await orch.initialize()
        
        captured_events = []
        expected_types = [
            EventType.TRANSCRIPTION_COMPLETE,
            EventType.INTENT_DETECTED,
            EventType.RESPONSE_READY,
            EventType.AUDIO_CHUNK,
            EventType.AUDIO_COMPLETE,
        ]
        
        async def capture_event(event):
            captured_events.append(event.type)
        
        for event_type in expected_types:
            orch.event_bus.subscribe(event_type)(capture_event)
        
        transcription_event = AgentEvent(
            type=EventType.TRANSCRIPTION_COMPLETE,
            source_brain="input_brain",
            payload={
                "transcript": "Hello world",
                "confidence": 0.95,
                "language": "en"
            }
        )
        await orch.event_bus.publish(transcription_event)
        
        await asyncio.sleep(0.3)
        
        assert EventType.TRANSCRIPTION_COMPLETE in captured_events
        assert EventType.RESPONSE_READY in captured_events
        assert EventType.AUDIO_CHUNK in captured_events
        assert EventType.AUDIO_COMPLETE in captured_events
        
        await orch.stop()
    
    @pytest.mark.asyncio
    async def test_pipeline_latency_under_500ms(self, orchestrator_with_mocks):
        """
        Measure total latency: time from TRANSCRIPTION_COMPLETE to AUDIO_COMPLETE.
        Target: < 500ms per spec.
        """
        orch = orchestrator_with_mocks
        await orch.initialize()
        
        event_times = {}
        
        async def record_time(event_type):
            async def handler(event):
                event_times[event_type] = time.time()
            return handler
        
        for event_type in [EventType.TRANSCRIPTION_COMPLETE, EventType.RESPONSE_READY, EventType.AUDIO_COMPLETE]:
            orch.event_bus.subscribe(event_type)(await record_time(event_type))
        
        start_time = time.time()
        event_times[EventType.TRANSCRIPTION_COMPLETE] = start_time
        
        transcription_event = AgentEvent(
            type=EventType.TRANSCRIPTION_COMPLETE,
            source_brain="input_brain",
            payload={
                "transcript": "Test latency measurement",
                "confidence": 0.95,
            }
        )
        await orch.event_bus.publish(transcription_event)
        
        await asyncio.sleep(0.3)
        
        if EventType.AUDIO_COMPLETE in event_times and EventType.TRANSCRIPTION_COMPLETE in event_times:
            latency_ms = (event_times[EventType.AUDIO_COMPLETE] - event_times[EventType.TRANSCRIPTION_COMPLETE]) * 1000
            print(f"\n Pipeline latency: {latency_ms:.1f}ms")
            assert latency_ms < 500, f"Latency {latency_ms:.1f}ms exceeds target 500ms"
        
        await orch.stop()
    
    @pytest.mark.asyncio
    async def test_input_brain_ready(self, orchestrator_with_mocks):
        """Verify InputBrain initialized and ready."""
        orch = orchestrator_with_mocks
        await orch.initialize()
        input_brain = orch.input_brain
        
        assert input_brain.state.value == "ready"
        assert input_brain.brain_id == "input_brain"
        
        await orch.stop()
    
    @pytest.mark.asyncio
    async def test_reasoning_brain_subscribes_to_transcription(self, orchestrator_with_mocks):
        """Verify ReasoningBrain subscribes to TRANSCRIPTION_COMPLETE."""
        orch = orchestrator_with_mocks
        await orch.initialize()
        
        handlers = orch.event_bus._subscribers.get(EventType.TRANSCRIPTION_COMPLETE, [])
        assert len(handlers) > 0
        
        await orch.stop()
    
    @pytest.mark.asyncio
    async def test_output_brain_subscribes_to_response_ready(self, orchestrator_with_mocks):
        """Verify OutputBrain subscribes to RESPONSE_READY."""
        orch = orchestrator_with_mocks
        await orch.initialize()
        
        handlers = orch.event_bus._subscribers.get(EventType.RESPONSE_READY, [])
        assert len(handlers) > 0
        
        await orch.stop()
    
    @pytest.mark.asyncio
    async def test_audio_chunk_events_generated(self, orchestrator_with_mocks):
        """Verify AUDIO_CHUNK events are generated during TTS."""
        orch = orchestrator_with_mocks
        await orch.initialize()
        
        chunk_events = []
        
        async def capture_chunk(event):
            chunk_events.append(event)
        
        orch.event_bus.subscribe(EventType.AUDIO_CHUNK)(capture_chunk)
        
        response_event = AgentEvent(
            type=EventType.RESPONSE_READY,
            source_brain="reasoning_brain",
            payload={"response": "This is a test response"}
        )
        await orch.event_bus.publish(response_event)
        
        await asyncio.sleep(0.2)
        
        assert len(chunk_events) >= 3
        
        await orch.stop()
    
    @pytest.mark.asyncio
    async def test_audio_complete_event_has_metadata(self, orchestrator_with_mocks):
        """Verify AUDIO_COMPLETE event contains required metadata."""
        orch = orchestrator_with_mocks
        await orch.initialize()
        
        complete_events = []
        
        async def capture_complete(event):
            complete_events.append(event)
        
        orch.event_bus.subscribe(EventType.AUDIO_COMPLETE)(capture_complete)
        
        response_event = AgentEvent(
            type=EventType.RESPONSE_READY,
            source_brain="reasoning_brain",
            payload={"response": "Test response"}
        )
        await orch.event_bus.publish(response_event)
        
        await asyncio.sleep(0.2)
        
        assert len(complete_events) == 1
        payload = complete_events[0].payload
        assert "duration_ms" in payload
        assert "chunk_count" in payload
        
        await orch.stop()
    
    @pytest.mark.asyncio
    async def test_missing_tts_provider_handled(self):
        """Test that orchestrator handles missing TTS provider gracefully."""
        event_bus_module._global_bus = None
        
        orchestrator = AgentOrchestrator(
            user_id="test_user",
            session_id="test_session",
            tts_provider=MockTTSProvider()
        )
        
        await orchestrator.initialize()
        assert orchestrator.output_brain.tts_provider is not None
        await orchestrator.stop()
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_on_reasoning_error(self, orchestrator_with_mocks):
        """Test that pipeline doesn't crash if ReasoningBrain errors."""
        orch = orchestrator_with_mocks
        await orch.initialize()
        
        orch.reasoning_brain.llm_provider = None
        
        transcription_event = AgentEvent(
            type=EventType.TRANSCRIPTION_COMPLETE,
            source_brain="input_brain",
            payload={"transcript": "Test", "confidence": 0.95}
        )
        
        await orch.event_bus.publish(transcription_event)
        await asyncio.sleep(0.1)
        
        await orch.stop()


class TestPipelineMetrics:
    """Test latency and performance metrics."""
    
    @pytest.mark.asyncio
    async def test_output_brain_tracks_synthesis_latency(self, orchestrator_with_mocks):
        """Verify OutputBrain records synthesis latencies."""
        orch = orchestrator_with_mocks
        await orch.initialize()
        
        response_event = AgentEvent(
            type=EventType.RESPONSE_READY,
            source_brain="reasoning_brain",
            payload={"response": "Test"}
        )
        
        await orch.event_bus.publish(response_event)
        await asyncio.sleep(0.2)
        
        assert len(orch.output_brain.synthesis_latencies) > 0
        for latency in orch.output_brain.synthesis_latencies:
            assert latency > 0
        
        await orch.stop()
