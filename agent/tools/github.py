from __future__ import annotations

from .base import BaseTool
import httpx
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class GitHubTool(BaseTool):
    name = "github"
    description = "Obtém informações públicas de repositórios GitHub. Entrada: 'owner/repo' ou URL."

    async def execute(self, input_data: str) -> str:
        q = (input_data or "").strip()
        if not q:
            return "Forneça 'owner/repo' ou URL do repositório GitHub."

        # Extrair owner/repo de uma URL se necessário
        if q.startswith("http"):
            try:
                p = urlparse(q)
                parts = p.path.strip("/").split("/")
                if len(parts) >= 2:
                    owner, repo = parts[0], parts[1]
                else:
                    return "URL GitHub inválida."
            except Exception:
                return "URL inválida."
        else:
            if "/" not in q:
                return "Formato inválido. Use owner/repo."
            owner, repo = q.split("/", 1)

        api = f"https://api.github.com/repos/{owner}/{repo}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(api)
                if r.status_code == 404:
                    return "Repositório não encontrado."
                r.raise_for_status()
                data = r.json()
                desc = data.get("description") or "(sem descrição)"
                stars = data.get("stargazers_count", 0)
                forks = data.get("forks_count", 0)
                issues = data.get("open_issues_count", 0)
                latest = ""
                # tentar release mais recente
                rel = await client.get(f"{api}/releases/latest")
                if rel.status_code == 200:
                    reld = rel.json()
                    latest = reld.get("tag_name", "")
                return f"{owner}/{repo}: {desc}\n⭐ {stars} | Forks: {forks} | Issues abertas: {issues}" + (f"\nÚltima release: {latest}" if latest else "")
        except Exception as e:
            logger.debug("GitHubTool error", exc_info=True)
            return f"Erro ao consultar GitHub: {e}"
