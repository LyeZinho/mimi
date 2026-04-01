import httpx
import logging
from .base import BaseTool

logger = logging.getLogger(__name__)

class WeatherTool(BaseTool):
    name = "weather"
    description = "Obtém a previsão do clima atual. Entrada: nome da cidade (ex: 'São Paulo')."

    async def execute(self, city: str) -> str:
        try:
            # 1. Geocoding
            async with httpx.AsyncClient() as client:
                geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=pt&format=json"
                resp = await client.get(geo_url)
                data = resp.json()
                
                if not data.get("results"):
                    return f"Cidade '{city}' não encontrada."
                
                lat = data["results"][0]["latitude"]
                lon = data["results"][0]["longitude"]
                city_name = data["results"][0]["name"]

                # 2. Weather
                weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code&timezone=auto"
                resp = await client.get(weather_url)
                w_data = resp.json()
                
                current = w_data.get("current", {})
                temp = current.get("temperature_2m", "N/A")
                
                return f"Clima em {city_name}: {temp}°C."
        except Exception as e:
            logger.error("Erro no clima: %s", e)
            return f"Erro ao obter clima: {str(e)}"
