def test_create_and_list_campaign(client):
    response = client.post(
        "/campaigns",
        json={"name": "Campanha Teste 2026", "election_year": 2026, "office": "Prefeito"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Campanha Teste 2026"
    assert body["status"] == "ACTIVE"

    listing = client.get("/campaigns")
    assert listing.status_code == 200
    assert any(c["id"] == body["id"] for c in listing.json())


def test_get_nonexistent_campaign_returns_404(client):
    response = client.get("/campaigns/does-not-exist")
    assert response.status_code == 404


def test_update_campaign(client):
    created = client.post("/campaigns", json={"name": "Original"}).json()
    updated = client.put(f"/campaigns/{created['id']}", json={"name": "Atualizada", "status": "SUSPENDED"})
    assert updated.status_code == 200
    assert updated.json()["name"] == "Atualizada"
    assert updated.json()["status"] == "SUSPENDED"
