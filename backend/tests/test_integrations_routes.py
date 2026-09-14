"""app/api/routes/integrations.py — /integrations/status must reflect real
state (never assume), and connect/disconnect must be ADMIN-only (RBAC
wired the same way as everything else — see test_permission_enforcement.py)."""
from __future__ import annotations

import uuid

import pytest

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.main import app as fastapi_app
from app.models.enums import Role
from app.models.user import User


@pytest.fixture()
def as_role(db_session):
    created_users: list[User] = []

    def _use(role: Role) -> User:
        unique = uuid.uuid4().hex[:8]
        user = User(name=f"Test {role.value}", email=f"integrations-{role.value.lower()}-{unique}@example.com", role=role, active=True)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        created_users.append(user)
        fastapi_app.dependency_overrides[get_current_user] = lambda: user
        return user

    yield _use

    fastapi_app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture()
def restore_backup_setting():
    settings = get_settings()
    original = settings.backup_storage_provider
    yield settings
    settings.backup_storage_provider = original


@pytest.fixture(autouse=True)
def _cleanup_gmail_connection(db_session):
    """The DB in this test suite isn't reset between tests (see
    conftest.py) — an active connection left by one test would leak into
    other tests that assume "no active gmail connection" as their starting
    state."""
    from app.services.integrations import google_tokens

    yield
    google_tokens.revoke_connection(db_session, "gmail")


def test_status_reports_all_sections(client, as_role, restore_backup_setting):
    restore_backup_setting.backup_storage_provider = None
    as_role(Role.VIEWER)  # VIEW_REPORTS is enough to see integration status

    response = client.get("/integrations/status")
    assert response.status_code == 200
    body = response.json()
    for key in ("google_oauth", "google_drive", "gmail", "backup", "database", "ocr"):
        assert key in body
        assert "connected" in body[key]

    assert body["google_drive"]["connected"] is False
    assert body["backup"]["connected"] is False
    assert body["database"]["connected"] is True


def test_status_reflects_configured_backup(client, as_role, restore_backup_setting):
    restore_backup_setting.backup_storage_provider = "google_drive"
    as_role(Role.VIEWER)

    response = client.get("/integrations/status")
    assert response.json()["backup"]["connected"] is True


def test_connect_requires_admin(client, as_role):
    as_role(Role.FINANCIAL)
    response = client.get("/integrations/google-drive/connect", follow_redirects=False)
    assert response.status_code == 403


def test_disconnect_requires_admin(client, as_role):
    as_role(Role.VIEWER)
    response = client.post("/integrations/google-drive/disconnect")
    assert response.status_code == 403


def test_admin_can_disconnect_even_when_not_connected(client, as_role):
    as_role(Role.ADMIN)
    response = client.post("/integrations/google-drive/disconnect")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "disconnected"


def test_gmail_connect_requires_admin(client, as_role):
    as_role(Role.FINANCIAL)
    response = client.get("/integrations/gmail/connect", follow_redirects=False)
    assert response.status_code == 403


def test_gmail_disconnect_requires_admin(client, as_role):
    as_role(Role.VIEWER)
    response = client.post("/integrations/gmail/disconnect")
    assert response.status_code == 403


def test_admin_can_disconnect_gmail_even_when_not_connected(client, as_role):
    as_role(Role.ADMIN)
    response = client.post("/integrations/gmail/disconnect")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "disconnected"


def test_gmail_scan_requires_manage_documents_permission(client, as_role):
    as_role(Role.VIEWER)  # can view but not manage documents
    response = client.post("/integrations/gmail/scan", json={})
    assert response.status_code == 403


def test_gmail_scan_without_connection_returns_not_configured(client, as_role):
    as_role(Role.FINANCIAL)
    response = client.post("/integrations/gmail/scan", json={})
    assert response.status_code == 503
    assert response.json()["error"] == "NOT_CONFIGURED"


def test_gmail_suggestions_list_is_visible_to_every_role(client, as_role):
    # Every role has VIEW_DOCUMENTS (see app/core/rbac.py _ALL_VIEW) —
    # confirms the dependency is wired, not that it discriminates by role.
    as_role(Role.VIEWER)
    response = client.get("/integrations/gmail/suggestions")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_gmail_reject_unknown_suggestion_returns_404(client, as_role):
    as_role(Role.FINANCIAL)
    response = client.post("/integrations/gmail/suggestions/does-not-exist/reject", json={})
    assert response.status_code == 404


def test_gmail_confirm_unknown_suggestion_returns_404(client, as_role):
    as_role(Role.FINANCIAL)
    response = client.post("/integrations/gmail/suggestions/does-not-exist/confirm")
    assert response.status_code == 404


def test_gmail_scan_then_confirm_end_to_end(client, as_role, db_session, monkeypatch):
    """Full route -> service -> document pipeline, HTTP to Gmail mocked. A
    scan alone must never create a Document; only confirm does."""
    import base64

    from app.services.integrations import gmail_service, google_tokens

    user = as_role(Role.FINANCIAL)
    google_tokens.save_connection(
        db_session,
        user_id=user.id,
        provider="gmail",
        scope="gmail.readonly",
        access_token="tok-e2e",
        refresh_token="refresh-e2e",
        expires_in_seconds=3600,
    )

    raw_bytes = b"%PDF-1.4 conteudo do recibo e2e"
    encoded = base64.urlsafe_b64encode(raw_bytes).decode().rstrip("=")

    message_list = {"messages": [{"id": "msg-e2e", "threadId": "thread-e2e"}]}
    message_detail = {
        "id": "msg-e2e",
        "threadId": "thread-e2e",
        "internalDate": "1700000000000",
        "payload": {
            "headers": [{"name": "From", "value": "fornecedor@example.com"}, {"name": "Subject", "value": "Recibo"}],
            "parts": [
                {"filename": "recibo-e2e.pdf", "mimeType": "application/pdf", "body": {"attachmentId": "att-e2e"}}
            ],
        },
    }

    def fake_get(url, headers=None, params=None, timeout=None):
        if url == gmail_service.GMAIL_API_BASE + "/messages":
            return _FakeGmailResponse(json_body=message_list)
        if url == gmail_service.GMAIL_API_BASE + "/messages/msg-e2e":
            return _FakeGmailResponse(json_body=message_detail)
        if url == gmail_service.GMAIL_API_BASE + "/messages/msg-e2e/attachments/att-e2e":
            return _FakeGmailResponse(json_body={"size": len(raw_bytes), "data": encoded})
        raise AssertionError(f"Unexpected GET {url}")

    monkeypatch.setattr(gmail_service.httpx, "get", fake_get)

    scan_response = client.post("/integrations/gmail/scan", json={})
    assert scan_response.status_code == 200
    new_suggestions = scan_response.json()["new_suggestions"]
    assert len(new_suggestions) == 1
    assert new_suggestions[0]["status"] == "PENDING"
    assert new_suggestions[0]["document_id"] is None
    suggestion_id = new_suggestions[0]["id"]

    # Listing filtered by status must reflect the same PENDING row.
    list_response = client.get("/integrations/gmail/suggestions", params={"status": "PENDING"})
    assert any(s["id"] == suggestion_id for s in list_response.json())

    confirm_response = client.post(f"/integrations/gmail/suggestions/{suggestion_id}/confirm")
    assert confirm_response.status_code == 200
    body = confirm_response.json()
    assert body["document"]["original_filename"] == "recibo-e2e.pdf"

    # Confirming again must fail — the suggestion is no longer PENDING.
    second_confirm = client.post(f"/integrations/gmail/suggestions/{suggestion_id}/confirm")
    assert second_confirm.status_code == 409


def test_gmail_reject_via_route(client, as_role, db_session):
    from app.models.enums import GmailSuggestionStatus
    from app.models.gmail_suggestion import GmailSuggestion

    as_role(Role.FINANCIAL)
    suggestion = GmailSuggestion(
        gmail_message_id="msg-reject-route",
        attachment_id="att-reject-route",
        attachment_filename="descartar.pdf",
        mime_type="application/pdf",
        status=GmailSuggestionStatus.PENDING,
    )
    db_session.add(suggestion)
    db_session.commit()
    db_session.refresh(suggestion)

    response = client.post(
        f"/integrations/gmail/suggestions/{suggestion.id}/reject", json={"reason": "Não é comprovante"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"
    assert response.json()["rejected_reason"] == "Não é comprovante"


class _FakeGmailResponse:
    def __init__(self, json_body=None, status_code=200):
        self._json = json_body or {}
        self.status_code = status_code

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")
