"""Templates de prompts para o LLM."""

from __future__ import annotations

from typing import Any

import json
from pathlib import Path
from agent.config import PERSONA_PATH

# Carrega persona (pode ser cacheada ou recarregada a cada chamada)
def load_persona() -> dict[str, Any]:
    if not PERSONA_PATH.exists():
        return {}
    with open(PERSONA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def build_system_prompt(state: dict[str, Any], tools: list[dict[str, Any]] | None = None) -> str:
    persona = load_persona()
    
    name = persona.get("name", "Mimi")
    desc = persona.get("description", "agente")
    instructions = persona.get("instructions", [])
    intents = persona.get("intents", [])
    emotions = persona.get("emotions", [])
    
    instructions_text = "\n".join([f"{i+1}. {rule}" for i, rule in enumerate(instructions)])
    intents_text = ", ".join(intents)
    emotions_text = ", ".join(emotions)

    tools_text = ""
    if tools:
        tools_list = []
        for t in tools:
            tools_list.append(f"- {t['name']}: {t['description']}")
        tools_block = "\n".join(tools_list)
        tools_text = (
            f"\nFerramentas disponíveis:\n{tools_block}\n"
            "Para usar, retorne JSON ESTRITAMENTE neste formato:\n"
            '{{"intent": "use_tool", "tool": "nome_da_ferramenta", "tool_input": "entrada em texto simples"}}\n'
            'Exemplo: {{"intent": "use_tool", "tool": "weather", "tool_input": "São Paulo"}}\n'
        )
    
    template = f"""\
Você é {name}, um {desc}.

Regras:
{instructions_text}
{len(instructions)+1}. Intents disponíveis: {intents_text}.
{len(instructions)+2}. Emoções: {emotions_text}.
{tools_text}
Estado atual do agente:
{{state_json}}
"""
    return template.format(state_json=json.dumps(state, ensure_ascii=False, indent=2))


def build_user_prompt(
    user_message: str,
    history: list[dict[str, Any]],
    context: list[dict[str, Any]] | None = None,
) -> str:
    persona = load_persona()
    max_history = persona.get("max_history_items", 5)
    
    lines = []
    # Respeita o limite configurado
    for entry in history[-max_history:]:
        role = entry.get("role", "user")
        content = entry.get("content", "")
        lines.append(f"[{role}] {content}")
        
    history_text = "\n".join(lines) if lines else "(sem histórico)"
    
    # Formata contexto (RAG)
    context_text = ""
    if context:
        context_lines = []
        for ctx in context:
            # Mostra apenas conteúdo e role para o LLM
            c_role = ctx.get("role", "unknown")
            c_content = ctx.get("content", "")
            context_lines.append(f"- [{c_role}] {c_content}")
        context_block = "\n".join(context_lines)
        context_text = f"\nMemórias Relevantes:\n{context_block}\n"
    
    template = """\
Histórico recente:
{history_text}
{context_text}
Usuário: {user_message}

Responda em JSON:
"""
    return template.format(
        history_text=history_text, 
        context_text=context_text,
        user_message=user_message
    )
