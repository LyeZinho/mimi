"""Response caching system to optimize token usage.

Caches LLM responses for common queries with TTL-based expiration.
Reduces API calls to Ollama by serving cached responses for identical user inputs.
"""

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ResponseCache:
    """Caches LLM responses with TTL-based expiration.
    
    Stores responses keyed by hash of user input. Supports configurable TTL
    (time-to-live) for cache entries. Persists to JSON file for cross-session
    caching. Thread-safe for concurrent reads, write-protected during flushes.
    
    Example:
        >>> cache = ResponseCache("data/response_cache.json", ttl_seconds=86400)
        >>> key = cache.get_cache_key("What is your name?")
        >>> if cached := cache.get(key):
        ...     print(f"Cache hit: {cached}")
        ... else:
        ...     response = llm.call("What is your name?")
        ...     cache.set(key, response)
        ...     cache.flush()
    """

    def __init__(
        self,
        cache_file: Path | str = "data/response_cache.json",
        ttl_seconds: int = 86400,
    ) -> None:
        """Initialize ResponseCache.
        
        Args:
            cache_file: Path to JSON cache file. Created if doesn't exist.
            ttl_seconds: Time-to-live for cache entries in seconds (default 24h).
        """
        self.cache_file = Path(cache_file)
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, dict[str, Any]] = {}
        self._dirty = False

        self._load_cache()
        logger.info(
            f"ResponseCache initialized: {len(self._cache)} entries, "
            f"TTL={ttl_seconds}s, file={self.cache_file}"
        )

    def _load_cache(self) -> None:
        """Load cache from disk. Creates empty cache if file doesn't exist."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._cache = data.get("cache", {})
                logger.info(f"Loaded cache from {self.cache_file}")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load cache: {e}. Starting fresh.")
                self._cache = {}
        else:
            self._cache = {}
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)

    def _cleanup_expired(self) -> None:
        """Remove expired entries from cache (in-memory only)."""
        now = time.time()
        expired_keys = [
            key
            for key, entry in self._cache.items()
            if now - entry.get("timestamp", 0) > self.ttl_seconds
        ]

        for key in expired_keys:
            del self._cache[key]
            self._dirty = True

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

    @staticmethod
    def get_cache_key(user_input: str) -> str:
        """Generate cache key from user input using SHA-256 hash.
        
        Args:
            user_input: User message to hash
            
        Returns:
            Hex digest of SHA-256 hash of input
            
        Example:
            >>> key = ResponseCache.get_cache_key("Hello")
            >>> len(key)
            64
        """
        return hashlib.sha256(user_input.encode()).hexdigest()

    def get(self, cache_key: str) -> Optional[dict[str, Any]]:
        """Retrieve cached response if valid and not expired.
        
        Args:
            cache_key: Cache key (from get_cache_key())
            
        Returns:
            Cached response dict if found and not expired, None otherwise
        """
        self._cleanup_expired()

        if cache_key not in self._cache:
            logger.debug(f"Cache miss: {cache_key[:8]}...")
            return None

        entry = self._cache[cache_key]
        now = time.time()
        age = now - entry.get("timestamp", 0)

        if age > self.ttl_seconds:
            logger.debug(f"Cache expired: {cache_key[:8]}... (age={age:.0f}s)")
            del self._cache[cache_key]
            self._dirty = True
            return None

        logger.debug(f"Cache hit: {cache_key[:8]}... (age={age:.0f}s)")
        return entry.get("response")

    def set(self, cache_key: str, response: dict[str, Any]) -> None:
        """Store response in cache (in-memory).
        
        Call flush() to persist to disk.
        
        Args:
            cache_key: Cache key (from get_cache_key())
            response: Response dict to cache (typically LLM response)
        """
        self._cache[cache_key] = {
            "timestamp": time.time(),
            "response": response,
        }
        self._dirty = True
        logger.debug(f"Cache set: {cache_key[:8]}...")

    def flush(self) -> None:
        """Persist in-memory cache to disk. Called after set()."""
        if not self._dirty:
            logger.debug("Cache already synced, skipping flush")
            return

        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "version": "1.0",
                        "cache": self._cache,
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
            self._dirty = False
            logger.info(f"Cache flushed to disk: {len(self._cache)} entries")
        except IOError as e:
            logger.error(f"Failed to flush cache: {e}")

    def clear(self) -> None:
        """Clear all cache entries (in-memory and on disk)."""
        self._cache.clear()
        self._dirty = True
        self.flush()
        logger.info("Cache cleared")

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dict with total_entries, file_size_bytes, oldest_entry_age_seconds
        """
        self._cleanup_expired()

        now = time.time()
        ages = [
            now - entry.get("timestamp", 0) for entry in self._cache.values()
        ]
        oldest_age = max(ages) if ages else 0

        file_size = self.cache_file.stat().st_size if self.cache_file.exists() else 0

        return {
            "total_entries": len(self._cache),
            "file_size_bytes": file_size,
            "oldest_entry_age_seconds": oldest_age,
            "dirty": self._dirty,
        }
