"""
Example: Simple test of 7-brain orchestrator with audio streaming

Run:
    python examples/test_orchestrator.py
"""

import asyncio
import logging

from agent.orchestrator import AgentOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s'
)

logger = logging.getLogger(__name__)


async def main():
    orchestrator = AgentOrchestrator(
        user_id="user_demo",
        session_id="session_demo_1"
    )
    
    logger.info("Initializing orchestrator...")
    await orchestrator.initialize()
    
    logger.info("Starting orchestrator...")
    await orchestrator.start()
    
    logger.info("Sending text input: 'Olá Mimi, como vai?'")
    await orchestrator.process_text_input("Olá Mimi, como vai?")
    
    await asyncio.sleep(3.0)
    
    metrics = await orchestrator.get_metrics()
    
    logger.info("=== METRICS ===")
    logger.info(f"Session: {metrics['session_id']}")
    logger.info(f"Running: {metrics['running']}")
    logger.info(f"Brains:")
    for brain_id, brain_metrics in metrics['brains'].items():
        logger.info(
            f"  {brain_id}: "
            f"{brain_metrics['events_processed']} events, "
            f"avg latency {brain_metrics['avg_latency_ms']:.1f}ms"
        )
    
    logger.info("\n=== EVENT HISTORY ===")
    history = await orchestrator.get_event_history(limit=20)
    for event in history:
        logger.info(f"  {event['type']:30} from {event['source']:20}")
    
    logger.info("Shutting down...")
    await orchestrator.stop()
    
    logger.info("Done!")


if __name__ == "__main__":
    asyncio.run(main())
