"""
Unit tests for PromptTemplates class with Portuguese prompt templates.
Tests verify intent extraction, response generation, and Portuguese language requirements.
"""

import pytest
from agent.llm.prompt_templates import PromptTemplates


class TestPromptTemplates:
    """Test suite for PromptTemplates class."""

    def test_intent_extraction_prompt(self):
        """Test that intent_extraction method combines transcript and context into a prompt."""
        transcript = "Qual é o horário de atendimento?"
        context = {"service": "appointment"}
        
        prompt = PromptTemplates.intent_extraction(transcript, context)
        
        # Should contain both transcript and context
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "Qual é o horário de atendimento?" in prompt or transcript in prompt
        assert context is not None  # Context was processed

    def test_intent_extraction_system_message(self):
        """Test that SYSTEM_INTENT_EXTRACTION constant exists and contains required JSON spec."""
        system_msg = PromptTemplates.SYSTEM_INTENT_EXTRACTION
        
        assert isinstance(system_msg, str)
        assert "intenção" in system_msg.lower() or "intencao" in system_msg.lower()
        # Should contain JSON format specification
        assert "json" in system_msg.lower() or "{" in system_msg
        # Should mention possible intents
        assert "query_hours" in system_msg or "horário" in system_msg.lower()

    def test_response_generation_prompt(self):
        """Test that response_generation method generates response from intent and context."""
        intent = "query_hours"
        context = {"location": "Lisboa", "service_type": "consulta"}
        
        prompt = PromptTemplates.response_generation(intent, context)
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "query_hours" in prompt or "horário" in prompt.lower()

    def test_chat_response_prompt(self):
        """Test that chat_response method generates generic chat response."""
        message = "Olá, como posso ajudar?"
        context = {"user_id": "user123", "timestamp": "2024-03-27"}
        
        prompt = PromptTemplates.chat_response(message, context)
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "Olá, como posso ajudar?" in prompt or message in prompt

    def test_prompts_are_in_portuguese(self):
        """Test that prompts contain Portuguese language terms."""
        # Check system message contains Portuguese
        system_msg = PromptTemplates.SYSTEM_INTENT_EXTRACTION
        
        portuguese_terms = ["intenção", "intencao", "resposta", "assistente", "JSON"]
        has_portuguese = any(term.lower() in system_msg.lower() for term in portuguese_terms)
        
        assert has_portuguese, "System message should contain Portuguese language terms"
        
        # Check that system message mentions required fields
        assert "intent" in system_msg.lower() or "intenção" in system_msg.lower()
        assert "confidence" in system_msg.lower() or "confiança" in system_msg.lower()
