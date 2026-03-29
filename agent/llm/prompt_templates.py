"""
Prompt templates for LLM interactions in Portuguese.
Provides static methods for generating prompts for intent extraction, response generation, and chat.
"""

import json
from typing import Any, Dict, Optional


class PromptTemplates:
    """
    Static prompt template provider with Portuguese language support.
    Offers methods for generating structured prompts for LLM interactions.
    """

    SYSTEM_INTENT_EXTRACTION = """Você é um assistente inteligente responsável por extrair a intenção de um usuário a partir de uma transcrição e contexto.

Sua tarefa é analisar o texto fornecido e retornar um JSON estruturado com os seguintes campos:
- intent: A intenção detectada (string)
- confidence: Nível de confiança da extração (float entre 0 e 1)
- parameters: Parâmetros adicionais extraídos (objeto JSON)
- sentiment: Sentimento detectado (positivo, neutro, negativo)

Possíveis intenções:
- query_hours: Consulta sobre horários de atendimento
- query_services: Consulta sobre serviços oferecidos
- query_location: Consulta sobre localização
- query_price: Consulta sobre preços
- query_contact: Consulta sobre informações de contato
- make_appointment: Desejo de fazer uma marcação/agendamento
- make_complaint: Fazer uma reclamação ou relatar problema
- greeting: Saudação inicial
- farewell: Despedida
- other: Outra intenção não categorizada

Retorne APENAS o JSON estruturado, sem explicações adicionais."""

    @staticmethod
    def intent_extraction(transcript: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a prompt for intent extraction from a user transcript.

        Args:
            transcript: The user's spoken or typed message
            context: Optional context dictionary with user session data

        Returns:
            A formatted prompt string combining transcript and context
        """
        context_str = ""
        if context:
            context_str = f"\n\nContexto adicional:\n{json.dumps(context, ensure_ascii=False, indent=2)}"

        prompt = f"""Analise a seguinte mensagem do usuário e extraia a intenção:

Mensagem: {transcript}{context_str}

Retorne o JSON com a intenção extraída."""

        return prompt

    @staticmethod
    def response_generation(intent: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a prompt for creating a response based on detected intent.

        Args:
            intent: The detected intent from the user
            context: Optional context dictionary with user session data

        Returns:
            A formatted prompt string for response generation
        """
        context_str = ""
        if context:
            context_str = f"\n\nContexto da sessão:\n{json.dumps(context, ensure_ascii=False, indent=2)}"

        prompt = f"""Gere uma resposta apropriada para o usuário com base na seguinte intenção:

Intenção detectada: {intent}{context_str}

Forneça uma resposta em português clara, concisa e amigável que atenda à intenção do usuário."""

        return prompt

    @staticmethod
    def chat_response(message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a prompt for generic chat response without explicit intent analysis.

        Args:
            message: The user's message
            context: Optional context dictionary with user session data

        Returns:
            A formatted prompt string for chat response generation
        """
        context_str = ""
        if context:
            context_str = f"\n\nContexto:\n{json.dumps(context, ensure_ascii=False, indent=2)}"

        prompt = f"""Você é um assistente amigável e útil. Responda à seguinte mensagem do usuário de forma apropriada e educada:

Mensagem do usuário: {message}{context_str}

Forneça uma resposta concisa e útil em português."""

        return prompt

    @staticmethod
    def response_generation_simple(transcript: str, intent: str, context: Optional[Dict[str, Any]] = None, user_profile: Optional[str] = None) -> str:
        """Generate a prompt for simple response generation with optional context.

        Args:
            transcript: The user's message
            intent: The detected intent
            context: Optional context dictionary with conversation history
            user_profile: Optional user profile summary for personalization

        Returns:
            A formatted prompt string for response generation
        """
        context_str = ""
        if context and context.get("conversation_history"):
            context_str = f"\n\nHistorico da conversacao:\n{context['conversation_history']}"
        
        profile_str = ""
        if user_profile:
            profile_str = f"\n{user_profile}"

        prompt = f"""Voce é um assistente inteligente e amigável. Responda a seguinte mensagem do usuario.{profile_str}

Mensagem do usuario: {transcript}
Intencao detectada: {intent}{context_str}

Forneça uma resposta concisa, natural e util em português."""

        return prompt
