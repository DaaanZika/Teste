"""app/api/routes/reports.py export endpoints — real HTTP round trip
through the actual expense/revenue data, not just the export_service
internals covered in test_export_service.py."""
from __future__ import annotations

import openpyxl
import io

from app.services.reports.export_service import DISCLAIMER


def _create_expense(client) -> str:
    response = client.post(
        "/expenses",
        json={"description": "Cartazes de campanha", "amount": "150.00", "supplier_name": "Gráfica Teste"},
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_export_expenses_csv_contains_disclaimer_and_data(client):
    _create_expense(client)
    response = client.get("/reports/expenses/export", params={"format": "csv"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert 'attachment; filename="despesas.csv"' in response.headers["content-disposition"]
    body = response.content.decode("utf-8-sig")
    assert DISCLAIMER in body
    assert "Gráfica Teste" in body


def test_export_expenses_xlsx_is_a_valid_workbook(client):
    _create_expense(client)
    response = client.get("/reports/expenses/export", params={"format": "xlsx"})
    assert response.status_code == 200
    assert "spreadsheetml" in response.headers["content-type"]
    workbook = openpyxl.load_workbook(io.BytesIO(response.content))
    assert workbook.active is not None


def test_export_expenses_pdf_has_valid_header(client):
    response = client.get("/reports/expenses/export", params={"format": "pdf"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content[:5] == b"%PDF-"


def test_export_revenues_default_format_is_csv(client):
    response = client.get("/reports/revenues/export")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")


def test_export_summary_as_key_value_pdf(client):
    response = client.get("/reports/summary/export", params={"format": "pdf"})
    assert response.status_code == 200
    assert response.content[:5] == b"%PDF-"


def test_export_documents_as_xlsx(client):
    response = client.get("/reports/documents/export", params={"format": "xlsx"})
    assert response.status_code == 200
    assert "spreadsheetml" in response.headers["content-type"]


def test_export_invalid_format_returns_422(client):
    response = client.get("/reports/expenses/export", params={"format": "docx"})
    assert response.status_code == 422
    assert response.json()["error"] == "VALIDATION_FAILED"
