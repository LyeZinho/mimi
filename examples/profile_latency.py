"""Latency profiler for audio input pipeline."""

import asyncio
import numpy as np
import time
import logging
from statistics import mean, stdev
from agent.orchestrator import AgentOrchestrator
from agent.audio import VADEngine, STTEngine, AudioCapture

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def profile_vad_latency():
    """Profile VAD latency."""
    vad = VADEngine(aggressiveness=2, sample_rate=16000)
    
    frame_size = vad.get_frame_size()
    test_audio = np.zeros(frame_size, dtype=np.int16).tobytes()
    
    latencies = []
    for _ in range(100):
        start = time.perf_counter()
        vad.is_speech(test_audio)
        latencies.append((time.perf_counter() - start) * 1000)
    
    logger.info(f"VAD latency: avg={mean(latencies):.2f}ms, "
                f"min={min(latencies):.2f}ms, max={max(latencies):.2f}ms, "
                f"std={stdev(latencies):.2f}ms")
    return mean(latencies) < 10


async def profile_stt_latency():
    """Profile STT latency (cold start + inference)."""
    stt = STTEngine(model_size="tiny", device="cpu", language="pt")
    
    await stt.initialize()
    
    test_audio = np.zeros(16000, dtype=np.int16).tobytes()
    
    start = time.perf_counter()
    result = await stt.transcribe(test_audio)
    latency_ms = (time.perf_counter() - start) * 1000
    
    logger.info(f"STT latency (silence): {latency_ms:.2f}ms")
    stt.shutdown()
    
    return latency_ms < 5000


async def profile_orchestrator_latency():
    """Profile full orchestrator pipeline latency."""
    orchestrator = AgentOrchestrator()
    await orchestrator.initialize()
    await orchestrator.start()
    
    input_brain = orchestrator.brains[0]
    
    test_audio = np.zeros(1024, dtype=np.int16).tobytes()
    
    latencies = []
    for _ in range(10):
        start = time.perf_counter()
        await input_brain.handle_audio_frame(test_audio)
        latencies.append((time.perf_counter() - start) * 1000)
    
    avg_latency = mean(latencies)
    logger.info(f"Orchestrator latency: avg={avg_latency:.2f}ms, "
                f"min={min(latencies):.2f}ms, max={max(latencies):.2f}ms")
    
    await orchestrator.stop()
    
    return avg_latency < 100


async def main():
    """Run all latency profilers."""
    logger.info("=== Audio Input Pipeline Latency Profiling ===")
    
    logger.info("\n1. VAD Latency Test...")
    vad_ok = await profile_vad_latency()
    
    logger.info("\n2. STT Latency Test...")
    stt_ok = await profile_stt_latency()
    
    logger.info("\n3. Orchestrator Latency Test...")
    orch_ok = await profile_orchestrator_latency()
    
    logger.info("\n=== Results ===")
    logger.info(f"VAD (<10ms):              {'PASS' if vad_ok else 'FAIL'}")
    logger.info(f"STT (<5000ms):            {'PASS' if stt_ok else 'FAIL'}")
    logger.info(f"Orchestrator (<100ms):    {'PASS' if orch_ok else 'FAIL'}")
    
    if all([vad_ok, stt_ok, orch_ok]):
        logger.info("\nAll latency targets PASSED")
        return 0
    else:
        logger.warning("\nSome latency targets FAILED")
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
