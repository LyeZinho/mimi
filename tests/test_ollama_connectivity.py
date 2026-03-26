"""Test Ollama connectivity with API key."""
import pytest
import asyncio
from agent.llm.client import LLMClient
from agent.config import OLLAMA_HOST, OLLAMA_API_KEY, LLM_MODEL


@pytest.mark.asyncio
async def test_ollama_api_connectivity():
    """Verify we can connect to Ollama API with provided key."""
    if not OLLAMA_API_KEY:
        pytest.skip("No OLLAMA_API_KEY in .env")
    
    try:
        import socket
        socket.create_connection(("api.ollama.ai", 443), timeout=2)
    except (socket.timeout, socket.gaierror, ConnectionRefusedError):
        pytest.skip("Cannot reach api.ollama.ai — network unavailable or service down")
    
    client = LLMClient(model=LLM_MODEL, base_url=OLLAMA_HOST)
    try:
        result = await client.get_intent(
            user_message="Hello, are you working?",
            history=[],
            state={"mood": "neutral"},
            context=None,
            tools=None
        )
        assert "intent" in result
        assert result["intent"] in ["speak", "use_tool", "ask_clarification"]
        print(f"✓ Ollama responded: {result}")
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_ollama_tool_recognition():
    """Verify LLM can recognize tool-use intent."""
    if not OLLAMA_API_KEY:
        pytest.skip("No OLLAMA_API_KEY in .env")
    
    try:
        import socket
        socket.create_connection(("api.ollama.ai", 443), timeout=2)
    except (socket.timeout, socket.gaierror, ConnectionRefusedError):
        pytest.skip("Cannot reach api.ollama.ai — network unavailable or service down")
    
    client = LLMClient(model=LLM_MODEL, base_url=OLLAMA_HOST)
    try:
        result = await client.get_intent(
            user_message="What's the weather in Lisbon?",
            history=[],
            state={"mood": "neutral"},
            context=None,
            tools=[
                {
                    "name": "weather",
                    "description": "Get weather for a location"
                }
            ]
        )
        assert "intent" in result
        print(f"✓ LLM intent: {result['intent']}")
    finally:
        await client.close()

