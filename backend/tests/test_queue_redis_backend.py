"""app/queue/redis_backend.py — real Redis round trip (this sandbox runs an
actual redis-server), plus the NotConfiguredError contract when REDIS_URL
isn't set."""
from __future__ import annotations

import json

import pytest

from app.core.config import get_settings
from app.core.exceptions import NotConfiguredError
from app.queue import redis_backend

REDIS_URL = "redis://localhost:6379/0"


@pytest.fixture()
def with_redis_url():
    settings = get_settings()
    original = settings.redis_url
    settings.redis_url = REDIS_URL
    yield settings
    settings.redis_url = original
    # Never leak a test job into another test or the real worker.
    import redis

    redis.from_url(REDIS_URL).delete(redis_backend.QUEUE_KEY)


def test_enqueue_without_redis_url_raises_not_configured():
    settings = get_settings()
    original = settings.redis_url
    settings.redis_url = None
    try:
        with pytest.raises(NotConfiguredError):
            redis_backend.enqueue_document_processing("doc-1")
    finally:
        settings.redis_url = original


def test_enqueue_then_dequeue_round_trip(with_redis_url):
    redis_backend.enqueue_document_processing("doc-123", user_id="user-1")

    job = redis_backend.dequeue_blocking(timeout=2)
    assert job == {"type": "document_processing", "document_id": "doc-123", "user_id": "user-1"}


def test_dequeue_times_out_on_empty_queue(with_redis_url):
    job = redis_backend.dequeue_blocking(timeout=1)
    assert job is None


def test_enqueue_pushes_valid_json(with_redis_url):
    import redis

    redis_backend.enqueue_document_processing("doc-json", user_id=None)
    client = redis.from_url(REDIS_URL)
    _key, raw = client.brpop([redis_backend.QUEUE_KEY], timeout=2)
    payload = json.loads(raw)
    assert payload["document_id"] == "doc-json"
    assert payload["user_id"] is None
