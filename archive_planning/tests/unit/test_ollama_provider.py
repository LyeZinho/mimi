import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from agent.llm.config import OllamaConfig
from agent.llm.errors import LLMConnectionError, LLMTimeoutError
from agent.llm.provider import LLMProvider
from agent.llm.ollama_provider import OllamaProvider


class TestOllamaInheritsFromProvider:
    def test_ollama_inherits_from_provider(self):
        config = OllamaConfig(provider="ollama", model="phi3:mini", host="http://localhost:11434", temperature=0.7, top_p=0.9)
        provider = OllamaProvider(config)
        assert isinstance(provider, LLMProvider)


class TestCountTokens:
    def test_count_tokens(self):
        config = OllamaConfig(provider="ollama", model="phi3:mini", host="http://localhost:11434")
        provider = OllamaProvider(config)
        assert provider.count_tokens("hello world test") == 3
        assert provider.count_tokens("") == 0
        assert provider.count_tokens("hello  world") == 2


class TestGenerateBatchResponse:
    @pytest.mark.asyncio
    async def test_generate_batch_response(self):
        config = OllamaConfig(provider="ollama", model="phi3:mini", host="http://localhost:11434", temperature=0.7, top_p=0.9)
        
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"response": "Hello!", "prompt_eval_count": 10, "eval_count": 5})
        
        mock_session = MagicMock()
        mock_session.post = MagicMock()
        mock_session.post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.post.return_value.__aexit__ = AsyncMock(return_value=None)
        
        provider = OllamaProvider(config)
        provider.session = mock_session
        
        response = await provider.generate("Hello Ollama", stream=False)
        assert response == "Hello!"


class TestValidateConnectionFail:
    @pytest.mark.asyncio
    async def test_validate_connection_fail(self):
        config = OllamaConfig(provider="ollama", model="phi3:mini", host="http://localhost:11434")
        
        mock_response = MagicMock()
        mock_response.status = 500
        
        mock_session = MagicMock()
        mock_session.get = MagicMock()
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        
        provider = OllamaProvider(config)
        provider.session = mock_session
        
        is_valid = await provider.validate_connection()
        assert is_valid is False


class TestGenerateStreamResponse:
    @pytest.mark.asyncio
    async def test_generate_stream_response(self):
        config = OllamaConfig(provider="ollama", model="phi3:mini", host="http://localhost:11434", temperature=0.7, top_p=0.9)
        
        async def mock_content():
            chunks = [json.dumps({"response": "Hello"}).encode(), json.dumps({"response": "!", "done": True}).encode()]
            for chunk in chunks:
                yield chunk
        
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.content = mock_content()
        
        mock_session = MagicMock()
        mock_session.post = MagicMock()
        mock_session.post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.post.return_value.__aexit__ = AsyncMock(return_value=None)
        
        provider = OllamaProvider(config)
        provider.session = mock_session
        
        responses = []
        async for chunk in await provider.generate("Hello Ollama", stream=True):
            responses.append(chunk)
        assert len(responses) > 0


class TestTimeoutError:
    @pytest.mark.asyncio
    async def test_generate_timeout_error(self):
        config = OllamaConfig(provider="ollama", model="phi3:mini", host="http://localhost:11434")
        
        mock_session = MagicMock()
        mock_session.post = MagicMock(side_effect=asyncio.TimeoutError("Timeout"))
        
        provider = OllamaProvider(config)
        provider.session = mock_session
        
        with pytest.raises(LLMTimeoutError):
            await provider.generate("Hello Ollama", stream=False)


class ClientErrorMock(Exception):
    pass


class TestConnectionError:
    @pytest.mark.asyncio
    async def test_generate_connection_error(self):
        config = OllamaConfig(provider="ollama", model="phi3:mini", host="http://localhost:11434")
        
        mock_session = MagicMock()
        mock_session.post = MagicMock(side_effect=ClientErrorMock("Connection failed"))
        
        provider = OllamaProvider(config)
        provider.session = mock_session
        
        with pytest.raises(LLMConnectionError):
            await provider.generate("Hello Ollama", stream=False)
