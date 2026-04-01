from abc import ABC, abstractmethod
from typing import Any

class BaseTool(ABC):
    name: str = "base_tool"
    description: str = "Base tool description"

    @abstractmethod
    async def execute(self, input_data: str) -> str:
        """Executa a ferramenta e retorna o resultado como string."""
        pass

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description
        }
