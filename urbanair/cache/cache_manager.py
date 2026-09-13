"""Thread-safe in-memory TTL cache for short-lived API response data."""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any


@dataclass
class _CacheEntry:
    value: Any
    expires_at: datetime


class InMemoryTTLCache:
    """A simple in-memory key/value store with per-entry TTL expiry.

    Thread-safe: a single :class:`threading.Lock` guards all mutations.
    """

    def __init__(self, ttl_seconds: int) -> None:
        self.ttl_seconds = ttl_seconds
        self._items: dict[str, _CacheEntry] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def _is_alive(self, entry: _CacheEntry) -> bool:
        return entry.expires_at > self._now()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str) -> Any | None:
        """Return the cached value for *key*, or ``None`` if missing/expired."""
        with self._lock:
            entry = self._items.get(key)
            if entry is None:
                return None
            if not self._is_alive(entry):
                del self._items[key]
                return None
            return entry.value

    def set(self, key: str, value: Any) -> None:
        """Store *value* under *key* with the configured TTL."""
        expires_at = self._now() + timedelta(seconds=self.ttl_seconds)
        with self._lock:
            self._items[key] = _CacheEntry(value=value, expires_at=expires_at)

    def invalidate(self, key: str) -> None:
        """Remove a single key from the cache, if present."""
        with self._lock:
            self._items.pop(key, None)

    def clear(self) -> None:
        """Evict all entries."""
        with self._lock:
            self._items.clear()

    def size(self) -> int:
        """Return the number of *live* (non-expired) entries."""
        now = self._now()
        with self._lock:
            return sum(1 for e in self._items.values() if e.expires_at > now)

    def keys(self) -> list[str]:
        """Return the keys of all live entries."""
        now = self._now()
        with self._lock:
            return [k for k, e in self._items.items() if e.expires_at > now]
