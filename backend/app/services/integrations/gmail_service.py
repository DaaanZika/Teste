"""Gmail attachment detection (PROMPT 3 §13).

Read-only, real Gmail API v1 calls over HTTPS (httpx) — no SDK. Detects
messages that *look like* they carry a receipt/invoice/expense document and
records one `GmailSuggestion` row per matching attachment. Nothing here
ever creates a `Document`, an `Expense`, or a `Revenue` on its own: a human
must call `confirm_suggestion` explicitly, which then runs the attachment
through the exact same upload pipeline (`document_service.upload_document`)
used for a manual upload — same validation, same duplicate detection, same
audit trail. `reject_suggestion` discards a suggestion without ever
touching the mailbox (no delete/label/modify scope is requested — see
GMAIL_SCOPES in app/services/auth/google_oauth.py).
"""
from __future__ import annotations

import base64
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import ConflictError, NotConfiguredError, NotFoundError
from app.core.tenancy import resolve_campaign_id
from app.models.campaign import Campaign
from app.models.enums import GmailSuggestionStatus
from app.models.gmail_suggestion import GmailSuggestion
from app.services.documents import document_service
from app.services.integrations.google_tokens import get_valid_access_token

logger = logging.getLogger("app.integrations.gmail")

GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"

# Portuguese and English terms a Brazilian campaign's receipts/invoices are
# likely to use, restricted to messages that actually carry an attachment.
# This is a detection heuristic, not an official classification — every
# match still requires human confirmation before anything is imported.
DETECTION_QUERY = (
    "has:attachment "
    '(nota OR "nota fiscal" OR recibo OR comprovante OR fatura OR boleto OR invoice OR receipt)'
)

DEFAULT_MAX_RESULTS = 20


def _require_connected(db: Session) -> str:
    token = get_valid_access_token(db, "gmail")
    if token is None:
        raise NotConfiguredError(
            "Gmail não está conectado. Conecte em Configurações > Integrações ou "
            "ignore esta funcionalidade — o sistema continua funcionando sem ela."
        )
    return token


def _header(headers: list[dict], name: str) -> str | None:
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value")
    return None


def _iter_attachment_parts(payload: dict):
    """Gmail nests attachments inside `payload.parts`, which can itself
    contain nested `parts` (e.g. multipart/mixed wrapping multipart/alternative)
    — walk the whole tree instead of assuming one level."""
    for part in payload.get("parts", []) or []:
        filename = part.get("filename")
        attachment_id = (part.get("body") or {}).get("attachmentId")
        if filename and attachment_id:
            yield {
                "filename": filename,
                "mime_type": part.get("mimeType", "application/octet-stream"),
                "attachment_id": attachment_id,
            }
        if part.get("parts"):
            yield from _iter_attachment_parts(part)


def scan_inbox(
    db: Session, *, organization_id: str, campaign_id: str | None = None, max_results: int = DEFAULT_MAX_RESULTS
) -> list[GmailSuggestion]:
    """Searches the connected mailbox and records a PENDING suggestion for
    every not-yet-seen attachment that matches an allowed upload type
    (same extensions/MIME types as a manual upload — see Settings). Safe to
    call repeatedly: an already-suggested (message, attachment) pair is
    skipped, never duplicated. `campaign_id` (PROMPT 4) is validated/
    resolved against `organization_id` up front, same as a manual upload —
    every suggestion this creates is anchored to a real, org-owned campaign."""
    campaign_id = resolve_campaign_id(db, organization_id, campaign_id)
    token = _require_connected(db)
    settings = get_settings()
    headers = {"Authorization": f"Bearer {token}"}

    response = httpx.get(
        f"{GMAIL_API_BASE}/messages",
        headers=headers,
        params={"q": DETECTION_QUERY, "maxResults": max_results},
        timeout=15,
    )
    response.raise_for_status()
    message_refs = response.json().get("messages", [])

    created: list[GmailSuggestion] = []
    for ref in message_refs:
        message_id = ref["id"]

        detail_response = httpx.get(
            f"{GMAIL_API_BASE}/messages/{message_id}", headers=headers, params={"format": "full"}, timeout=15
        )
        detail_response.raise_for_status()
        message = detail_response.json()
        payload = message.get("payload", {})
        message_headers = payload.get("headers", [])

        internal_date_ms = message.get("internalDate")
        received_at = (
            datetime.fromtimestamp(int(internal_date_ms) / 1000, tz=timezone.utc) if internal_date_ms else None
        )

        for attachment in _iter_attachment_parts(payload):
            extension = (
                "." + attachment["filename"].rsplit(".", 1)[-1].lower() if "." in attachment["filename"] else ""
            )
            if extension not in settings.allowed_upload_extensions:
                continue

            already_seen = db.execute(
                select(GmailSuggestion).where(
                    GmailSuggestion.gmail_message_id == message_id,
                    GmailSuggestion.attachment_id == attachment["attachment_id"],
                )
            ).scalar_one_or_none()
            if already_seen is not None:
                continue

            suggestion = GmailSuggestion(
                gmail_message_id=message_id,
                gmail_thread_id=message.get("threadId"),
                sender=_header(message_headers, "From"),
                subject=_header(message_headers, "Subject"),
                received_at=received_at,
                attachment_id=attachment["attachment_id"],
                attachment_filename=attachment["filename"],
                mime_type=attachment["mime_type"],
                campaign_id=campaign_id,
                status=GmailSuggestionStatus.PENDING,
            )
            db.add(suggestion)
            created.append(suggestion)

    db.commit()
    for suggestion in created:
        db.refresh(suggestion)
    return created


def list_suggestions(
    db: Session, *, organization_id: str, status: GmailSuggestionStatus | None = None
) -> list[GmailSuggestion]:
    stmt = (
        select(GmailSuggestion)
        .join(Campaign, GmailSuggestion.campaign_id == Campaign.id)
        .where(Campaign.organization_id == organization_id)
        .order_by(GmailSuggestion.created_at.desc())
    )
    if status is not None:
        stmt = stmt.where(GmailSuggestion.status == status)
    return list(db.execute(stmt).scalars())


def _get_suggestion_in_org(db: Session, suggestion_id: str, *, organization_id: str) -> GmailSuggestion:
    suggestion = db.get(GmailSuggestion, suggestion_id)
    if suggestion is None or suggestion.campaign_id is None:
        raise NotFoundError(f"Sugestão do Gmail {suggestion_id} não encontrada.")
    campaign = db.get(Campaign, suggestion.campaign_id)
    if campaign is None or campaign.organization_id != organization_id:
        raise NotFoundError(f"Sugestão do Gmail {suggestion_id} não encontrada.")
    return suggestion


def confirm_suggestion(db: Session, suggestion_id: str, *, user_id: str | None = None, organization_id: str):
    """Downloads the attachment for real and runs it through the normal
    upload pipeline — the only path by which a Gmail suggestion ever
    becomes a `Document` (PROMPT 3 §45: no silent/automatic import).
    `organization_id` (PROMPT 4) scopes both the suggestion lookup itself
    and the resulting upload's duplicate detection."""
    suggestion = _get_suggestion_in_org(db, suggestion_id, organization_id=organization_id)
    if suggestion.status != GmailSuggestionStatus.PENDING:
        raise ConflictError(f"Sugestão {suggestion_id} já foi {suggestion.status.value.lower()}.")

    token = _require_connected(db)
    response = httpx.get(
        f"{GMAIL_API_BASE}/messages/{suggestion.gmail_message_id}/attachments/{suggestion.attachment_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    response.raise_for_status()
    encoded = response.json()["data"]
    content = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))

    result = document_service.upload_document(
        db,
        filename=suggestion.attachment_filename,
        content=content,
        mime_type=suggestion.mime_type,
        campaign_id=suggestion.campaign_id,
        user_id=user_id,
        organization_id=organization_id,
    )

    suggestion.status = GmailSuggestionStatus.IMPORTED
    suggestion.document_id = result.document.id
    db.commit()
    db.refresh(suggestion)
    return result


def reject_suggestion(
    db: Session, suggestion_id: str, *, reason: str | None = None, organization_id: str
) -> GmailSuggestion:
    suggestion = _get_suggestion_in_org(db, suggestion_id, organization_id=organization_id)
    if suggestion.status != GmailSuggestionStatus.PENDING:
        raise ConflictError(f"Sugestão {suggestion_id} já foi {suggestion.status.value.lower()}.")

    suggestion.status = GmailSuggestionStatus.REJECTED
    suggestion.rejected_reason = reason
    db.commit()
    db.refresh(suggestion)
    return suggestion
