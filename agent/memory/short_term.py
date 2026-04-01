import json
import logging
from redis.asyncio import Redis
from agent.schemas import MemoryEntry

log = logging.getLogger(__name__)
_KEY_PREFIX = "mimi:session:"
_MAX_HISTORY = 50


class ShortTermMemory:
    def __init__(self, redis_url: str) -> None:
        self._url = redis_url
        self._redis: Redis | None = None

    async def connect(self) -> None:
        self._redis = Redis.from_url(self._url, decode_responses=False)
        log.info("Redis connected: %s", self._url)

    async def disconnect(self) -> None:
        if self._redis:
            await self._redis.close()

    def _key(self, session_id: str) -> str:
        return f"{_KEY_PREFIX}{session_id}"

    async def add(self, session_id: str, entry: MemoryEntry) -> None:
        assert self._redis, "Not connected"
        key = self._key(session_id)
        await self._redis.rpush(key, entry.model_dump_json())
        await self._redis.ltrim(key, -_MAX_HISTORY, -1)

    async def get_history(self, session_id: str, limit: int = 20) -> list[MemoryEntry]:
        assert self._redis, "Not connected"
        raw: list[bytes] = await self._redis.lrange(self._key(session_id), -limit, -1)
        return [MemoryEntry.model_validate_json(r) for r in raw]

    async def clear(self, session_id: str) -> None:
        assert self._redis, "Not connected"
        await self._redis.delete(self._key(session_id))
