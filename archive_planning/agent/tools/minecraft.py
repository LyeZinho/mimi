from __future__ import annotations

from .base import BaseTool
import httpx
import logging

logger = logging.getLogger(__name__)


class MinecraftTool(BaseTool):
    name = "minecraft"
    description = "Verifica status de servidor Minecraft (mcsrvstat). Entrada: host[:port]."

    async def execute(self, input_data: str) -> str:
        host = (input_data or "").strip()
        if not host:
            return "Forneça o hostname do servidor (ex: play.example.com ou 1.2.3.4:25565)."
        url = f"https://api.mcsrvstat.us/2/{host}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(url)
                r.raise_for_status()
                data = r.json()
                if not data.get("online"):
                    return f"Servidor {host} está offline."
                ip = data.get("ip") or host
                players = data.get("players", {})
                online = players.get("online", 0)
                maxp = players.get("max", "?")
                motd = data.get("motd", {}).get("clean", [])[0] if data.get("motd", {}).get("clean") else ""
                return f"{host} online — {online}/{maxp} jogadores\nMOTD: {motd}\nIP: {ip}"
        except Exception as e:
            logger.debug("MinecraftTool error", exc_info=True)
            return f"Erro ao consultar servidor Minecraft: {e}"
