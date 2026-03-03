from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


@dataclass
class CacheEntry:
    value: Any
    expires_at: datetime


class InMemoryTTLCache:
    def __init__(self, ttl_seconds: int) -> None:
        self.ttl_seconds = ttl_seconds
        self._items: dict[str, CacheEntry] = {}

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def get(self, key: str) -> Any | None:
        entry = self._items.get(key)
        if not entry:
            return None
        if entry.expires_at <= self._now():
            self._items.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: Any) -> None:
        expires_at = self._now() + timedelta(seconds=self.ttl_seconds)
        self._items[key] = CacheEntry(value=value, expires_at=expires_at)

    def clear(self) -> None:
        self._items.clear()
