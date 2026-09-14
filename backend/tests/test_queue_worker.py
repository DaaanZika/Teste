"""app/queue/worker.py — _process_job dispatches to the exact same
document_service.process_document the synchronous ("inline") route path
calls, and a single bad job never raises out of the worker loop."""
from __future__ import annotations

import uuid

import pytest

from app.models.campaign import Campaign
from app.models.document import Document
from app.queue import worker


@pytest.fixture()
def uploaded_document(db_session):
    campaign = Campaign(name=f"Campanha {uuid.uuid4().hex[:8]}")
    db_session.add(campaign)
    db_session.commit()

    document = Document(
        campaign_id=campaign.id,
        original_filename="nota.png",
        mime_type="image/png",
        file_extension="png",
        file_size_bytes=10,
        sha256_hash=uuid.uuid4().hex,
        original_path="originals/nota.png",  # never actually read — process_document is mocked below
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)
    return document


def test_process_job_calls_document_service(monkeypatch, uploaded_document):
    calls = []

    def fake_process_document(db, document_id, *, user_id=None):
        calls.append((document_id, user_id))

    monkeypatch.setattr(worker.document_service, "process_document", fake_process_document)

    worker._process_job({"type": "document_processing", "document_id": uploaded_document.id, "user_id": "u1"})

    assert calls == [(uploaded_document.id, "u1")]


def test_process_job_ignores_unknown_type(monkeypatch):
    calls = []
    monkeypatch.setattr(
        worker.document_service, "process_document", lambda *a, **k: calls.append((a, k))
    )

    worker._process_job({"type": "something_else", "document_id": "irrelevant"})

    assert calls == []


def test_process_job_never_raises_on_failure(monkeypatch, uploaded_document):
    def failing_process_document(db, document_id, *, user_id=None):
        raise RuntimeError("boom")

    monkeypatch.setattr(worker.document_service, "process_document", failing_process_document)

    # Must not raise — a single bad job must never kill the worker loop.
    worker._process_job({"type": "document_processing", "document_id": uploaded_document.id, "user_id": None})


def test_run_refuses_to_start_without_redis_queue_backend(monkeypatch):
    from app.core.config import get_settings

    settings = get_settings()
    original = settings.queue_backend
    settings.queue_backend = "inline"
    try:
        with pytest.raises(SystemExit):
            worker.run()
    finally:
        settings.queue_backend = original
