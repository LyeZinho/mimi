import pytest
from agent.output.response_buffer import ResponseBuffer


@pytest.mark.asyncio
async def test_response_buffer_init():
    """Test ResponseBuffer initialization."""
    buffer = ResponseBuffer(sample_rate=22050, buffer_duration_sec=5.0)
    
    assert buffer.sample_rate == 22050
    assert buffer.buffer_duration_sec == 5.0
    assert buffer.total_chunks == 0
    assert not buffer.is_complete()


@pytest.mark.asyncio
async def test_response_buffer_add_chunk():
    """Test adding a chunk to buffer."""
    buffer = ResponseBuffer(sample_rate=22050)
    
    audio_bytes = b'\x00' * 1024
    phonemes = ['a', 'e', 'i']
    
    await buffer.add_chunk(audio_bytes, phonemes)
    
    assert buffer.total_chunks == 1
    assert buffer.total_bytes >= len(audio_bytes)


@pytest.mark.asyncio
async def test_response_buffer_get_chunks():
    """Test retrieving chunks from buffer."""
    buffer = ResponseBuffer(sample_rate=22050)
    
    audio_bytes_1 = b'\x01' * 1024
    audio_bytes_2 = b'\x02' * 1024
    
    await buffer.add_chunk(audio_bytes_1, ['a'])
    await buffer.add_chunk(audio_bytes_2, ['e'])
    
    chunks = buffer.get_chunks(start_index=0)
    
    assert len(chunks) == 2
    assert chunks[0]['audio_bytes'] == audio_bytes_1
    assert chunks[1]['audio_bytes'] == audio_bytes_2


@pytest.mark.asyncio
async def test_response_buffer_complete():
    """Test marking buffer as complete."""
    buffer = ResponseBuffer()
    
    assert not buffer.is_complete()
    
    buffer.mark_complete()
    
    assert buffer.is_complete()


@pytest.mark.asyncio
async def test_response_buffer_clear():
    """Test clearing buffer for new response."""
    buffer = ResponseBuffer()
    
    await buffer.add_chunk(b'\x00' * 1024, ['a'])
    
    assert buffer.total_chunks == 1
    
    buffer.clear()
    
    assert buffer.total_chunks == 0
    assert not buffer.is_complete()


@pytest.mark.asyncio
async def test_response_buffer_duration():
    """Test calculating total audio duration."""
    buffer = ResponseBuffer(sample_rate=22050)
    
    # 2 chunks of 1024 bytes each (16-bit = 2 bytes/sample)
    # 1024 bytes = 512 samples at 22050 Hz = ~23ms
    await buffer.add_chunk(b'\x00' * 1024, [])
    await buffer.add_chunk(b'\x00' * 1024, [])
    
    duration_sec = buffer.duration_seconds()
    
    assert duration_sec > 0
    assert duration_sec < 1.0  # Should be ~46ms
