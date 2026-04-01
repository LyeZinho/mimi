import logging
import aiosqlite
from agent.schemas import MemoryEntry

log = logging.getLogger(__name__)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL
)
"""


class LongTermMemory:
    def __init__(self, db_path: str) -> None:
        self._path = db_path
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self._db = await aiosqlite.connect(self._path)
        await self._db.execute(_CREATE_TABLE)
        await self._db.commit()
        log.info("SQLite connected: %s", self._path)

    async def disconnect(self) -> None:
        if self._db:
            await self._db.close()

    async def save(self, session_id: str, entry: MemoryEntry) -> None:
        assert self._db
        await self._db.execute(
            "INSERT INTO memory (session_id, role, content, timestamp) VALUES (?,?,?,?)",
            (session_id, entry.role, entry.content, entry.timestamp.isoformat()),
        )
        await self._db.commit()

    async def load(self, session_id: str, limit: int = 20) -> list[MemoryEntry]:
        assert self._db
        async with self._db.execute(
            "SELECT role, content, timestamp FROM memory WHERE session_id=? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()
        return [MemoryEntry(role=r[0], content=r[1], timestamp=r[2]) for r in reversed(rows)]
