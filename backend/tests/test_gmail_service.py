"""app/services/integrations/gmail_service.py — detection never imports
anything by itself; only confirm_suggestion (a human action) does, and it
runs the attachment through the same upload pipeline as a manual upload.
All Gmail API calls are mocked — nothing here talks to a real mailbox.

PROMPT 4: every call takes organization_id explicitly, the same as the
route layer supplies it from the session — never trusted from elsewhere.
"""
from __future__ import annotations

import base64
import uuid

import pytest

from app.core.exceptions import ConflictError, NotConfiguredError
from app.models.campaign import Campaign
from app.models.enums import GmailSuggestionStatus
from app.models.gmail_suggestion import GmailSuggestion
from app.models.organization import Organization
from app.services.integrations import gmail_service


@pytest.fixture(autouse=True)
def _cleanup_gmail_connection(db_session):
    from app.services.integrations import google_tokens

    yield
    google_tokens.revoke_connection(db_session, "gmail")


@pytest.fixture()
def connected_user(db_session):
    from app.models.enums import Role
    from app.models.user import User

    unique = uuid.uuid4().hex[:8]
    org = Organization(name=f"Org {unique}", slug=f"org-{unique}")
    db_session.add(org)
    db_session.flush()
    u = User(
        name="Admin", email=f"gmail-admin-{unique}@example.com", role=Role.ADMIN, active=True, organization_id=org.id
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture()
def connected_gmail(db_session, connected_user):
    from app.services.integrations import google_tokens

    google_tokens.save_connection(
        db_session,
        user_id=connected_user.id,
        provider="gmail",
        scope="gmail.readonly",
        access_token="tok-valid",
        refresh_token="refresh-1",
        expires_in_seconds=3600,
    )
    return connected_user


@pytest.fixture()
def campaign_for(db_session):
    """A real, org-owned campaign for a given user's organization —
    suggestions created directly (bypassing scan_inbox's own resolution)
    need a genuine campaign_id to be reachable through the org boundary."""

    def _make(user) -> Campaign:
        unique = uuid.uuid4().hex[:8]
        c = Campaign(name=f"Campanha {unique}", organization_id=user.organization_id)
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)
        return c

    return _make


class _FakeResponse:
    def __init__(self, json_body=None, status_code=200):
        self._json = json_body or {}
        self.status_code = status_code

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


MESSAGE_LIST = {"messages": [{"id": "msg-1", "threadId": "thread-1"}]}

MESSAGE_DETAIL = {
    "id": "msg-1",
    "threadId": "thread-1",
    "internalDate": "1700000000000",
    "payload": {
        "headers": [
            {"name": "From", "value": "fornecedor@example.com"},
            {"name": "Subject", "value": "Nota fiscal referente ao serviço"},
        ],
        "parts": [
            {"mimeType": "text/plain", "body": {}},
            {
                "filename": "nota-fiscal.pdf",
                "mimeType": "application/pdf",
                "body": {"attachmentId": "att-1", "size": 1234},
            },
            {
                "filename": "assinatura.png",  # image without a matching term is still allowed by extension
                "mimeType": "image/png",
                "body": {"attachmentId": "att-2", "size": 500},
            },
            {
                "filename": "planilha.xlsx",  # not an allowed upload extension — must be skipped
                "mimeType": "application/vnd.ms-excel",
                "body": {"attachmentId": "att-3", "size": 200},
            },
        ],
    },
}


def test_scan_without_connection_raises_not_configured(db_session):
    unique = uuid.uuid4().hex[:8]
    org = Organization(name=f"Org {unique}", slug=f"org-{unique}")
    db_session.add(org)
    db_session.commit()
    with pytest.raises(NotConfiguredError):
        gmail_service.scan_inbox(db_session, organization_id=org.id)


def test_scan_creates_suggestions_for_allowed_attachments_only(monkeypatch, db_session, connected_gmail):
    def fake_get(url, headers=None, params=None, timeout=None):
        if url == gmail_service.GMAIL_API_BASE + "/messages":
            assert params["q"] == gmail_service.DETECTION_QUERY
            return _FakeResponse(json_body=MESSAGE_LIST)
        if url == gmail_service.GMAIL_API_BASE + "/messages/msg-1":
            return _FakeResponse(json_body=MESSAGE_DETAIL)
        raise AssertionError(f"Unexpected GET {url}")

    monkeypatch.setattr(gmail_service.httpx, "get", fake_get)

    created = gmail_service.scan_inbox(db_session, organization_id=connected_gmail.organization_id, max_results=10)

    filenames = {s.attachment_filename for s in created}
    assert filenames == {"nota-fiscal.pdf", "assinatura.png"}
    assert "planilha.xlsx" not in filenames

    pdf_suggestion = next(s for s in created if s.attachment_filename == "nota-fiscal.pdf")
    assert pdf_suggestion.sender == "fornecedor@example.com"
    assert pdf_suggestion.subject == "Nota fiscal referente ao serviço"
    assert pdf_suggestion.status == GmailSuggestionStatus.PENDING
    assert pdf_suggestion.gmail_message_id == "msg-1"
    assert pdf_suggestion.received_at is not None
    assert pdf_suggestion.campaign_id is not None


def test_scan_is_idempotent_across_reruns(monkeypatch, db_session, connected_gmail):
    # Distinct message/attachment ids from every other test in this file —
    # the DB isn't reset between tests (see conftest.py), so reusing "msg-1"
    # would find them already suggested by an earlier test, not by this
    # test's own first call.
    message_list = {"messages": [{"id": "msg-idem", "threadId": "thread-idem"}]}
    message_detail = {
        **MESSAGE_DETAIL,
        "id": "msg-idem",
        "threadId": "thread-idem",
        "payload": {
            **MESSAGE_DETAIL["payload"],
            "parts": [
                {
                    "filename": "nota-idem.pdf",
                    "mimeType": "application/pdf",
                    "body": {"attachmentId": "att-idem-1", "size": 1234},
                },
                {
                    "filename": "recibo-idem.png",
                    "mimeType": "image/png",
                    "body": {"attachmentId": "att-idem-2", "size": 500},
                },
            ],
        },
    }

    def fake_get(url, headers=None, params=None, timeout=None):
        if url == gmail_service.GMAIL_API_BASE + "/messages":
            return _FakeResponse(json_body=message_list)
        return _FakeResponse(json_body=message_detail)

    monkeypatch.setattr(gmail_service.httpx, "get", fake_get)

    first = gmail_service.scan_inbox(db_session, organization_id=connected_gmail.organization_id)
    second = gmail_service.scan_inbox(db_session, organization_id=connected_gmail.organization_id)

    assert len(first) == 2
    assert len(second) == 0  # both attachments already suggested — not duplicated


def test_list_suggestions_filters_by_status(db_session, connected_gmail, campaign_for):
    campaign = campaign_for(connected_gmail)
    s1 = GmailSuggestion(
        campaign_id=campaign.id,
        gmail_message_id="m1",
        attachment_id="a1",
        attachment_filename="a.pdf",
        mime_type="application/pdf",
        status=GmailSuggestionStatus.PENDING,
    )
    s2 = GmailSuggestion(
        campaign_id=campaign.id,
        gmail_message_id="m2",
        attachment_id="a2",
        attachment_filename="b.pdf",
        mime_type="application/pdf",
        status=GmailSuggestionStatus.REJECTED,
    )
    db_session.add_all([s1, s2])
    db_session.commit()

    pending = gmail_service.list_suggestions(
        db_session, organization_id=connected_gmail.organization_id, status=GmailSuggestionStatus.PENDING
    )
    assert {s.id for s in pending} >= {s1.id}
    assert s2.id not in {s.id for s in pending}


def test_confirm_suggestion_downloads_and_uploads_document(monkeypatch, db_session, connected_gmail, campaign_for):
    campaign = campaign_for(connected_gmail)
    suggestion = GmailSuggestion(
        campaign_id=campaign.id,
        gmail_message_id="msg-confirm",
        attachment_id="att-confirm",
        attachment_filename="recibo.pdf",
        mime_type="application/pdf",
        status=GmailSuggestionStatus.PENDING,
    )
    db_session.add(suggestion)
    db_session.commit()
    db_session.refresh(suggestion)

    raw_bytes = b"%PDF-1.4 conteudo do recibo"
    encoded = base64.urlsafe_b64encode(raw_bytes).decode().rstrip("=")

    def fake_get(url, headers=None, timeout=None, params=None):
        assert url == f"{gmail_service.GMAIL_API_BASE}/messages/msg-confirm/attachments/att-confirm"
        return _FakeResponse(json_body={"size": len(raw_bytes), "data": encoded})

    monkeypatch.setattr(gmail_service.httpx, "get", fake_get)

    result = gmail_service.confirm_suggestion(
        db_session, suggestion.id, user_id=connected_gmail.id, organization_id=connected_gmail.organization_id
    )

    assert result.document.original_filename == "recibo.pdf"
    db_session.refresh(suggestion)
    assert suggestion.status == GmailSuggestionStatus.IMPORTED
    assert suggestion.document_id == result.document.id


def test_confirm_suggestion_twice_raises_conflict(monkeypatch, db_session, connected_gmail, campaign_for):
    campaign = campaign_for(connected_gmail)
    suggestion = GmailSuggestion(
        campaign_id=campaign.id,
        gmail_message_id="msg-confirm-2",
        attachment_id="att-confirm-2",
        attachment_filename="recibo2.pdf",
        mime_type="application/pdf",
        status=GmailSuggestionStatus.IMPORTED,
    )
    db_session.add(suggestion)
    db_session.commit()
    db_session.refresh(suggestion)

    with pytest.raises(ConflictError):
        gmail_service.confirm_suggestion(db_session, suggestion.id, organization_id=connected_gmail.organization_id)


def test_confirm_suggestion_from_another_organization_is_not_found(db_session, connected_gmail, campaign_for):
    """A suggestion belonging to a different organization must 404, never
    be confirmed by this caller."""
    from app.core.exceptions import NotFoundError

    campaign = campaign_for(connected_gmail)
    suggestion = GmailSuggestion(
        campaign_id=campaign.id,
        gmail_message_id="msg-cross-org",
        attachment_id="att-cross-org",
        attachment_filename="recibo-cross.pdf",
        mime_type="application/pdf",
        status=GmailSuggestionStatus.PENDING,
    )
    db_session.add(suggestion)
    db_session.commit()
    db_session.refresh(suggestion)

    unique = uuid.uuid4().hex[:8]
    other_org = Organization(name=f"Other {unique}", slug=f"other-{unique}")
    db_session.add(other_org)
    db_session.commit()

    with pytest.raises(NotFoundError):
        gmail_service.confirm_suggestion(db_session, suggestion.id, organization_id=other_org.id)


def test_reject_suggestion_never_touches_mailbox(monkeypatch, db_session, connected_gmail, campaign_for):
    campaign = campaign_for(connected_gmail)
    suggestion = GmailSuggestion(
        campaign_id=campaign.id,
        gmail_message_id="msg-reject",
        attachment_id="att-reject",
        attachment_filename="irrelevante.pdf",
        mime_type="application/pdf",
        status=GmailSuggestionStatus.PENDING,
    )
    db_session.add(suggestion)
    db_session.commit()
    db_session.refresh(suggestion)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("reject_suggestion must never call the Gmail API")

    monkeypatch.setattr(gmail_service.httpx, "get", fail_if_called)
    monkeypatch.setattr(gmail_service.httpx, "post", fail_if_called)
    monkeypatch.setattr(gmail_service.httpx, "delete", fail_if_called)

    result = gmail_service.reject_suggestion(
        db_session, suggestion.id, reason="Não é um documento fiscal", organization_id=connected_gmail.organization_id
    )

    assert result.status == GmailSuggestionStatus.REJECTED
    assert result.rejected_reason == "Não é um documento fiscal"


def test_reject_suggestion_twice_raises_conflict(db_session, connected_gmail, campaign_for):
    campaign = campaign_for(connected_gmail)
    suggestion = GmailSuggestion(
        campaign_id=campaign.id,
        gmail_message_id="msg-reject-2",
        attachment_id="att-reject-2",
        attachment_filename="irrelevante2.pdf",
        mime_type="application/pdf",
        status=GmailSuggestionStatus.REJECTED,
    )
    db_session.add(suggestion)
    db_session.commit()
    db_session.refresh(suggestion)

    with pytest.raises(ConflictError):
        gmail_service.reject_suggestion(db_session, suggestion.id, organization_id=connected_gmail.organization_id)
