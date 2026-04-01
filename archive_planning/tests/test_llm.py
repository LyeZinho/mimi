"""Tests for LLMClient."""

import json
import pytest
from unittest.mock import AsyncMock, patch
from agent.llm.client import LLMClient

@pytest.fixture
def llm_client():
    return LLMClient()

@pytest.mark.asyncio
async def test_parse_intent_valid_json(llm_client):
    valid_json_resp = 'Here is the JSON: {"intent": "speak", "text": "Hi"}'
    
    # Mock _chat to avoid network call
    with patch.object(llm_client, '_chat', new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = valid_json_resp
        
        intent = await llm_client.get_intent("Input", [], {})
        assert intent["intent"] == "speak"
        assert intent["text"] == "Hi"

@pytest.mark.asyncio
async def test_parse_intent_fallback(llm_client):
    plain_text_resp = "Just some plain text response."
    
    with patch.object(llm_client, '_chat', new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = plain_text_resp
        
        intent = await llm_client.get_intent("Input", [], {})
        # Should fallback to speak intent
        assert intent["intent"] == "speak"
        assert intent["text"] == "Just some plain text response."
        assert intent["emotion"] == "neutral"

@pytest.mark.asyncio
async def test_parse_intent_malformed_json_fallback(llm_client):
    malformed_resp = '{"intent": "speak", "text": "Broken...'
    
    with patch.object(llm_client, '_chat', new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = malformed_resp
        
        intent = await llm_client.get_intent("Input", [], {})
        # Should fallback
        assert intent["intent"] == "speak"
