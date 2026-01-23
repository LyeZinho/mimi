import logging
from duckduckgo_search import DDGS
from .base import BaseTool

logger = logging.getLogger(__name__)

class SearchTool(BaseTool):
    name = "search"
    description = "Busca informações atualizadas na internet. Use para fatos, notícias ou curiosidades."

    async def execute(self, query: str) -> str:
        try:
            results = DDGS().text(query, max_results=3)
            if not results:
                return "Nenhum resultado encontrado."
            
            summary = []
            for r in results:
                summary.append(f"- {r['title']}: {r['body']}")
            return "\n".join(summary)
        except Exception as e:
            logger.error("Erro na busca: %s", e)
            return f"Erro ao buscar: {str(e)}"
