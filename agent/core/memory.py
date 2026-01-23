"""Gerenciamento de memória do agente."""

from __future__ import annotations

import json
import sqlite3
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator


@dataclass
class MemoryEntry:
    """Entrada de memória com metadados."""

    content: str
    role: str  # "user" | "assistant" | "system"
    importance: float = 0.5
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "role": self.role,
            "importance": self.importance,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class Memory:
    """Memória de curto e longo prazo."""

    def __init__(
        self,
        short_term_limit: int = 20,
        db_path: str | Path | None = None,
    ) -> None:
        self._short_term: deque[MemoryEntry] = deque(maxlen=short_term_limit)
        self._db_path = Path(db_path) if db_path else None
        if self._db_path:
            self._init_db()

    # ───────────────────────────────── DB ─────────────────────────────────
    def _init_db(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    role TEXT NOT NULL,
                    importance REAL,
                    timestamp REAL,
                    metadata TEXT
                )
                """
            )
            conn.commit()

    def _persist(self, entry: MemoryEntry) -> None:
        if not self._db_path:
            return
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO memories (content, role, importance, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    entry.content,
                    entry.role,
                    entry.importance,
                    entry.timestamp,
                    json.dumps(entry.metadata),
                ),
            )
            conn.commit()

    # ───────────────────────────────── API ────────────────────────────────
    def add(
        self,
        content: str,
        role: str = "user",
        importance: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        entry = MemoryEntry(
            content=content,
            role=role,
            importance=importance,
            metadata=metadata or {},
        )
        self._short_term.append(entry)
        self._persist(entry)
        return entry

    def recent(self, n: int | None = None) -> list[MemoryEntry]:
        """Retorna as últimas n entradas (ou todas se n=None)."""
        items = list(self._short_term)
        return items[-n:] if n else items

    def search_long_term(
        self, keyword: str, limit: int = 10
    ) -> list[MemoryEntry]:
        """Busca simples por palavra-chave na memória persistente."""
        if not self._db_path:
            return []
            
        # Extrai palavras significativas (simplificado)
        ignore = {"o", "a", "os", "as", "um", "uma", "e", "de", "da", "do", "em", "para", "que", "é", "?", "!"}
        words = [w for w in keyword.lower().split() if w and w not in ignore]
        
        if not words:
            return []

        # Monta query OR para cada palavra
        query_parts = []
        params = []
        for w in words:
            query_parts.append("content LIKE ?")
            params.append(f"%{w}%")
            
        where_clause = " OR ".join(query_parts)
        
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                f"""
                SELECT content, role, importance, timestamp, metadata
                FROM memories
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (*params, limit),
            ).fetchall()
        return [
            MemoryEntry(
                content=r[0],
                role=r[1],
                importance=r[2],
                timestamp=r[3],
                metadata=json.loads(r[4]) if r[4] else {},
            )
            for r in rows
        ]

    def __iter__(self) -> Iterator[MemoryEntry]:
        return iter(self._short_term)

    def __len__(self) -> int:
        return len(self._short_term)
