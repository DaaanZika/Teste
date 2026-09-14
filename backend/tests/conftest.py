"""Test configuration.

Environment variables are set *before* anything under `app` is imported so
`Settings` (cached via `lru_cache`) picks up an isolated temp database and
storage directory instead of the real local `storage/` folder.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

_TEST_ROOT = Path(tempfile.mkdtemp(prefix="campanhas_backend_test_"))
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_ROOT / 'test.db'}"
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

Base.metadata.create_all(bind=engine)


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
