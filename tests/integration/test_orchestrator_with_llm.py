"""
Integration test: Orchestrator with LLM provider.

Tests that AgentOrchestrator correctly initializes, starts, and stops
with a custom LLM provider injected into the ReasoningBrain.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from agent.orchestrator import AgentOrchestrator
from agent.llm.provider import LLMProvider


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLMProvider with generate returning JSON response."""
    provider = AsyncMock(spec=LLMProvider)
    provider.generate = AsyncMock(
        return_value='{"intent": "query_hours", "confidence": 0.95, "parameters": {}}'
    )
    return provider


@pytest.mark.asyncio
async def test_orchestrator_with_custom_llm(mock_llm_provider):
    """
    Test orchestrator lifecycle with custom LLM provider.
    
    Steps:
    1. Create mock LLMProvider returning JSON response
    2. Create AgentOrchestrator
    3. Inject mock provider into orchestrator.brains[1] (ReasoningBrain)
    4. Call await orchestrator.initialize()
    5. Call await orchestrator.start()
    6. Get orchestrator.brains[0] (InputBrain)
    7. Call await orchestrator.stop()
    8. Verify no errors
    """
    # Create orchestrator
    orchestrator = AgentOrchestrator(user_id="test_user", session_id="test_session")
    
    # Inject mock LLM provider into ReasoningBrain (index 1)
    orchestrator.brains[1].llm_provider = mock_llm_provider
    
    # Initialize orchestrator
    await orchestrator.initialize()
    
    # Start orchestrator
    await orchestrator.start()
    
    # Get InputBrain (index 0)
    input_brain = orchestrator.brains[0]
    assert input_brain is not None
    assert input_brain.brain_id == "input_brain"
    
    # Stop orchestrator
    await orchestrator.stop()
    
    # Verify no errors occurred
    assert orchestrator._running is False
