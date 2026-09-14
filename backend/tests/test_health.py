def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"


def test_ready_checks_database_and_skips_redis_when_not_configured(client):
    # Default test config uses QUEUE_BACKEND=inline (no Redis required).
    response = client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ready"
    check_names = [c["name"] for c in body["data"]["checks"]]
    assert check_names == ["database"]
    assert body["data"]["checks"][0]["healthy"] is True
