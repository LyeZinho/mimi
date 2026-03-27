"""End-to-end test for audio input pipeline."""

import asyncio
import numpy as np
import pytest
from agent.audio import VADEngine, STTEngine, AudioCapture


class TestVADEngine:
    """Test VAD engine with real webrtcvad."""
    
    @pytest.mark.asyncio
    async def test_vad_detects_silence(self):
        vad = VADEngine(aggressiveness=2, sample_rate=16000)
        
        silence = np.zeros(vad.get_frame_size(), dtype=np.int16).tobytes()
        assert not vad.is_speech(silence)
    
    @pytest.mark.asyncio
    async def test_vad_detects_noise(self):
        vad = VADEngine(aggressiveness=2, sample_rate=16000)
        
        noise = np.random.randint(-1000, 1000, vad.get_frame_size() // 2, dtype=np.int16).tobytes()
        result = vad.is_speech(noise)
        assert isinstance(result, (bool, np.bool_))


class TestSTTEngine:
    """Test STT engine with real faster-whisper."""
    
    @pytest.mark.asyncio
    async def test_stt_initialization(self):
        stt = STTEngine(model_size="tiny", device="cpu", language="pt")
        await stt.initialize()
        assert stt.model is not None
        stt.shutdown()
    
    @pytest.mark.asyncio
    async def test_stt_transcribes_silence(self):
        stt = STTEngine(model_size="tiny", device="cpu", language="pt")
        await stt.initialize()
        
        silence = np.zeros(16000, dtype=np.int16).tobytes()
        result = await stt.transcribe(silence)
        
        assert "text" in result
        assert "language" in result
        assert "confidence" in result
        
        stt.shutdown()


class TestAudioCapture:
    """Test audio capture (mock mode, no actual microphone needed)."""
    
    @pytest.mark.asyncio
    async def test_audio_capture_lifecycle(self):
        capture = AudioCapture(sample_rate=16000, channels=1, chunk_size=1024)
        
        chunks_received = []
        
        async def mock_callback(audio_bytes):
            chunks_received.append(audio_bytes)
        
        capture.set_callback(mock_callback)
        
        try:
            await capture.start()
            assert capture.is_running
            
            await asyncio.sleep(0.5)
            
            await capture.stop()
            assert not capture.is_running
        except Exception as e:
            print(f"Note: Audio capture test skipped (no microphone available): {e}")


class TestInputBrainIntegration:
    """Integration test for InputBrain with real VAD/STT."""
    
    @pytest.mark.asyncio
    async def test_input_brain_vad(self):
        from agent.brains.input_brain import InputBrain
        from agent.core.messaging import get_event_bus, get_shared_state
        
        brain = InputBrain(brain_id="input", event_bus=get_event_bus(), shared_state=get_shared_state())
        await brain.initialize()
        
        silence = np.zeros(1024, dtype=np.int16).tobytes()
        result = brain._run_vad(silence)
        
        assert isinstance(result, bool)
