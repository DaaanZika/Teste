"""Confidence scoring for OCR results.

Combines Tesseract's own per-word confidence (when available) with how
many of the fields we look for were actually found. Either signal alone is
noisy — a document can OCR at 90% character accuracy while extracting zero
usable fields (bad layout), or extract a couple of fields from a noisy
scan. Low confidence routes the document to `HUMAN_REVIEW`; the user
corrects it and that correction is what the app trusts, not a guess.
"""
from __future__ import annotations

from app.models.enums import OCRConfidence
from app.services.ocr.extractor import ExtractedFields

_CRITICAL_FIELDS = ("valor", "data")


def score_confidence(
    *,
    engine_available: bool,
    mean_ocr_confidence: float | None,
    extracted: ExtractedFields,
) -> OCRConfidence:
    if not engine_available:
        return OCRConfidence.NONE

    critical_found = sum(1 for f in _CRITICAL_FIELDS if getattr(extracted, f) is not None)
    total_found = len(extracted.fields_found)

    if critical_found == 0 and total_found == 0:
        return OCRConfidence.LOW

    tesseract_score = mean_ocr_confidence if mean_ocr_confidence is not None else 50.0

    if critical_found == len(_CRITICAL_FIELDS) and total_found >= 4 and tesseract_score >= 60:
        return OCRConfidence.HIGH
    if critical_found >= 1 and total_found >= 2 and tesseract_score >= 35:
        return OCRConfidence.MEDIUM
    return OCRConfidence.LOW


def requires_human_review(confidence: OCRConfidence) -> bool:
    return confidence in (OCRConfidence.LOW, OCRConfidence.NONE)
