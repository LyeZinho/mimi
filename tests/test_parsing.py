import pytest
from unittest.mock import MagicMock
from agent.llm.client import LLMClient

@pytest.fixture
def client():
    return LLMClient()

def test_parse_clean_json(client):
    raw = '{"intent": "speak", "text": "Hello"}'
    res = client._parse_intent(raw)
    assert res["intent"] == "speak"
    assert res["text"] == "Hello"

def test_parse_markdown_json(client):
    raw = 'Here is the response:\n```json\n{\n  "intent": "speak",\n  "text": "Hello"\n}\n```'
    res = client._parse_intent(raw)
    assert res["intent"] == "speak"
    assert res["text"] == "Hello"

def test_parse_multiple_jsons_picks_first_valid(client):
    # Case where model outputs multiple JSONs or garbage
    raw = '''
    Thinking...
    { "intent": "speak", "text": "First" }
    
    Explanation:
    { "other": "stuff" }
    '''
    res = client._parse_intent(raw)
    assert res["intent"] == "speak"
    assert res["text"] == "First"

def test_parse_garbage_fallback(client):
    raw = "Just plain text response."
    res = client._parse_intent(raw)
    assert res["intent"] == "speak"
    assert res["text"] == "Just plain text response."
