# tests/unit/test_brain_health_check.py
import pytest
from agent.core.health_check import BrainHealthCheck
from agent.core.messaging import EventBus


@pytest.mark.asyncio
async def test_brain_health_check_init():
    """BrainHealthCheck should initialize with EventBus reference."""
    bus = EventBus()
    health_check = BrainHealthCheck(bus)
    assert health_check.bus is bus
    assert health_check.results == {}
