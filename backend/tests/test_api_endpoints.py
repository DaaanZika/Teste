from app.models.enums import RevenueStatus


def test_create_revenue_pending_information_when_incomplete(client):
    response = client.post("/revenues", json={"amount": "300.00"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == RevenueStatus.PENDING_INFORMATION.value
    assert body["missing_fields"] is not None


def test_create_revenue_with_negative_amount_rejected(client):
    response = client.post("/revenues", json={"amount": "-5.00"})
    assert response.status_code == 422


def test_list_and_get_revenue(client):
    created = client.post(
        "/revenues", json={"amount": "500.00", "date": "2024-02-01", "donor_name": "Fulano de Tal"}
    ).json()

    listing = client.get("/revenues")
    assert listing.status_code == 200
    assert any(r["id"] == created["id"] for r in listing.json())

    single = client.get(f"/revenues/{created['id']}")
    assert single.status_code == 200
    assert single.json()["id"] == created["id"]


def test_reports_endpoints_return_json(client):
    for path in ("/reports/summary", "/reports/documents"):
        response = client.get(path)
        assert response.status_code == 200

    for path in ("/reports/expenses", "/reports/revenues"):
        response = client.get(path)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


def test_compliance_alerts_endpoint(client):
    # Creating an expense without a document raises a "despesa sem documento" alert.
    client.post("/expenses", json={"description": "Teste alerta", "amount": "42.00"})
    response = client.get("/compliance/alerts")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_compliance_rules_starts_empty_in_v1(client):
    response = client.get("/compliance/rules")
    assert response.status_code == 200
    assert response.json() == []


def test_audit_log_records_expense_creation(client):
    created = client.post(
        "/expenses", json={"description": "Auditoria teste", "amount": "77.00"}
    ).json()

    response = client.get("/audit", params={"entity": "expense", "entity_id": created["id"]})
    assert response.status_code == 200
    logs = response.json()
    assert len(logs) >= 1
    assert logs[0]["entity"] == "expense"
    assert logs[0]["entity_id"] == created["id"]


def test_finance_balance_is_consistent_with_summary(client):
    client.post("/revenues", json={"amount": "1000.00", "date": "2024-01-01", "donor_name": "Doador"})
    client.post("/expenses", json={"description": "Gasto", "amount": "300.00", "date": "2024-01-02"})

    summary = client.get("/finance/summary").json()
    balance = client.get("/finance/balance").json()

    assert balance["balance"] == summary["balance"]


def test_finance_summary_and_balance_accept_date_range(client):
    client.post("/revenues", json={"amount": "100.00", "date": "2024-05-01", "donor_name": "Doador"})
    client.post("/revenues", json={"amount": "900.00", "date": "2024-06-15", "donor_name": "Doador"})
    client.post("/expenses", json={"description": "Fora do periodo", "amount": "50.00", "date": "2024-04-01"})

    summary = client.get(
        "/finance/summary", params={"start_date": "2024-05-01", "end_date": "2024-05-31"}
    ).json()
    balance = client.get(
        "/finance/balance", params={"start_date": "2024-05-01", "end_date": "2024-05-31"}
    ).json()

    assert summary["total_revenues"] == "100.00"
    assert summary["total_expenses"] == "0.00"
    assert balance["total_revenues"] == "100.00"
    assert balance["balance"] == "100.00"


def test_finance_totals_by_category_type_param_selects_revenue_or_expense(client):
    client.post(
        "/revenues",
        json={"amount": "500.00", "date": "2024-03-01", "donor_name": "Doador", "source_type": "Pessoa física"},
    )
    client.post(
        "/expenses",
        json={"description": "Gasolina", "amount": "80.00", "date": "2024-03-02", "category": "Combustível"},
    )

    expense_breakdown = client.get("/finance/totals/category").json()
    assert any(row["category"] == "Combustível" for row in expense_breakdown)
    assert not any(row["category"] == "Pessoa física" for row in expense_breakdown)

    revenue_breakdown = client.get("/finance/totals/category", params={"type": "REVENUE"}).json()
    assert any(row["category"] == "Pessoa física" for row in revenue_breakdown)
    assert not any(row["category"] == "Combustível" for row in revenue_breakdown)
