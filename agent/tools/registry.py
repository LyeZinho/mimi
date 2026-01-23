from .base import BaseTool
from .search import SearchTool
from .weather import WeatherTool
from .time import TimeTool
from .calc import CalculatorTool
from .notes import NotesTool
from .http import HTTPTool
from .github import GitHubTool
from .crypto import CryptoTool
from .minecraft import MinecraftTool

class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        self._register_defaults()

    def _register_defaults(self):
        self.register(SearchTool())
        self.register(WeatherTool())
        self.register(TimeTool())
        self.register(CalculatorTool())
        self.register(NotesTool())
        self.register(HTTPTool())
        self.register(GitHubTool())
        self.register(CryptoTool())
        self.register(MinecraftTool())

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[dict]:
        return [t.to_dict() for t in self._tools.values()]
