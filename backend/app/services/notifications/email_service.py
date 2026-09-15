"""Outbound email (PROMPT 4 password reset; the SMTP settings themselves
already existed as optional config since PROMPT 3, unused until now).

Google/Drive/Gmail, and now email, are all optional per project principle
("nenhuma integração externa é obrigatória") — when SMTP isn't configured
this logs the message instead of raising, so password reset still "works"
in the sense that a token is generated and the flow doesn't 500; an
operator without SMTP configured reads the link from the server log.
"""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def is_configured() -> bool:
    settings = get_settings()
    return bool(settings.smtp_host and settings.smtp_from)


def send_email(*, to: str, subject: str, body: str) -> bool:
    """Returns True if actually sent via SMTP, False if only logged
    (SMTP not configured, or the send failed) — callers must not leak this
    boolean back to an unauthenticated caller (see auth.py forgot-password:
    the HTTP response is identical either way, to avoid email enumeration)."""
    settings = get_settings()
    if not is_configured():
        logger.warning("SMTP não configurado — e-mail para %s não enviado (apenas registrado): %s", to, body)
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from
    message["To"] = to
    message.set_content(body)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.starttls()
            if settings.smtp_user and settings.smtp_password:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(message)
        return True
    except (smtplib.SMTPException, OSError) as exc:
        logger.error("Falha ao enviar e-mail para %s via SMTP: %s", to, exc)
        return False
