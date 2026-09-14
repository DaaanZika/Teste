"""Planned email ingestion adapter (e.g. pulling receipts from Gmail). NOT implemented in V1."""
from __future__ import annotations

from abc import ABC, abstractmethod


class EmailProvider(ABC):
    @abstractmethod
    def fetch_new_messages(self) -> list[dict]: ...

    @abstractmethod
    def download_attachment(self, message_id: str, attachment_id: str) -> bytes: ...


class GmailProvider(EmailProvider):
    def __init__(self, *args, **kwargs) -> None:
        raise NotImplementedError(
            "GmailProvider is not implemented in V1. No Gmail/OAuth calls are made by this backend."
        )

    def fetch_new_messages(self) -> list[dict]:  # pragma: no cover
        raise NotImplementedError

    def download_attachment(self, message_id: str, attachment_id: str) -> bytes:  # pragma: no cover
        raise NotImplementedError
