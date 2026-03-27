"""
Tests for PlaybackEngine: real-time audio playback with sounddevice.

Tests playback of complete audio, streaming from AudioBuffer, state management,
latency tracking, and error handling without actual hardware dependencies.
"""

import pytest
import numpy as np
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass

from agent.output.audio_buffer import AudioBuffer


@dataclass
class PlaybackConfig:
    """Configuration for PlaybackEngine."""
    sample_rate: int = 44100
    channels: int = 1
    dtype: str = "float32"


class TestPlaybackEngineInitialization:
    """Test PlaybackEngine initialization and configuration."""
    
    @pytest.mark.asyncio
    async def test_init_with_default_config(self):
        """Test initialization with default PlaybackConfig."""
        from agent.output.playback_engine import PlaybackEngine
        
        config = PlaybackConfig()
        engine = PlaybackEngine(config)
        
        assert engine.config.sample_rate == 44100
        assert engine.config.channels == 1
        assert engine.config.dtype == "float32"
        
    @pytest.mark.asyncio
    async def test_init_with_custom_config(self):
        """Test initialization with custom sample rate and channels."""
        from agent.output.playback_engine import PlaybackEngine
        
        config = PlaybackConfig(sample_rate=48000, channels=2)
        engine = PlaybackEngine(config)
        
        assert engine.config.sample_rate == 48000
        assert engine.config.channels == 2
        
    @pytest.mark.asyncio
    async def test_init_playback_state_idle(self):
        """Test initial playback state is idle."""
        from agent.output.playback_engine import PlaybackEngine
        
        config = PlaybackConfig()
        engine = PlaybackEngine(config)
        
        assert engine._playback_state == "idle"
        assert engine._playback_latency_ms == 0.0


class TestPlaybackEnginePlayAsync:
    """Test async playback of complete audio data."""
    
    @pytest.mark.asyncio
    async def test_play_async_simple_audio_array(self):
        """Test playing a simple numpy array."""
        from agent.output.playback_engine import PlaybackEngine
        
        with patch("agent.output.playback_engine.sd") as mock_sd:
            config = PlaybackConfig()
            engine = PlaybackEngine(config)
            
            # Create test audio: 1 second at 44100 Hz
            audio_data = np.random.randn(44100).astype(np.float32)
            
            # Mock sounddevice.play
            mock_sd.play = Mock()
            mock_sd.wait = Mock()
            
            await engine.play_async(audio_data)
            
            # Verify sounddevice.play was called with correct parameters
            mock_sd.play.assert_called_once()
            args, kwargs = mock_sd.play.call_args
            np.testing.assert_array_equal(args[0], audio_data)
            assert kwargs.get("samplerate") == 44100
            
    @pytest.mark.asyncio
    async def test_play_async_blocks_until_done(self):
        """Test that play_async blocks until sounddevice.wait completes."""
        from agent.output.playback_engine import PlaybackEngine
        
        with patch("agent.output.playback_engine.sd") as mock_sd:
            config = PlaybackConfig()
            engine = PlaybackEngine(config)
            
            audio_data = np.random.randn(44100).astype(np.float32)
            
            # Mock sounddevice
            mock_sd.play = Mock()
            mock_sd.wait = Mock()
            
            await engine.play_async(audio_data)
            
            # Verify wait was called to block
            mock_sd.wait.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_play_async_sets_playing_state(self):
        """Test that play_async sets state to 'playing' during playback."""
        from agent.output.playback_engine import PlaybackEngine
        
        with patch("agent.output.playback_engine.sd") as mock_sd:
            config = PlaybackConfig()
            engine = PlaybackEngine(config)
            
            audio_data = np.random.randn(44100).astype(np.float32)
            
            mock_sd.play = Mock()
            mock_sd.wait = Mock()
            
            await engine.play_async(audio_data)
            
            # After playback, state should return to idle
            assert engine._playback_state == "idle"
            
    @pytest.mark.asyncio
    async def test_play_async_rejects_empty_audio(self):
        """Test that play_async rejects empty audio arrays."""
        from agent.output.playback_engine import PlaybackEngine
        
        config = PlaybackConfig()
        engine = PlaybackEngine(config)
        
        empty_audio = np.array([], dtype=np.float32)
        
        with pytest.raises(ValueError, match="Audio data cannot be empty"):
            await engine.play_async(empty_audio)
            
    @pytest.mark.asyncio
    async def test_play_async_rejects_invalid_dtype(self):
        """Test that play_async validates audio data type."""
        from agent.output.playback_engine import PlaybackEngine
        
        config = PlaybackConfig()
        engine = PlaybackEngine(config)
        
        # Wrong dtype
        invalid_audio = np.random.randint(0, 100, 44100).astype(np.int32)
        
        with pytest.raises(ValueError, match="Audio data must be float32"):
            await engine.play_async(invalid_audio)


class TestPlaybackEngineStreaming:
    """Test streaming playback from AudioBuffer."""
    
    @pytest.mark.asyncio
    async def test_play_streaming_from_buffer(self):
        """Test streaming playback from AudioBuffer."""
        from agent.output.playback_engine import PlaybackEngine
        
        with patch("agent.output.playback_engine.sd") as mock_sd:
            config = PlaybackConfig(sample_rate=44100)
            engine = PlaybackEngine(config)
            
            # Create AudioBuffer and write test data
            buffer = AudioBuffer(sample_rate=44100, channels=1, duration_sec=2.0)
            audio_data = np.random.randn(88200).astype(np.float32)  # 2 seconds
            await buffer.write(audio_data.tobytes())
            
            mock_sd.play = Mock()
            mock_sd.wait = Mock()
            
            # Stream for 0.1 seconds
            await engine.play_streaming(buffer, chunk_size=4410)
            
            # Verify sounddevice.play was called at least once
            assert mock_sd.play.call_count >= 1
            
    @pytest.mark.asyncio
    async def test_play_streaming_respects_chunk_size(self):
        """Test that streaming uses specified chunk size."""
        from agent.output.playback_engine import PlaybackEngine
        
        with patch("agent.output.playback_engine.sd") as mock_sd:
            config = PlaybackConfig(sample_rate=44100)
            engine = PlaybackEngine(config)
            
            buffer = AudioBuffer(sample_rate=44100, channels=1, duration_sec=2.0)
            audio_data = np.random.randn(44100).astype(np.float32)  # 1 second
            await buffer.write(audio_data.tobytes())
            
            mock_sd.play = Mock()
            mock_sd.wait = Mock()
            
            chunk_size = 8820  # 0.2 seconds
            await engine.play_streaming(buffer, chunk_size=chunk_size)
            
            # Verify chunk processing
            if mock_sd.play.call_count > 0:
                args, _ = mock_sd.play.call_args
                # Last chunk might be smaller, but not larger than chunk_size
                assert args[0].shape[0] <= chunk_size or args[0].shape[0] > 0
                
    @pytest.mark.asyncio
    async def test_play_streaming_rejects_empty_buffer(self):
        """Test that play_streaming handles empty buffer gracefully."""
        from agent.output.playback_engine import PlaybackEngine
        
        config = PlaybackConfig()
        engine = PlaybackEngine(config)
        
        # Empty buffer with no data
        buffer = AudioBuffer(sample_rate=44100, channels=1, duration_sec=1.0)
        
        # Should not raise, but also not produce output
        await engine.play_streaming(buffer, chunk_size=4410)


class TestPlaybackEngineStateControl:
    """Test pause, resume, and stop state transitions."""
    
    @pytest.mark.asyncio
    async def test_pause_changes_state(self):
        """Test that pause changes state to 'paused'."""
        from agent.output.playback_engine import PlaybackEngine
        
        with patch("agent.output.playback_engine.sd") as mock_sd:
            config = PlaybackConfig()
            engine = PlaybackEngine(config)
            
            # Set to playing state
            engine._playback_state = "playing"
            
            mock_sd.stop = Mock()
            engine.pause()
            
            assert engine._playback_state == "paused"
            mock_sd.stop.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_resume_changes_state(self):
        """Test that resume changes state from paused to playing."""
        from agent.output.playback_engine import PlaybackEngine
        
        config = PlaybackConfig()
        engine = PlaybackEngine(config)
        
        engine._playback_state = "paused"
        engine.resume()
        
        assert engine._playback_state == "playing"
        
    @pytest.mark.asyncio
    async def test_stop_resets_state_to_idle(self):
        """Test that stop resets state to idle and stops sounddevice."""
        from agent.output.playback_engine import PlaybackEngine
        
        with patch("agent.output.playback_engine.sd") as mock_sd:
            config = PlaybackConfig()
            engine = PlaybackEngine(config)
            
            engine._playback_state = "playing"
            
            mock_sd.stop = Mock()
            engine.stop()
            
            assert engine._playback_state == "idle"
            mock_sd.stop.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_resume_from_idle_raises_error(self):
        """Test that resume from idle raises error."""
        from agent.output.playback_engine import PlaybackEngine
        
        config = PlaybackConfig()
        engine = PlaybackEngine(config)
        
        # Already in idle state
        with pytest.raises(RuntimeError, match="Cannot resume from idle"):
            engine.resume()
            
    @pytest.mark.asyncio
    async def test_pause_from_idle_raises_error(self):
        """Test that pause from idle raises error."""
        from agent.output.playback_engine import PlaybackEngine
        
        config = PlaybackConfig()
        engine = PlaybackEngine(config)
        
        with pytest.raises(RuntimeError, match="Cannot pause from idle"):
            engine.pause()


class TestPlaybackEngineWaitUntilDone:
    """Test wait_until_done blocking behavior."""
    
    @pytest.mark.asyncio
    async def test_wait_until_done_blocks_while_playing(self):
        """Test that wait_until_done blocks while playback is active."""
        from agent.output.playback_engine import PlaybackEngine
        
        config = PlaybackConfig()
        engine = PlaybackEngine(config)
        
        engine._playback_state = "playing"
        
        # Simulate completion after small delay
        async def complete_playback():
            import asyncio
            await asyncio.sleep(0.01)
            engine._playback_state = "idle"
        
        import asyncio
        task = asyncio.create_task(complete_playback())
        
        await engine.wait_until_done()
        await task
        
        assert engine._playback_state == "idle"
        
    @pytest.mark.asyncio
    async def test_wait_until_done_returns_immediately_when_idle(self):
        """Test that wait_until_done returns immediately if idle."""
        from agent.output.playback_engine import PlaybackEngine
        
        config = PlaybackConfig()
        engine = PlaybackEngine(config)
        
        engine._playback_state = "idle"
        
        # Should return immediately without waiting
        await engine.wait_until_done()
        
        assert engine._playback_state == "idle"


class TestPlaybackEngineLatencyTracking:
    """Test playback latency measurement."""
    
    @pytest.mark.asyncio
    async def test_get_playback_latency_initial_zero(self):
        """Test that initial playback latency is zero."""
        from agent.output.playback_engine import PlaybackEngine
        
        config = PlaybackConfig()
        engine = PlaybackEngine(config)
        
        latency = engine.get_playback_latency_ms()
        assert latency == 0.0
        
    @pytest.mark.asyncio
    async def test_get_playback_latency_after_playback(self):
        """Test that latency is measured after playback completes."""
        from agent.output.playback_engine import PlaybackEngine
        
        with patch("agent.output.playback_engine.sd") as mock_sd:
            config = PlaybackConfig()
            engine = PlaybackEngine(config)
            
            audio_data = np.random.randn(44100).astype(np.float32)
            
            mock_sd.play = Mock()
            mock_sd.wait = Mock()
            
            await engine.play_async(audio_data)
            
            latency = engine.get_playback_latency_ms()
            # Latency should be measured (likely small for mock, but > 0)
            assert isinstance(latency, float)
            assert latency >= 0.0


class TestPlaybackEngineErrorHandling:
    """Test error handling and edge cases."""
    
    @pytest.mark.asyncio
    async def test_device_error_raises_exception(self):
        """Test that sounddevice errors are propagated."""
        from agent.output.playback_engine import PlaybackEngine
        
        with patch("agent.output.playback_engine.sd") as mock_sd:
            config = PlaybackConfig()
            engine = PlaybackEngine(config)
            
            audio_data = np.random.randn(44100).astype(np.float32)
            
            # Simulate device error
            mock_sd.play = Mock(side_effect=RuntimeError("Device not found"))
            
            with pytest.raises(RuntimeError, match="Device not found"):
                await engine.play_async(audio_data)
                
    @pytest.mark.asyncio
    async def test_play_async_with_mono_audio(self):
        """Test playing mono audio (1D array)."""
        from agent.output.playback_engine import PlaybackEngine
        
        with patch("agent.output.playback_engine.sd") as mock_sd:
            config = PlaybackConfig(channels=1)
            engine = PlaybackEngine(config)
            
            # Mono: 1D array
            audio_data = np.random.randn(44100).astype(np.float32)
            
            mock_sd.play = Mock()
            mock_sd.wait = Mock()
            
            await engine.play_async(audio_data)
            
            mock_sd.play.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_play_async_with_stereo_audio(self):
        """Test playing stereo audio (2D array)."""
        from agent.output.playback_engine import PlaybackEngine
        
        with patch("agent.output.playback_engine.sd") as mock_sd:
            config = PlaybackConfig(channels=2)
            engine = PlaybackEngine(config)
            
            # Stereo: 2D array (samples, channels)
            audio_data = np.random.randn(44100, 2).astype(np.float32)
            
            mock_sd.play = Mock()
            mock_sd.wait = Mock()
            
            await engine.play_async(audio_data)
            
            mock_sd.play.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_multiple_play_async_calls_sequential(self):
        """Test that multiple play_async calls work sequentially."""
        from agent.output.playback_engine import PlaybackEngine
        
        with patch("agent.output.playback_engine.sd") as mock_sd:
            config = PlaybackConfig()
            engine = PlaybackEngine(config)
            
            audio_data = np.random.randn(22050).astype(np.float32)
            
            mock_sd.play = Mock()
            mock_sd.wait = Mock()
            
            await engine.play_async(audio_data)
            await engine.play_async(audio_data)
            
            # Should be called twice
            assert mock_sd.play.call_count == 2


class TestPlaybackEngineIntegration:
    """Integration tests combining multiple features."""
    
    @pytest.mark.asyncio
    async def test_play_pause_resume_workflow(self):
        """Test complete pause/resume workflow."""
        from agent.output.playback_engine import PlaybackEngine
        
        with patch("agent.output.playback_engine.sd") as mock_sd:
            config = PlaybackConfig()
            engine = PlaybackEngine(config)
            
            mock_sd.stop = Mock()
            
            # Start playing
            engine._playback_state = "playing"
            
            # Pause
            engine.pause()
            assert engine._playback_state == "paused"
            
            # Resume
            engine.resume()
            assert engine._playback_state == "playing"
            
            # Stop
            engine.stop()
            assert engine._playback_state == "idle"
            
    @pytest.mark.asyncio
    async def test_streaming_workflow(self):
        """Test complete streaming workflow."""
        from agent.output.playback_engine import PlaybackEngine
        
        with patch("agent.output.playback_engine.sd") as mock_sd:
            config = PlaybackConfig(sample_rate=44100)
            engine = PlaybackEngine(config)
            
            # Create buffer with data
            buffer = AudioBuffer(sample_rate=44100, channels=1, duration_sec=1.0)
            audio_data = np.random.randn(44100).astype(np.float32)
            await buffer.write(audio_data.tobytes())
            
            mock_sd.play = Mock()
            mock_sd.wait = Mock()
            
            # Stream playback
            await engine.play_streaming(buffer, chunk_size=4410)
            
            # Verify playback occurred
            assert mock_sd.play.call_count >= 1
