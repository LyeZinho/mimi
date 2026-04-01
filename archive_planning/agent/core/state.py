"""Estado interno do agente."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentState:
    """Estado explícito do agente, mantido fora do prompt."""

    mood: str = "neutral"
    focus: str | None = None
    speaking: bool = False
    context: list[dict[str, Any]] = field(default_factory=list)

    # Extensível para estados customizados
    custom: dict[str, Any] = field(default_factory=dict)

    def set(self, key: str, value: Any) -> None:
        """Define um atributo conhecido ou customizado."""
        if hasattr(self, key) and key != "custom":
            setattr(self, key, value)
        else:
            self.custom[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        if hasattr(self, key) and key != "custom":
            return getattr(self, key)
        return self.custom.get(key, default)

    def summary(self) -> dict[str, Any]:
        """Retorna resumo do estado para inclusão em prompts."""
        return {
            "mood": self.mood,
            "focus": self.focus,
            "speaking": self.speaking,
            "custom": self.custom,
        }
