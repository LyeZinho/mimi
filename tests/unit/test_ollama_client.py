import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from agent.llm.ollama_client import OllamaClient

@pytest.mark.asyncio
async def test_generate_returns_text():
    client = OllamaClient(host="http://fake:11434", model="test")
    mock_response = MagicMock()
    mock_response.json = AsyncMock(return_value={
        "message": {"content": "Hello there"}
    })
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
        result = await client.generate(messages=[{"role": "user", "content": "hi"}])
    
    assert result == "Hello there"
    mock_post.assert_called_once()

@pytest.mark.asyncio
async def test_generate_includes_system_prompt():
    client = OllamaClient(host="http://fake:11434", model="test", system_prompt="You are Mimi.")
    mock_response = MagicMock()
    mock_response.json = AsyncMock(return_value={"message": {"content": "Hi!"}})
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
        await client.generate(messages=[{"role": "user", "content": "hello"}])

    call_args = mock_post.call_args
    body = call_args.kwargs.get("json", call_args.args[1] if len(call_args.args) > 1 else {})
    messages = body["messages"]
    assert messages[0]["role"] == "system"
    assert "Mimi" in messages[0]["content"]
