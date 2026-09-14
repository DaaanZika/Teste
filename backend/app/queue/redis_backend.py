"""Redis-backed job queue for document processing (PROMPT 3 §7/§34).

Only used when QUEUE_BACKEND=redis — the default ("inline", V1's original
behavior) never imports this module and runs OCR synchronously inside the
request instead. A separate worker process (`python -m app.queue.worker`,
see docker-compose.yml's `worker` service, profile "queue") pops jobs
pushed here and runs them through the exact same
`app.services.documents.document_service.process_document` the
synchronous path calls — no OCR logic is duplicated between the two modes,
only *when* it runs differs.
"""
from __future__ import annotations

import json

from app.core.config import get_settings
from app.core.exceptions import NotConfiguredError

QUEUE_KEY = "campanhas:queue:document_processing"


def _get_client():
    settings = get_settings()
    if not settings.redis_url:
        raise NotConfiguredError(
            "QUEUE_BACKEND=redis, mas REDIS_URL não foi definido. Configure REDIS_URL ou "
            "volte para QUEUE_BACKEND=inline (padrão, não exige Redis)."
        )
    import redis

    return redis.from_url(settings.redis_url)


def enqueue_document_processing(document_id: str, *, user_id: str | None = None) -> None:
    client = _get_client()
    job = {"type": "document_processing", "document_id": document_id, "user_id": user_id}
    client.lpush(QUEUE_KEY, json.dumps(job))


def dequeue_blocking(timeout: int = 5) -> dict | None:
    """Blocks up to `timeout` seconds for the next job. Returns None on a
    timeout (no job available) so the worker loop can check for a shutdown
    signal periodically instead of blocking forever on an idle queue."""
    client = _get_client()
    result = client.brpop([QUEUE_KEY], timeout=timeout)
    if result is None:
        return None
    _key, raw = result
    return json.loads(raw)
