from app.models.enums import DocumentLinkStatus, ExpenseStatus


def test_quick_expense_creates_pending_information_when_data_missing(client):
    response = client.post("/expenses/quick", json={"text": "Impressão de material 850"})
    assert response.status_code == 200
    body = response.json()

    assert body["amount"] == "850.00"
    assert body["status"] == ExpenseStatus.PENDING_INFORMATION.value
    assert "data" in body["missing_fields"]
    assert "documento" in body["missing_fields"]
    assert body["document_status"] == DocumentLinkStatus.PENDING.value


def test_quick_expense_examples_from_spec_do_not_block_creation(client):
    for text in ("R$ 850 gráfica ABC", "Gasolina 230 reais ontem", "Aluguel comitê 3500 dia 10", "Uber 86,40"):
        response = client.post("/expenses/quick", json={"text": text})
        assert response.status_code == 200, f"failed for: {text}"
        assert response.json()["source_text"] == text


def test_create_expense_with_negative_amount_is_rejected(client):
    response = client.post("/expenses", json={"description": "teste", "amount": "-10.00"})
    assert response.status_code == 422


def test_create_complete_expense_is_marked_complete(client):
    upload = client.post(
        "/documents/upload",
        files={"file": ("recibo_despesa.png", b"\x89PNG\r\n\x1a\nfake-but-unique-bytes-1", "image/png")},
    )
    # This tiny payload is not a real PNG, so we only use its id for linking,
    # not for OCR processing, in this test.
    document_id = upload.json()["document"]["id"]

    response = client.post(
        "/expenses",
        json={
            "description": "Combustível para o comitê",
            "amount": "150.00",
            "date": "2024-05-10",
            "supplier_name": "Posto Central",
            "document_id": document_id,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == ExpenseStatus.COMPLETE.value
    assert body["missing_fields"] is None
    assert body["document_status"] == DocumentLinkStatus.ATTACHED.value


def test_expense_feeds_finance_summary(client):
    client.post(
        "/expenses",
        json={"description": "Aluguel", "amount": "1000.00", "date": "2024-01-05", "supplier_name": "Imobiliária X"},
    )
    response = client.get("/finance/summary")
    assert response.status_code == 200
    body = response.json()
    assert float(body["total_expenses"]) >= 1000.00
