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


@pytest.mark.asyncio
async def test_health_check_all_brains():
    """Health check should verify all brains are operational."""
    from agent.orchestrator import AgentOrchestrator
    from agent.llm.ollama_provider import OllamaProvider
    from agent.llm.config import OllamaConfig

    config = OllamaConfig(provider="ollama", model="phi3:mini")
    llm_provider = OllamaProvider(config)
    orchestrator = AgentOrchestrator(llm_provider=llm_provider)

    health_check = BrainHealthCheck(orchestrator.bus)

    brains = {
        "InputBrain": orchestrator.input_brain,
        "ReasoningBrain": orchestrator.reasoning_brain,
        "PlanningBrain": orchestrator.planning_brain,
        "ExecutionBrain": orchestrator.execution_brain,
        "SentimentBrain": orchestrator.sentiment_brain,
        "AvatarBrain": orchestrator.avatar_brain,
        "OutputBrain": orchestrator.output_brain,
    }

    results = await health_check.run(brains, timeout=5)

    assert len(health_check.results) == 7

    for brain_name, result in health_check.results.items():
        assert "status" in result
        assert result["status"] in ["operational", "failed", "timeout"]
        assert "details" in result

