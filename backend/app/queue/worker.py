"""Worker process for QUEUE_BACKEND=redis (PROMPT 3 §7/§34).

Run with `python -m app.queue.worker` (see docker-compose.yml's `worker`
service, profile "queue" — not started by `docker compose up` alone).
Pops one job at a time from Redis and runs it through the exact same
`app.services.documents.document_service.process_document` the
synchronous ("inline") request path calls. A single bad job is logged and
skipped — it never crashes the loop, and never leaves the previous job's
DB session open for the next one.
"""
from __future__ import annotations

import logging
import signal
import sys
from types import FrameType

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.logging import configure_logging
from app.queue.redis_backend import dequeue_blocking
from app.services.documents import document_service

logger = logging.getLogger("app.queue.worker")

_shutdown = False


def _handle_shutdown(signum: int, frame: FrameType | None) -> None:
    global _shutdown
    logger.info("Worker recebeu sinal %s — encerrando após o job atual.", signum)
    _shutdown = True


def _process_job(job: dict) -> None:
    job_type = job.get("type")
    if job_type != "document_processing":
        logger.warning("Tipo de job desconhecido ignorado: %s", job_type)
        return

    document_id = job["document_id"]
    user_id = job.get("user_id")
    db = SessionLocal()
    try:
        document_service.process_document(db, document_id, user_id=user_id)
        logger.info("Documento %s processado pela fila.", document_id)
    except Exception:  # noqa: BLE001 - one bad job must never kill the worker loop
        logger.exception("Falha ao processar documento %s pela fila.", document_id)
    finally:
        db.close()


def run() -> None:
    settings = get_settings()
    if settings.queue_backend != "redis":
        logger.error(
            "QUEUE_BACKEND=%s — este worker só faz sentido com QUEUE_BACKEND=redis. Encerrando.",
            settings.queue_backend,
        )
        sys.exit(1)

    logger.info("Worker de processamento de documentos iniciado (QUEUE_BACKEND=redis).")
    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)

    while not _shutdown:
        job = dequeue_blocking(timeout=5)
        if job is not None:
            _process_job(job)

    logger.info("Worker encerrado.")


if __name__ == "__main__":
    configure_logging()
    run()
