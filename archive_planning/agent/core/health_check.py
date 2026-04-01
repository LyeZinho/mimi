"""Brain health check system for startup verification."""

import asyncio
import logging
from typing import Any, Literal

from agent.core.messaging import EventBus

logger = logging.getLogger(__name__)

Status = Literal["operational", "failed", "timeout"]


class BrainHealthCheck:
    """Health check system for all 7 brains."""

    def __init__(self, bus: EventBus):
        """Initialize with EventBus reference."""
        self.bus = bus
        self.results: dict[str, dict] = {}

    async def run(self, brains: dict[str, Any], timeout: int = 10) -> bool:
        """Run all brain health checks in parallel.

        Args:
            brains: Dict mapping brain names to brain instances
            timeout: Seconds to wait per brain before timing out

        Returns:
            True if all brains operational, False if any failed/timed out
        """
        self.results = {}

        logger.debug(f"Starting health checks for {len(brains)} brains...")

        async def check_brain_with_logging(
            name: str, brain: Any, timeout: int
        ) -> tuple[str, Any]:
            """Wrapper to log individual brain health check results."""
            logger.debug(f"[HC] Starting {name}...")
            try:
                result = await asyncio.wait_for(
                    brain.health_check(), timeout=timeout
                )
                logger.debug(f"[HC] {name} complete: {result.get('status')}")
                return (name, result)
            except asyncio.TimeoutError:
                logger.warning(f"[HC] {name} timed out after {timeout}s")
                return (name, asyncio.TimeoutError())
            except Exception as e:
                logger.error(f"[HC] {name} error: {e}")
                return (name, e)

        # Create tasks for all brain health checks
        task_list = []
        for name, brain in brains.items():
            task = asyncio.create_task(check_brain_with_logging(name, brain, timeout))
            task_list.append(task)

        logger.debug(f"Created {len(task_list)} health check tasks, starting gather...")

        # Gather all results
        try:
            logger.debug(f"Awaiting gather of {len(task_list)} tasks...")
            results = await asyncio.gather(*task_list, return_exceptions=True)
            logger.debug(f"Received results from {len(results)} tasks, processing...")
            
            for task_result in results:
                if isinstance(task_result, tuple) and len(task_result) == 2:
                    brain_name, result = task_result
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
            logger.error(f"Critical error during health check: {e}", exc_info=True)
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
