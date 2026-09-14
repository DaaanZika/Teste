"""Unit tests for app.core.health — exercised directly (not through the API)
so Redis reachability can be tested without touching the app's cached Settings.
"""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from app.core.config import Settings
from app.core.health import check_redis


def _settings(**overrides) -> Settings:
    return Settings(**{"queue_backend": "inline", **overrides})


def test_check_redis_returns_none_when_queue_backend_is_inline():
    with patch("app.core.health.get_settings", return_value=_settings(queue_backend="inline")):
        assert check_redis() is None


def test_check_redis_unhealthy_when_redis_required_but_url_missing():
    with patch("app.core.health.get_settings", return_value=_settings(queue_backend="redis", redis_url=None)):
        status = check_redis()
        assert status is not None
        assert status.healthy is False
        assert "REDIS_URL" in status.detail


def test_check_redis_unhealthy_when_unreachable():
    unreachable = "redis://127.0.0.1:1/0"
    with patch(
        "app.core.health.get_settings", return_value=_settings(queue_backend="redis", redis_url=unreachable)
    ):
        status = check_redis()
        assert status is not None
        assert status.healthy is False


def test_check_redis_healthy_when_reachable():
    redis_url = os.environ.get("TEST_REDIS_URL", "redis://127.0.0.1:6379/0")

    try:
        import redis as redis_lib

        redis_lib.from_url(redis_url, socket_connect_timeout=1).ping()
    except Exception:
        pytest.skip(f"No Redis reachable at {redis_url} in this environment")

    with patch("app.core.health.get_settings", return_value=_settings(queue_backend="redis", redis_url=redis_url)):
        status = check_redis()
        assert status is not None
        assert status.healthy is True, status.detail
