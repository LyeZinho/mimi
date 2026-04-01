"""
Tests for AudioBuffer ring buffer implementation.
Tests circular buffer for real-time audio with wraparound, fill tracking, and playback readiness.
"""

import pytest
import numpy as np
from agent.output.audio_buffer import AudioBuffer


class TestAudioBufferInitialization:
    """Test AudioBuffer initialization with proper ring buffer allocation."""
    
    def test_init_default_parameters(self):
        """Test initialization with default parameters."""
        buffer = AudioBuffer()
        assert buffer.sample_rate == 22050
        assert buffer.channels == 1
        assert buffer.duration_sec == 5.0
        
    def test_init_custom_parameters(self):
        """Test initialization with custom parameters."""
        buffer = AudioBuffer(sample_rate=44100, channels=2, duration_sec=10.0)
        assert buffer.sample_rate == 44100
        assert buffer.channels == 2
        assert buffer.duration_sec == 10.0
        
    def test_init_pre_allocates_numpy_buffer(self):
        """Test that numpy ring buffer is pre-allocated with correct shape."""
        buffer = AudioBuffer(sample_rate=22050, channels=1, duration_sec=5.0)
        total_samples = 22050 * 5  # sample_rate * duration_sec
        assert buffer._buffer.shape == (total_samples, 1)
        assert buffer._buffer.dtype == np.float32


class TestAudioBufferWrite:
    """Test writing audio chunks to the ring buffer."""
    
    def test_write_single_chunk_updates_write_position(self):
        """Test writing a single audio chunk updates write position."""
        buffer = AudioBuffer(sample_rate=22050, channels=1, duration_sec=5.0)
        audio_chunk = b'\x00\x00\x00\x00' * 1000  # 1000 samples
        
        pytest.mark.asyncio
        import asyncio
        asyncio.run(buffer.write(audio_chunk))
        
        # Write position should advance
        assert buffer._write_pos > 0
        
    def test_write_converts_bytes_to_numpy(self):
        """Test that bytes are properly converted to numpy array."""
        buffer = AudioBuffer(sample_rate=22050, channels=1, duration_sec=5.0)
        # Create audio chunk: 100 samples of float32 (4 bytes per sample)
        audio_data = np.array([0.1, 0.2, 0.3] * 33 + [0.1], dtype=np.float32)
        audio_chunk = audio_data.tobytes()
        
        pytest.mark.asyncio
        import asyncio
        asyncio.run(buffer.write(audio_chunk))
        
        assert buffer._write_pos > 0
        
    def test_write_multiple_chunks_sequentially(self):
        """Test writing multiple chunks sequentially."""
        buffer = AudioBuffer(sample_rate=22050, channels=1, duration_sec=5.0)
        audio_data = np.array([0.1] * 100, dtype=np.float32)
        
        pytest.mark.asyncio
        import asyncio
        async def write_chunks():
            for _ in range(3):
                await buffer.write(audio_data.tobytes())
        
        asyncio.run(write_chunks())
        assert buffer._write_pos == 300
        
    def test_write_handles_buffer_wraparound(self):
        """Test writing handles circular buffer wraparound correctly."""
        buffer = AudioBuffer(sample_rate=1000, channels=1, duration_sec=1.0)
        # Total capacity: 1000 samples
        
        pytest.mark.asyncio
        import asyncio
        async def write_with_wraparound():
            # Write 900 samples
            data1 = np.array([0.1] * 900, dtype=np.float32)
            await buffer.write(data1.tobytes())
            assert buffer._write_pos == 900
            
            # Write 200 more samples (should wrap around)
            data2 = np.array([0.2] * 200, dtype=np.float32)
            await buffer.write(data2.tobytes())
            assert buffer._write_pos == 100  # 900 + 200 = 1100 mod 1000
        
        asyncio.run(write_with_wraparound())


class TestAudioBufferRead:
    """Test reading audio chunks from the ring buffer."""
    
    def test_read_returns_numpy_array(self):
        """Test that read returns a numpy array."""
        buffer = AudioBuffer(sample_rate=22050, channels=1, duration_sec=5.0)
        
        pytest.mark.asyncio
        import asyncio
        async def test_read():
            # Write some data first
            audio_data = np.array([0.5] * 100, dtype=np.float32)
            await buffer.write(audio_data.tobytes())
            
            # Read data
            result = await buffer.read(50)
            assert isinstance(result, np.ndarray)
            assert result.dtype == np.float32
            assert len(result) == 50
        
        asyncio.run(test_read())
        
    def test_read_updates_read_position(self):
        """Test that reading updates the read position."""
        buffer = AudioBuffer(sample_rate=22050, channels=1, duration_sec=5.0)
        
        pytest.mark.asyncio
        import asyncio
        async def test_read_pos():
            audio_data = np.array([0.3] * 200, dtype=np.float32)
            await buffer.write(audio_data.tobytes())
            
            initial_read_pos = buffer._read_pos
            await buffer.read(50)
            assert buffer._read_pos == (initial_read_pos + 50) % buffer._buffer_size
        
        asyncio.run(test_read_pos())
        
    def test_read_handles_wraparound(self):
        """Test reading handles wraparound correctly."""
        buffer = AudioBuffer(sample_rate=1000, channels=1, duration_sec=1.0)
        
        pytest.mark.asyncio
        import asyncio
        async def test_read_wrap():
            # Write data across wraparound boundary
            buffer._write_pos = 950
            audio_data = np.array(np.arange(100, dtype=np.float32))
            
            # Manually place data at write position
            for i in range(50):
                buffer._buffer[950 + i, 0] = float(i)
            for i in range(50):
                buffer._buffer[i, 0] = float(50 + i)
            
            buffer._write_pos = 50
            buffer._read_pos = 950
            
            result = await buffer.read(100)
            assert len(result) == 100
            assert result[0] == 0.0
            assert result[99] == 99.0
        
        asyncio.run(test_read_wrap())


class TestAudioBufferFillLevel:
    """Test buffer fill level calculation."""
    
    def test_fill_level_empty_buffer(self):
        """Test fill level is 0 for empty buffer."""
        buffer = AudioBuffer(sample_rate=22050, channels=1, duration_sec=5.0)
        assert buffer.get_fill_level() == 0.0
        
    def test_fill_level_half_full(self):
        """Test fill level returns correct value when half full."""
        buffer = AudioBuffer(sample_rate=1000, channels=1, duration_sec=1.0)
        
        pytest.mark.asyncio
        import asyncio
        async def test_half_fill():
            audio_data = np.array([0.1] * 500, dtype=np.float32)
            await buffer.write(audio_data.tobytes())
            
            fill = buffer.get_fill_level()
            assert 0.49 < fill < 0.51  # ~0.5
        
        asyncio.run(test_half_fill())
        
    def test_fill_level_full_buffer(self):
        """Test fill level approaches 1.0 when buffer is full."""
        buffer = AudioBuffer(sample_rate=1000, channels=1, duration_sec=1.0)
        
        pytest.mark.asyncio
        import asyncio
        async def test_full_fill():
            audio_data = np.array([0.1] * 1000, dtype=np.float32)
            await buffer.write(audio_data.tobytes())
            
            fill = buffer.get_fill_level()
            assert 0.99 < fill <= 1.0
        
        asyncio.run(test_full_fill())


class TestAudioBufferPlaybackReadiness:
    """Test playback readiness detection."""
    
    def test_is_ready_for_playback_below_threshold(self):
        """Test playback not ready when fill is below threshold."""
        buffer = AudioBuffer(sample_rate=1000, channels=1, duration_sec=1.0)
        
        pytest.mark.asyncio
        import asyncio
        async def test_not_ready():
            # Write only 5% (below default 10% threshold)
            audio_data = np.array([0.1] * 50, dtype=np.float32)
            await buffer.write(audio_data.tobytes())
            
            assert not buffer.is_ready_for_playback(threshold=0.1)
        
        asyncio.run(test_not_ready())
        
    def test_is_ready_for_playback_meets_threshold(self):
        """Test playback ready when fill meets threshold."""
        buffer = AudioBuffer(sample_rate=1000, channels=1, duration_sec=1.0)
        
        pytest.mark.asyncio
        import asyncio
        async def test_ready():
            # Write 20% (above default 10% threshold)
            audio_data = np.array([0.1] * 200, dtype=np.float32)
            await buffer.write(audio_data.tobytes())
            
            assert buffer.is_ready_for_playback(threshold=0.1)
        
        asyncio.run(test_ready())
        
    def test_is_ready_for_playback_custom_threshold(self):
        """Test playback readiness with custom threshold."""
        buffer = AudioBuffer(sample_rate=1000, channels=1, duration_sec=1.0)
        
        pytest.mark.asyncio
        import asyncio
        async def test_custom_threshold():
            # Write 30%
            audio_data = np.array([0.1] * 300, dtype=np.float32)
            await buffer.write(audio_data.tobytes())
            
            assert not buffer.is_ready_for_playback(threshold=0.5)
            assert buffer.is_ready_for_playback(threshold=0.2)
        
        asyncio.run(test_custom_threshold())


class TestAudioBufferUnderrun:
    """Test underrun handling when reading more than available."""
    
    def test_underrun_read_more_than_available(self):
        """Test reading more samples than available."""
        buffer = AudioBuffer(sample_rate=1000, channels=1, duration_sec=1.0)
        
        pytest.mark.asyncio
        import asyncio
        async def test_underrun():
            # Write 100 samples
            audio_data = np.array([0.1] * 100, dtype=np.float32)
            await buffer.write(audio_data.tobytes())
            
            # Try to read 200 samples
            result = await buffer.read(200)
            # Should return available samples or handle gracefully
            assert len(result) > 0
        
        asyncio.run(test_underrun())


class TestAudioBufferOverflow:
    """Test overflow handling when writing more than capacity."""
    
    def test_overflow_write_exceeding_capacity(self):
        """Test writing data larger than buffer capacity."""
        buffer = AudioBuffer(sample_rate=1000, channels=1, duration_sec=1.0)
        
        pytest.mark.asyncio
        import asyncio
        async def test_overflow():
            # Write 1500 samples to 1000-sample buffer (should wrap)
            audio_data = np.array([0.1] * 1500, dtype=np.float32)
            await buffer.write(audio_data.tobytes())
            
            # Should not crash, buffer should wrap around
            assert buffer._write_pos >= 0
            assert buffer._write_pos < buffer._buffer_size
        
        asyncio.run(test_overflow())
        
    def test_overflow_write_multiple_times_exceeding_capacity(self):
        """Test multiple writes exceeding capacity."""
        buffer = AudioBuffer(sample_rate=1000, channels=1, duration_sec=1.0)
        
        pytest.mark.asyncio
        import asyncio
        async def test_multi_overflow():
            # Write more than buffer size multiple times
            for _ in range(3):
                audio_data = np.array([0.1] * 500, dtype=np.float32)
                await buffer.write(audio_data.tobytes())
            
            # Should handle gracefully with wraparound
            assert buffer._write_pos >= 0
            assert buffer._write_pos < buffer._buffer_size
        
        asyncio.run(test_multi_overflow())


class TestAudioBufferRingBufferBehavior:
    """Test circular buffer properties and wraparound semantics."""
    
    def test_ring_buffer_preserves_data_within_capacity(self):
        """Test that data is preserved when within capacity."""
        buffer = AudioBuffer(sample_rate=1000, channels=1, duration_sec=1.0)
        
        pytest.mark.asyncio
        import asyncio
        async def test_preserve():
            # Write and read back
            test_data = np.array([0.1, 0.2, 0.3, 0.4, 0.5], dtype=np.float32)
            await buffer.write(test_data.tobytes())
            
            result = await buffer.read(5)
            np.testing.assert_array_almost_equal(result, test_data)
        
        asyncio.run(test_preserve())
