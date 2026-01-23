
import pytest
from unittest.mock import AsyncMock, MagicMock
from agent.core.agent import AgentCore
from agent.core.memory import Memory
from agent.core.state import AgentState

@pytest.mark.asyncio
async def test_agent_conversation_flow():
    # Setup dependencies
    mock_llm = AsyncMock()
    # Mock LLM returning a structured intent
    mock_llm.get_intent.return_value = {
        "intent": "speak",
        "text": "Hello user!",
        "emotion": "happy"
    }
    
    mock_router = AsyncMock()
    mock_router.execute.return_value = {"status": "executed"}
    
    memory = Memory(short_term_limit=5)
    state = AgentState()
    
    agent = AgentCore(llm=mock_llm, router=mock_router, memory=memory, state=state)
    
    # Execute input
    user_input = "Hi there"
    result = await agent.handle_input(user_input, source="text")
    
    # Verify Memory
    recent = memory.recent()
    assert len(recent) >= 2
    assert recent[0].content == user_input
    assert recent[0].role == "user"
    assert recent[1].content == "Hello user!"
    assert recent[1].role == "assistant"
    
    # Verify LLM call
    mock_llm.get_intent.assert_called_once()
    
    # Verify Router call
    mock_router.execute.assert_called_once()
    assert result["status"] == "executed"
