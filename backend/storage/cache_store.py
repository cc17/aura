"""Generic in-memory cache with TTL and capacity eviction."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class CacheEntry:
    value: str
    expires_at: datetime


@dataclass
class CacheStore:
    MAX_ENTRIES: int = 500
    DEFAULT_TTL: int = 86400  # 24 hours

    _data: dict[str, CacheEntry] = field(default_factory=dict)

    def set(self, key: str, value: str, ttl: int | None = None) -> None:
        """Store a value with optional TTL (seconds). Defaults to DEFAULT_TTL."""
        ttl = ttl if ttl is not None else self.DEFAULT_TTL
        expires_at = datetime.now() + timedelta(seconds=ttl)
        self._data[key] = CacheEntry(value=value, expires_at=expires_at)

        if len(self._data) > self.MAX_ENTRIES:
            self._evict()

    def get(self, key: str) -> str | None:
        """Return cached value or None if missing/expired."""
        entry = self._data.get(key)
        if entry is None:
            return None
        if datetime.now() >= entry.expires_at:
            del self._data[key]
            return None
        return entry.value

    def _evict(self) -> None:
        """Remove expired entries first, then oldest if still over capacity."""
        now = datetime.now()
        expired = [k for k, v in self._data.items() if now >= v.expires_at]
        for k in expired:
            del self._data[k]

        if len(self._data) > self.MAX_ENTRIES:
            # Remove oldest entries (by expiry time) until under limit
            sorted_keys = sorted(self._data, key=lambda k: self._data[k].expires_at)
            excess = len(self._data) - self.MAX_ENTRIES
            for k in sorted_keys[:excess]:
                del self._data[k]

    @staticmethod
    def make_key(*parts: str) -> str:
        """Build a deterministic cache key from string parts."""
        raw = "|".join(p.strip().lower() for p in parts if p)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


# Module-level singleton
cache_store = CacheStore()
