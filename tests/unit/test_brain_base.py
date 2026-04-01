import pytest
from agent.brains.base import BrainBase, BrainRegistry

class EchoBrain(BrainBase):
    name = "echo"
    async def run(self, context: dict) -> dict:
        return {**context, "echo": True}

@pytest.mark.asyncio
async def test_brain_run():
    brain = EchoBrain()
    result = await brain.run({"input": "hello"})
    assert result["echo"] is True
    assert result["input"] == "hello"

def test_registry_register_and_get():
    registry = BrainRegistry()
    brain = EchoBrain()
    registry.register(brain)
    assert registry.get("echo") is brain

def test_registry_get_unknown_raises():
    registry = BrainRegistry()
    with pytest.raises(KeyError):
        registry.get("unknown")

@pytest.mark.asyncio
async def test_registry_run_pipeline():
    registry = BrainRegistry()
    registry.register(EchoBrain())
    ctx = {"value": 1}
    result = await registry.run_pipeline(["echo"], ctx)
    assert result["echo"] is True
