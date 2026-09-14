"""PUT /expenses/{id} — untested route until this file: plain field
updates, linking a document after the fact (and the LINK_DOCUMENT audit
action that's supposed to fire specifically for that), and the 404/403
edges."""
from __future__ import annotations

from app.models.enums import AuditAction, DocumentLinkStatus, ExpenseStatus


def _create_expense(client, **overrides) -> dict:
    payload = {"description": "Material gráfico", "amount": "80.00"}
    payload.update(overrides)
    response = client.post("/expenses", json=payload)
    assert response.status_code == 200
    return response.json()


def _upload_document(client) -> str:
    response = client.post(
        "/documents/upload",
        files={"file": ("recibo.png", b"\x89PNG\r\n\x1a\nbytes-unicos-para-teste", "image/png")},
    )
    assert response.status_code == 200
    return response.json()["document"]["id"]


def test_update_plain_field(client):
    expense = _create_expense(client)

    response = client.put(f"/expenses/{expense['id']}", json={"supplier_name": "Gráfica Nova"})
    assert response.status_code == 200
    assert response.json()["supplier_name"] == "Gráfica Nova"


def test_linking_a_document_via_update_attaches_it_and_completes_the_expense(client):
    expense = _create_expense(client, date="2024-03-01", supplier_name="Gráfica X")
    assert expense["status"] == ExpenseStatus.PENDING_INFORMATION.value  # no document yet
    assert expense["document_status"] == DocumentLinkStatus.PENDING.value

    document_id = _upload_document(client)
    response = client.put(f"/expenses/{expense['id']}", json={"document_id": document_id})

    assert response.status_code == 200
    body = response.json()
    assert body["document_status"] == DocumentLinkStatus.ATTACHED.value
    assert body["status"] == ExpenseStatus.COMPLETE.value


def test_linking_a_document_via_update_records_link_document_audit_action(client):
    expense = _create_expense(client)
    document_id = _upload_document(client)

    client.put(f"/expenses/{expense['id']}", json={"document_id": document_id})

    audit_response = client.get("/audit", params={"entity": "expense", "entity_id": expense["id"]})
    assert audit_response.status_code == 200
    actions = [entry["action"] for entry in audit_response.json()]
    assert AuditAction.LINK_DOCUMENT.value in actions
    # The original creation is still a CREATE, not overwritten.
    assert AuditAction.CREATE.value in actions


def test_update_without_document_id_records_plain_update_action(client):
    expense = _create_expense(client)

    client.put(f"/expenses/{expense['id']}", json={"supplier_name": "Outro Fornecedor"})

    audit_response = client.get("/audit", params={"entity": "expense", "entity_id": expense["id"]})
    actions = [entry["action"] for entry in audit_response.json()]
    assert AuditAction.UPDATE.value in actions
    assert AuditAction.LINK_DOCUMENT.value not in actions


def test_update_with_unknown_document_id_returns_404(client):
    expense = _create_expense(client)

    response = client.put(f"/expenses/{expense['id']}", json={"document_id": "does-not-exist"})
    assert response.status_code == 404


def test_update_unknown_expense_returns_404(client):
    response = client.put("/expenses/does-not-exist", json={"supplier_name": "X"})
    assert response.status_code == 404
