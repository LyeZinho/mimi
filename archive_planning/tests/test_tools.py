import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from agent.tools.registry import ToolRegistry
from agent.tools.search import SearchTool
from agent.tools.weather import WeatherTool
from agent.core.agent import AgentCore
from agent.llm.client import LLMClient
from agent.output.actions import ActionRouter

@pytest.fixture
def registry():
    return ToolRegistry()

@pytest.mark.asyncio
async def test_search_tool_mocked(registry):
    # Mock DDGS
    with patch("agent.tools.search.DDGS") as mock_ddgs:
        instance = mock_ddgs.return_value
        instance.text.return_value = [{"title": "Test Result", "body": "Content"}]
        
        tool = registry.get_tool("search")
        result = await tool.execute("query")
        assert "Test Result" in result

@pytest.mark.asyncio
async def test_weather_tool_mocked(registry):
    # Mock httpx
    with patch("httpx.AsyncClient") as mock_client:
        mock_get = AsyncMock()
        mock_client.return_value.__aenter__.return_value.get = mock_get
        
        # Responses for Geocoding and Weather
        mock_get.side_effect = [
            MagicMock(json=lambda: {"results": [{"latitude": 10, "longitude": 20, "name": "City"}]}),
            MagicMock(json=lambda: {"current": {"temperature_2m": 25.5}})
        ]
        
        tool = registry.get_tool("weather")
        result = await tool.execute("City")
        assert "Clima em City" in result
        assert "25.5°C" in result

@pytest.mark.asyncio
async def test_agent_tool_loop():
    # Setup components
    llm = MagicMock(spec=LLMClient)
    # 1st call: use_tool, 2nd call: speak
    llm.get_intent = AsyncMock(side_effect=[
        {"intent": "use_tool", "tool": "search", "tool_input": "cats"},
        {"intent": "speak", "text": "Cats are great"}
    ])
    
    registry = ToolRegistry()
    registry.get_tool = MagicMock()
    mock_tool = MagicMock()
    mock_tool.execute = AsyncMock(return_value="Search results form cats")
    registry.get_tool.return_value = mock_tool
    
    router = ActionRouter() # Uses dummy tts
    agent = AgentCore(llm=llm, router=router, registry=registry)
    
    # Run
    await agent.handle_input("Tell me about cats")
    
    # Verify loop
    assert llm.get_intent.call_count == 2
    mock_tool.execute.assert_called_with("cats")
    # Verify result added to memory
    last_memory = agent.memory.recent(1)[0]
    assert last_memory.role == "assistant" # Final response
