"""Unit tests for ResponseCache response caching system."""

import json
import time
from pathlib import Path

import pytest

from agent.core.response_cache import ResponseCache


class TestResponseCacheKeyGeneration:
    """Tests for cache key generation."""

    def test_get_cache_key_returns_hex_string(self):
        """Test that get_cache_key returns 64-char hex SHA-256 digest."""
        key = ResponseCache.get_cache_key("hello")
        assert isinstance(key, str)
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)

    def test_get_cache_key_deterministic(self):
        """Test that same input produces same key."""
        key1 = ResponseCache.get_cache_key("test message")
        key2 = ResponseCache.get_cache_key("test message")
        assert key1 == key2

    def test_get_cache_key_different_inputs(self):
        """Test that different inputs produce different keys."""
        key1 = ResponseCache.get_cache_key("message1")
        key2 = ResponseCache.get_cache_key("message2")
        assert key1 != key2


class TestResponseCacheInit:
    """Tests for cache initialization."""

    def test_init_creates_empty_cache(self, tmp_path):
        """Test that init creates cache with no entries."""
        cache_file = tmp_path / "cache.json"
        cache = ResponseCache(cache_file)
        assert cache.get_stats()["total_entries"] == 0

    def test_init_loads_existing_cache(self, tmp_path):
        """Test that init loads existing cache file."""
        cache_file = tmp_path / "cache.json"
        
        initial_cache = {
            "version": "1.0",
            "cache": {
                "key1": {
                    "timestamp": time.time(),
                    "response": {"text": "cached response"}
                }
            }
        }
        cache_file.write_text(json.dumps(initial_cache))
        
        cache = ResponseCache(cache_file)
        assert cache.get_stats()["total_entries"] == 1

    def test_init_handles_corrupt_cache(self, tmp_path):
        """Test that init starts fresh if cache file is corrupt."""
        cache_file = tmp_path / "cache.json"
        cache_file.write_text("{ invalid json }")
        
        cache = ResponseCache(cache_file)
        assert cache.get_stats()["total_entries"] == 0

    def test_init_creates_parent_directory(self, tmp_path):
        """Test that init creates parent directories if needed."""
        cache_file = tmp_path / "deep" / "nested" / "cache.json"
        cache = ResponseCache(cache_file)
        
        assert cache.cache_file.parent.exists()


class TestResponseCacheGetSet:
    """Tests for cache get/set operations."""

    @pytest.fixture
    def cache(self, tmp_path):
        """Provide initialized ResponseCache."""
        return ResponseCache(tmp_path / "cache.json", ttl_seconds=3600)

    def test_set_and_get_response(self, cache):
        """Test setting and getting a cached response."""
        key = ResponseCache.get_cache_key("hello")
        response = {"text": "Hello world", "emotion": "happy"}
        
        cache.set(key, response)
        retrieved = cache.get(key)
        
        assert retrieved == response

    def test_get_nonexistent_key_returns_none(self, cache):
        """Test that getting nonexistent key returns None."""
        key = ResponseCache.get_cache_key("nonexistent")
        assert cache.get(key) is None

    def test_set_marks_cache_dirty(self, cache):
        """Test that set() marks cache as dirty."""
        key = ResponseCache.get_cache_key("test")
        cache.set(key, {"text": "response"})
        assert cache._dirty is True

    def test_multiple_entries(self, cache):
        """Test storing and retrieving multiple entries."""
        key1 = ResponseCache.get_cache_key("message1")
        key2 = ResponseCache.get_cache_key("message2")
        
        response1 = {"text": "response1"}
        response2 = {"text": "response2"}
        
        cache.set(key1, response1)
        cache.set(key2, response2)
        
        assert cache.get(key1) == response1
        assert cache.get(key2) == response2
        assert cache.get_stats()["total_entries"] == 2


class TestResponseCacheTTL:
    """Tests for TTL expiration."""

    def test_ttl_expiration(self, tmp_path):
        """Test that expired entries are not returned."""
        cache = ResponseCache(tmp_path / "cache.json", ttl_seconds=1)
        
        key = ResponseCache.get_cache_key("test")
        response = {"text": "response"}
        cache.set(key, response)
        
        assert cache.get(key) == response
        
        time.sleep(1.1)
        
        assert cache.get(key) is None

    def test_ttl_not_expired(self, tmp_path):
        """Test that non-expired entries are returned."""
        cache = ResponseCache(tmp_path / "cache.json", ttl_seconds=10)
        
        key = ResponseCache.get_cache_key("test")
        response = {"text": "response"}
        cache.set(key, response)
        
        time.sleep(0.2)
        
        assert cache.get(key) == response

    def test_cleanup_removes_expired_entries(self, tmp_path):
        """Test that cleanup removes expired entries from cache."""
        cache = ResponseCache(tmp_path / "cache.json", ttl_seconds=1)
        
        key1 = ResponseCache.get_cache_key("msg1")
        key2 = ResponseCache.get_cache_key("msg2")
        
        cache.set(key1, {"text": "response1"})
        
        time.sleep(1.1)
        
        cache.set(key2, {"text": "response2"})
        
        cache._cleanup_expired()
        
        assert len(cache._cache) == 1
        assert key2 in cache._cache


class TestResponseCacheFlush:
    """Tests for cache persistence."""

    def test_flush_persists_to_disk(self, tmp_path):
        """Test that flush() writes cache to disk."""
        cache_file = tmp_path / "cache.json"
        cache = ResponseCache(cache_file)
        
        key = ResponseCache.get_cache_key("test")
        cache.set(key, {"text": "response"})
        cache.flush()
        
        assert cache_file.exists()
        
        data = json.loads(cache_file.read_text())
        assert "cache" in data
        assert key in data["cache"]

    def test_flush_skips_if_not_dirty(self, tmp_path):
        """Test that flush() skips if cache is not dirty."""
        cache_file = tmp_path / "cache.json"
        cache = ResponseCache(cache_file)
        
        cache._dirty = False
        mtime_before = cache_file.stat().st_mtime if cache_file.exists() else 0
        
        time.sleep(0.01)
        cache.flush()
        
        mtime_after = cache_file.stat().st_mtime if cache_file.exists() else 0
        assert mtime_before == mtime_after

    def test_persisted_cache_reloads(self, tmp_path):
        """Test that cache persisted to disk can be reloaded."""
        cache_file = tmp_path / "cache.json"
        
        key = ResponseCache.get_cache_key("test")
        response = {"text": "response", "emotion": "happy"}
        
        cache1 = ResponseCache(cache_file)
        cache1.set(key, response)
        cache1.flush()
        
        cache2 = ResponseCache(cache_file)
        assert cache2.get(key) == response


class TestResponseCacheClear:
    """Tests for cache clearing."""

    def test_clear_removes_all_entries(self, tmp_path):
        """Test that clear() removes all cache entries."""
        cache = ResponseCache(tmp_path / "cache.json")
        
        cache.set(ResponseCache.get_cache_key("msg1"), {"text": "resp1"})
        cache.set(ResponseCache.get_cache_key("msg2"), {"text": "resp2"})
        
        assert cache.get_stats()["total_entries"] == 2
        
        cache.clear()
        
        assert cache.get_stats()["total_entries"] == 0

    def test_clear_persists_to_disk(self, tmp_path):
        """Test that clear() persists empty cache to disk."""
        cache_file = tmp_path / "cache.json"
        cache = ResponseCache(cache_file)
        
        cache.set(ResponseCache.get_cache_key("test"), {"text": "resp"})
        cache.flush()
        
        cache.clear()
        
        data = json.loads(cache_file.read_text())
        assert len(data["cache"]) == 0


class TestResponseCacheStats:
    """Tests for cache statistics."""

    def test_get_stats_returns_dict(self, tmp_path):
        """Test that get_stats returns expected keys."""
        cache = ResponseCache(tmp_path / "cache.json")
        stats = cache.get_stats()
        
        assert "total_entries" in stats
        assert "file_size_bytes" in stats
        assert "oldest_entry_age_seconds" in stats
        assert "dirty" in stats

    def test_get_stats_total_entries(self, tmp_path):
        """Test that get_stats reports correct entry count."""
        cache = ResponseCache(tmp_path / "cache.json")
        
        cache.set(ResponseCache.get_cache_key("msg1"), {"text": "resp1"})
        cache.set(ResponseCache.get_cache_key("msg2"), {"text": "resp2"})
        
        stats = cache.get_stats()
        assert stats["total_entries"] == 2

    def test_get_stats_oldest_age(self, tmp_path):
        """Test that get_stats reports oldest entry age."""
        cache = ResponseCache(tmp_path / "cache.json")
        
        cache.set(ResponseCache.get_cache_key("msg1"), {"text": "resp1"})
        
        time.sleep(0.1)
        
        stats = cache.get_stats()
        assert stats["oldest_entry_age_seconds"] >= 0.1

    def test_get_stats_file_size(self, tmp_path):
        """Test that get_stats reports file size."""
        cache_file = tmp_path / "cache.json"
        cache = ResponseCache(cache_file)
        
        cache.set(ResponseCache.get_cache_key("test"), {"text": "response"})
        cache.flush()
        
        stats = cache.get_stats()
        assert stats["file_size_bytes"] > 0


class TestResponseCacheIntegration:
    """Integration tests for ResponseCache."""

    def test_full_lifecycle(self, tmp_path):
        """Test full lifecycle: create, set, flush, load, get."""
        cache_file = tmp_path / "cache.json"
        
        key = ResponseCache.get_cache_key("What is your name?")
        response = {
            "intent": "speak",
            "text": "I'm Mimi!",
            "emotion": "happy",
            "gesture": "wave"
        }
        
        cache1 = ResponseCache(cache_file, ttl_seconds=3600)
        cache1.set(key, response)
        cache1.flush()
        
        cache2 = ResponseCache(cache_file, ttl_seconds=3600)
        retrieved = cache2.get(key)
        
        assert retrieved == response

    def test_common_questions_pattern(self, tmp_path):
        """Test caching pattern for common questions."""
        cache = ResponseCache(tmp_path / "cache.json", ttl_seconds=3600)
        
        questions = [
            "What's your name?",
            "How are you?",
            "What time is it?"
        ]
        
        responses = [
            {"text": "I'm Mimi"},
            {"text": "I'm doing well"},
            {"text": "It's time to chat"}
        ]
        
        for question, response in zip(questions, responses):
            key = ResponseCache.get_cache_key(question)
            cache.set(key, response)
        
        cache.flush()
        
        for question, expected_response in zip(questions, responses):
            key = ResponseCache.get_cache_key(question)
            retrieved = cache.get(key)
            assert retrieved == expected_response
