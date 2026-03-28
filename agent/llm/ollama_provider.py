import asyncio
import json
import time
from typing import AsyncIterator, Optional
import aiohttp
from agent.llm.config import OllamaConfig
from agent.llm.errors import LLMConnectionError, LLMTimeoutError
from agent.llm.provider import LLMProvider


class OllamaProvider(LLMProvider):
    def __init__(self, config: OllamaConfig):
        super().__init__(config)
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None

    async def generate(self, prompt: str, stream: bool = False) -> str | AsyncIterator[str]:
        start_time = time.time()
        
        try:
            if self.session is None:
                self.session = aiohttp.ClientSession()
            
            url = f"{self.config.host}/api/generate"
            payload = {
                "model": self.config.model,
                "prompt": prompt,
                "stream": stream,
                "temperature": self.config.temperature,
                "top_p": self.config.top_p,
            }
            
            if stream:
                return self._stream_generate(url, payload, start_time)
            else:
                return await self._batch_generate(url, payload, start_time)
                
        except asyncio.TimeoutError as e:
            self.error_count += 1
            raise LLMTimeoutError(str(e)) from e
        except Exception as e:
            if "ClientError" in type(e).__name__:
                self.error_count += 1
                raise LLMConnectionError(str(e)) from e
            raise

    async def _batch_generate(self, url: str, payload: dict, start_time: float) -> str:
        headers = {}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        
        async with self.session.post(url, json=payload, headers=headers) as response:
            data = await response.json()
            
            latency_ms = (time.time() - start_time) * 1000
            self.total_latency_ms += latency_ms
            self.request_count += 1
            
            response_text = data.get("response", "")
            prompt_tokens = data.get("prompt_eval_count", 0)
            response_tokens = data.get("eval_count", 0)
            
            self.token_count_in += prompt_tokens
            self.token_count_out += response_tokens
            
            return response_text

    async def _stream_generate(self, url: str, payload: dict, start_time: float) -> AsyncIterator[str]:
        headers = {}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        
        async with self.session.post(url, json=payload, headers=headers) as response:
            async for line in response.content:
                if line:
                    data = json.loads(line.decode())
                    chunk = data.get("response", "")
                    if chunk:
                        yield chunk
            
            latency_ms = (time.time() - start_time) * 1000
            self.total_latency_ms += latency_ms
            self.request_count += 1

    def count_tokens(self, text: str) -> int:
        return len(text.split())

    async def validate_connection(self) -> bool:
        try:
            if self.session is None:
                self.session = aiohttp.ClientSession()
            
            headers = {}
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"
            
            url = f"{self.config.host}/api/tags"
            async with self.session.get(url, headers=headers) as response:
                return response.status == 200
        except Exception:
            return False

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None
