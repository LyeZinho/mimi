"""Main entry point for real-time audio input pipeline."""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.orchestrator import AgentOrchestrator
from agent.audio import AudioCapture

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Run real-time audio input pipeline."""
    
    orchestrator = AgentOrchestrator()
    await orchestrator.initialize()
    await orchestrator.start()
    
    input_brain = orchestrator.brains["input"]
    
    audio_capture = AudioCapture(
        sample_rate=16000,
        channels=1,
        chunk_size=1024,
        callback=input_brain.handle_audio_frame
    )
    
    try:
        logger.info("Starting audio capture... (Press Ctrl+C to stop)")
        await audio_capture.start()
        
        while True:
            await asyncio.sleep(1)
            metrics = orchestrator.get_metrics()
            
            if metrics and "input" in metrics:
                input_metrics = metrics["input"]
                logger.info(
                    f"Input Brain - Events: {input_metrics.get('event_count', 0)}, "
                    f"Latency: {input_metrics.get('avg_latency_ms', 0):.1f}ms"
                )
    
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await audio_capture.stop()
        await orchestrator.stop()
        logger.info("Pipeline stopped")


if __name__ == "__main__":
    asyncio.run(main())
