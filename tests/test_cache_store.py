"""Tests for the in-memory cache store."""

from datetime import datetime, timedelta

from backend.storage.cache_store import CacheStore


def test_set_and_get():
    store = CacheStore()
    store.set("k1", "v1")
    assert store.get("k1") == "v1"


def test_get_missing_key():
    store = CacheStore()
    assert store.get("nonexistent") is None


def test_ttl_expiry():
    store = CacheStore()
    store.set("k1", "v1", ttl=1)
    # Manually expire the entry
    store._data["k1"].expires_at = datetime.now() - timedelta(seconds=1)
    assert store.get("k1") is None
    assert "k1" not in store._data


def test_capacity_eviction():
    store = CacheStore()
    store.MAX_ENTRIES = 5

    for i in range(7):
        store.set(f"k{i}", f"v{i}")

    # Should have at most MAX_ENTRIES items
    assert len(store._data) <= 5


def test_expired_entries_evicted_first():
    store = CacheStore()
    store.MAX_ENTRIES = 3

    store.set("old", "val_old", ttl=1)
    store._data["old"].expires_at = datetime.now() - timedelta(seconds=1)

    store.set("a", "va")
    store.set("b", "vb")
    store.set("c", "vc")  # This triggers eviction

    # The expired "old" should be evicted, keeping a, b, c
    assert store.get("old") is None
    assert store.get("a") == "va"
    assert store.get("b") == "vb"
    assert store.get("c") == "vc"


def test_make_key_deterministic():
    k1 = CacheStore.make_key("hello", "world")
    k2 = CacheStore.make_key("hello", "world")
    assert k1 == k2


def test_make_key_case_insensitive():
    k1 = CacheStore.make_key("Hello", "World")
    k2 = CacheStore.make_key("hello", "world")
    assert k1 == k2


def test_make_key_strips_whitespace():
    k1 = CacheStore.make_key("  hello  ", "  world  ")
    k2 = CacheStore.make_key("hello", "world")
    assert k1 == k2


def test_overwrite_existing_key():
    store = CacheStore()
    store.set("k1", "v1")
    store.set("k1", "v2")
    assert store.get("k1") == "v2"
