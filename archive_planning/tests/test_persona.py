import json
import pytest
from unittest.mock import patch, mock_open
from agent.llm.prompts import build_system_prompt, build_user_prompt

FAKE_PERSONA = {
    "name": "TestBot",
    "description": "A test bot",
    "instructions": ["Rule 1", "Rule 2"],
    "intents": ["speak"],
    "emotions": ["neutral"],
    "max_history_items": 2
}

@patch("agent.llm.prompts.load_persona", return_value=FAKE_PERSONA)
def test_build_system_prompt_uses_persona(mock_load):
    state = {"mood": "neutral"}
    prompt = build_system_prompt(state)
    
    assert "Você é TestBot" in prompt
    assert "A test bot" in prompt
    assert "1. Rule 1" in prompt
    assert "2. Rule 2" in prompt
    assert "Intents disponíveis: speak" in prompt

@patch("agent.llm.prompts.load_persona", return_value=FAKE_PERSONA)
def test_build_user_prompt_respects_limit(mock_load):
    history = [
        {"role": "user", "content": "1"},
        {"role": "user", "content": "2"},
        {"role": "user", "content": "3"},
        {"role": "user", "content": "4"}
    ]
    
    prompt = build_user_prompt("hello", history)
    
    # Should only contain last 2 items (3 and 4)
    assert "[user] 3" in prompt
    assert "[user] 4" in prompt
    assert "[user] 2" not in prompt
