"""Test configuration.

Environment variables are set *before* anything under `app` is imported so
`Settings` (cached via `lru_cache`) picks up an isolated temp database and
storage directory instead of the real local `storage/` folder.

By default tests run against a throwaway SQLite file. Set TEST_DATABASE_URL
to run the exact same suite against PostgreSQL (e.g. in CI, or locally to
confirm a schema/migration change behaves the same on both — see
backend/DATABASE.md). `DATABASE_URL` itself is deliberately NOT read here:
the suite must never depend on whatever a developer's shell happens to have
exported for running the app, only on an explicit opt-in.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

_TEST_ROOT = Path(tempfile.mkdtemp(prefix="campanhas_backend_test_"))
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_TEST_ROOT / 'test.db'}"
os.environ["STORAGE_ROOT"] = str(_TEST_ROOT / "storage")
os.environ["STORAGE_ORIGINALS_DIR"] = str(_TEST_ROOT / "storage" / "originals")
os.environ["STORAGE_PROCESSED_DIR"] = str(_TEST_ROOT / "storage" / "processed")
os.environ["STORAGE_TEMPORARY_DIR"] = str(_TEST_ROOT / "storage" / "temporary")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.models  # noqa: E402,F401 - populate Base.metadata before create_all
from app.api.deps import get_db  # noqa: E402
from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402

if os.environ.get("TEST_DATABASE_URL"):
    # A real, persistent database (e.g. Postgres) may carry tables from a
    # previous run — start from a clean schema instead of assuming it's
    # empty. The SQLite temp-file path never needs this: it's a fresh file.
    Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """The rate limiter (app/core/rate_limit.py) tracks hits in process
    memory, keyed by client IP — every test using `client` shares the same
    "testclient" IP, so without a reset a rate-limit test (or simply many
    tests hitting the same endpoint) would bleed its counters into
    unrelated tests run afterwards in the same process."""
    from app.core.rate_limit import reset_all

    reset_all()
    yield
    reset_all()


@pytest.fixture()
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = _override_get_db
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()
