"""app/core/rate_limit.py — the sliding/fixed-window counter itself, plus
its wiring into /auth/google/login and /auth/google/callback
(docs/audit/FASE-D-gaps.md "Sem rate limiting no login")."""
from __future__ import annotations

import time
from unittest.mock import Mock

import pytest

from app.core.exceptions import RateLimitExceededError
from app.core.rate_limit import enforce_rate_limit, reset_all


def _fake_request(ip: str = "1.2.3.4"):
    request = Mock()
    request.client = Mock(host=ip)
    return request


def test_allows_requests_under_the_limit():
    request = _fake_request()
    for _ in range(5):
        enforce_rate_limit(request, bucket="test_bucket_a", max_attempts=5, window_seconds=60)
    # No exception — the 5th call is still within the 5-attempt budget.


def test_blocks_requests_over_the_limit():
    request = _fake_request()
    for _ in range(3):
        enforce_rate_limit(request, bucket="test_bucket_b", max_attempts=3, window_seconds=60)

    with pytest.raises(RateLimitExceededError):
        enforce_rate_limit(request, bucket="test_bucket_b", max_attempts=3, window_seconds=60)


def test_limit_is_per_bucket_not_global():
    request = _fake_request()
    for _ in range(3):
        enforce_rate_limit(request, bucket="test_bucket_c1", max_attempts=3, window_seconds=60)

    # A different bucket for the same client must have its own budget.
    enforce_rate_limit(request, bucket="test_bucket_c2", max_attempts=3, window_seconds=60)


def test_limit_is_per_client_ip():
    for _ in range(3):
        enforce_rate_limit(_fake_request("1.1.1.1"), bucket="test_bucket_d", max_attempts=3, window_seconds=60)

    # A different IP must not be blocked by another client's usage.
    enforce_rate_limit(_fake_request("2.2.2.2"), bucket="test_bucket_d", max_attempts=3, window_seconds=60)


def test_window_expiry_allows_requests_again():
    request = _fake_request()
    for _ in range(2):
        enforce_rate_limit(request, bucket="test_bucket_e", max_attempts=2, window_seconds=0.2)

    with pytest.raises(RateLimitExceededError):
        enforce_rate_limit(request, bucket="test_bucket_e", max_attempts=2, window_seconds=0.2)

    time.sleep(0.25)
    enforce_rate_limit(request, bucket="test_bucket_e", max_attempts=2, window_seconds=0.2)


def test_reset_all_clears_every_bucket():
    request = _fake_request()
    for _ in range(3):
        enforce_rate_limit(request, bucket="test_bucket_f", max_attempts=3, window_seconds=60)

    reset_all()

    enforce_rate_limit(request, bucket="test_bucket_f", max_attempts=3, window_seconds=60)


def test_google_login_returns_429_after_too_many_attempts(client):
    for _ in range(10):
        response = client.get("/auth/google/login", follow_redirects=False)
        assert response.status_code == 503  # not configured in this test env — reached before rate limiting

    response = client.get("/auth/google/login", follow_redirects=False)
    assert response.status_code == 429
    assert response.json()["error"] == "RATE_LIMIT_EXCEEDED"


def test_google_callback_returns_429_after_too_many_attempts(client):
    for _ in range(20):
        response = client.get(
            "/auth/google/callback", params={"code": "x", "state": "does-not-match"}, follow_redirects=False
        )
        assert response.status_code == 401  # mismatched state — reached before rate limiting

    response = client.get(
        "/auth/google/callback", params={"code": "x", "state": "does-not-match"}, follow_redirects=False
    )
    assert response.status_code == 429
