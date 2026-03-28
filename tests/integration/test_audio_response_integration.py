import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from agent.core.messaging import EventBus, EventType, AgentEvent
from agent.bridge import OrchestratorBridge
from agent.output.response_buffer import ResponseBuffer


@pytest.mark.asyncio
async def test_response_buffer_accumulates_chunks():
    buffer = ResponseBuffer(sample_rate=22050, buffer_duration_sec=5)
    
    for i in range(3):
        audio_bytes = bytes([i] * 1024)
        await buffer.add_chunk(audio_bytes, [chr(97 + i)])
    
    chunks = buffer.get_chunks(start_index=0)
    
    assert len(chunks) == 3
    assert chunks[0]['audio_bytes'] == bytes([0] * 1024)
    assert chunks[1]['audio_bytes'] == bytes([1] * 1024)
    assert chunks[2]['audio_bytes'] == bytes([2] * 1024)
    
    duration = buffer.duration_seconds()
    assert duration > 0


@pytest.mark.asyncio
async def test_audio_chunks_sent_via_bridge():
    mock_avatar = AsyncMock()
    event_bus = EventBus()
    bridge = OrchestratorBridge(mock_avatar, event_bus)
    
    await event_bus.start()
    await bridge.start()
    
    audio_chunk_event = AgentEvent(
        type=EventType.AUDIO_CHUNK,
        source_brain="output_brain",
        payload={
            "data": b'\x00\x01\x02\x03',
            "chunk_index": 0,
        }
    )
    
    await event_bus.publish(audio_chunk_event)
    
    await asyncio.sleep(0.2)
    
    mock_avatar.send_command.assert_called()
    
    call_args = mock_avatar.send_command.call_args[0][0]
    assert call_args['type'] == 'audio_chunk'
    assert 'audio_data' in call_args
    assert call_args['audio_data'] == '00010203'
    
    await event_bus.stop()


@pytest.mark.asyncio
async def test_bridge_and_buffer_integration():
    event_bus = EventBus()
    mock_avatar = AsyncMock()
    bridge = OrchestratorBridge(mock_avatar, event_bus)
    
    await event_bus.start()
    await bridge.start()
    
    buffer = ResponseBuffer(sample_rate=22050)
    
    for i in range(3):
        chunk_data = b'\x00\x01' * 512
        await buffer.add_chunk(chunk_data, ['a', 'e', 'i'][i:i+1])
        
        chunk_event = AgentEvent(
            type=EventType.AUDIO_CHUNK,
            source_brain="output_brain",
            payload={
                "data": chunk_data,
                "chunk_index": i,
            }
        )
        
        await event_bus.publish(chunk_event)
    
    await asyncio.sleep(0.2)
    
    assert mock_avatar.send_command.call_count >= 3
    assert buffer.total_chunks == 3
    assert buffer.duration_seconds() > 0
    
    await event_bus.stop()


@pytest.mark.asyncio
async def test_response_buffer_tracks_duration():
    buffer = ResponseBuffer(sample_rate=22050)
    
    test_audio = b'\x00\x01' * 1024
    await buffer.add_chunk(test_audio, ['a', 'e'])
    
    duration = buffer.duration_seconds()
    assert duration > 0
    assert buffer.total_chunks == 1
    assert buffer.is_complete() == False
    
    buffer.mark_complete()
    assert buffer.is_complete() == True


@pytest.mark.asyncio
async def test_phoneme_data_event_flow():
    event_bus = EventBus()
    await event_bus.start()
    
    phoneme_events = []
    
    async def capture_phoneme_events(event):
        phoneme_events.append(event)
    
    event_bus.subscribe(EventType.PHONEME_DATA)(capture_phoneme_events)
    
    phoneme_event = AgentEvent(
        type=EventType.PHONEME_DATA,
        source_brain="output_brain",
        payload={
            "text": "olá",
            "phonemes": ['o', 'l', 'a'],
            "sample_positions": [0, 1024, 2048],
            "sample_rate": 22050,
        }
    )
    
    await event_bus.publish(phoneme_event)
    await asyncio.sleep(0.2)
    
    assert len(phoneme_events) == 1
    assert phoneme_events[0].payload['phonemes'] == ['o', 'l', 'a']
    
    await event_bus.stop()
