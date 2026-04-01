from __future__ import annotations

from .base import BaseTool
import httpx
import logging

logger = logging.getLogger(__name__)


class CryptoTool(BaseTool):
    name = "crypto"
    description = "Consulta preço de criptomoedas via CoinGecko. Entrada: id ou símbolo (btc, eth)."

    SYMBOL_MAP = {
        "btc": "bitcoin",
        "eth": "ethereum",
        "ada": "cardano",
        "xrp": "ripple",
    }

    async def execute(self, input_data: str) -> str:
        q = (input_data or "").strip().lower()
        if not q:
            return "Forneça o id da moeda (ex: bitcoin) ou símbolo (ex: btc)."
        coin = self.SYMBOL_MAP.get(q, q)
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(url)
                r.raise_for_status()
                data = r.json()
                if coin not in data:
                    return f"Moeda '{coin}' não encontrada no CoinGecko."
                price = data[coin]["usd"]
                return f"{coin}: ${price} USD"
        except Exception as e:
            logger.debug("CryptoTool error", exc_info=True)
            return f"Erro ao consultar CoinGecko: {e}"
