"""Brain health check system for startup verification."""

import asyncio
import logging
from typing import Dict, Literal, Any

from agent.core.messaging import EventBus

logger = logging.getLogger(__name__)

Status = Literal["operational", "failed", "timeout"]


class BrainHealthCheck:
    """Health check system for all 7 brains."""

    def __init__(self, bus: EventBus):
        """Initialize with EventBus reference."""
        self.bus = bus
        self.results: Dict[str, Dict] = {}

    async def run(self, brains: Dict[str, Any], timeout: int = 10) -> bool:
        """Run all brain health checks in parallel.

        Args:
            brains: Dict mapping brain names to brain instances
            timeout: Seconds to wait per brain before timing out

        Returns:
            True if all brains operational, False if any failed/timed out
        """
        self.results = {}

        # Create tasks for all brain health checks
        tasks = {
            name: asyncio.create_task(
                asyncio.wait_for(brain.health_check(), timeout=timeout)
            )
            for name, brain in brains.items()
        }

        # Gather all results
        try:
            results = await asyncio.gather(*tasks.values(), return_exceptions=True)
            for brain_name, result in zip(tasks.keys(), results):
                if isinstance(result, asyncio.TimeoutError):
                    self.results[brain_name] = {
                        "name": brain_name,
                        "status": "timeout",
                        "details": f"Health check timed out after {timeout}s",
                    }
                elif isinstance(result, Exception):
                    self.results[brain_name] = {
                        "name": brain_name,
                        "status": "failed",
                        "details": str(result),
                    }
                else:
                    self.results[brain_name] = result
        except Exception as e:
            logger.error(f"Critical error during health check: {e}")
            return False

        # Log results
        for brain_name, result in self.results.items():
            status = result.get("status", "unknown")
            details = result.get("details", "")
            if status == "operational":
                logger.info(f"✓ {brain_name:20} operational - {details}")
            elif status == "timeout":
                logger.warning(f"⚠ {brain_name:20} timeout - {details}")
            else:
                logger.error(f"✗ {brain_name:20} failed - {details}")

        # Check if all operational
        all_operational = all(
            result.get("status") == "operational" for result in self.results.values()
        )

        return all_operational
