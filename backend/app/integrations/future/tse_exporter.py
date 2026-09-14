"""Planned exporter to the TSE's official accountability format (SPCE/módulo web or successor).

NOT implemented in V1: the exact export layout is a legal/technical
requirement that must come from an official TSE source before being coded.
REVISÃO HUMANA — do not implement without a confirmed official specification.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class TSEExporter(ABC):
    @abstractmethod
    def export_campaign(self, campaign_id: str) -> bytes: ...


class NotImplementedTSEExporter(TSEExporter):
    def export_campaign(self, campaign_id: str) -> bytes:
        raise NotImplementedError(
            "TSE export is not implemented in V1. REVISÃO HUMANA required: the official "
            "export format must be confirmed against a TSE source before implementation."
        )
