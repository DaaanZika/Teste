"""Small text-normalization helpers shared by OCR extraction and quick-entry parsing.

These are pure functions with no side effects so they're trivial to unit test
and reused identically by both `services.ocr.extractor` and
`services.finance.quick_expense_parser` — one parsing behavior, not two.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

_CNPJ_RE = re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b")
_CPF_RE = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")

_MONEY_RE = re.compile(
    r"R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}|\d{1,3}(?:\.\d{3})*|\d+)"
    r"|(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})\s*(?:reais|r\$)"
    r"|\b(\d+(?:[.,]\d{1,2})?)\s*reais\b",
    re.IGNORECASE,
)

_DATE_PATTERNS = (
    (re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b"), "%d/%m/%Y"),
    (re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{2})\b"), "%d/%m/%y"),
    (re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b"), "%Y-%m-%d"),
)

_RELATIVE_DATE_WORDS = {
    "hoje": 0,
    "ontem": -1,
    "anteontem": -2,
}

_MONTH_NAMES = {
    "janeiro": 1, "jan": 1,
    "fevereiro": 2, "fev": 2,
    "marco": 3, "março": 3, "mar": 3,
    "abril": 4, "abr": 4,
    "maio": 5, "mai": 5,
    "junho": 6, "jun": 6,
    "julho": 7, "jul": 7,
    "agosto": 8, "ago": 8,
    "setembro": 9, "set": 9,
    "outubro": 10, "out": 10,
    "novembro": 11, "nov": 11,
    "dezembro": 12, "dez": 12,
}


def normalize_whitespace(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text).strip()


def parse_money(text: str) -> Decimal | None:
    """Extract the first Brazilian-formatted currency amount found in `text`, or None."""
    match = _MONEY_RE.search(text)
    if not match:
        return None
    raw = next(g for g in match.groups() if g)
    return _to_decimal(raw)


def _to_decimal(raw: str) -> Decimal | None:
    raw = raw.strip()
    if "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    try:
        return Decimal(raw).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def parse_date(text: str, *, reference: date | None = None) -> date | None:
    """Extract a date from free text: numeric formats, relative words, or 'dia N'."""
    reference = reference or date.today()
    lowered = text.lower()

    for word, offset in _RELATIVE_DATE_WORDS.items():
        if word in lowered:
            return reference + timedelta(days=offset)

    for pattern, fmt in _DATE_PATTERNS:
        match = pattern.search(text)
        if match:
            candidate = match.group(0)
            try:
                return datetime.strptime(candidate, fmt).date()
            except ValueError:
                continue

    day_match = re.search(r"\bdia\s+(\d{1,2})\b", lowered)
    if day_match:
        day = int(day_match.group(1))
        if 1 <= day <= 31:
            try:
                return reference.replace(day=day)
            except ValueError:
                return None

    for name, month in _MONTH_NAMES.items():
        month_match = re.search(rf"\b(\d{{1,2}})\s+de\s+{name}\b", lowered)
        if month_match:
            day = int(month_match.group(1))
            try:
                return date(reference.year, month, day)
            except ValueError:
                return None

    return None


def find_cnpj(text: str) -> str | None:
    match = _CNPJ_RE.search(text)
    return _normalize_document(match.group(0)) if match else None


def find_cpf(text: str) -> str | None:
    # Avoid matching a CNPJ substring as a CPF.
    for match in _CPF_RE.finditer(text):
        candidate = match.group(0)
        span_text = text[max(0, match.start() - 3) : match.end() + 3]
        if "/" in span_text:
            continue
        return _normalize_document(candidate)
    return None


def _normalize_document(raw: str) -> str:
    return re.sub(r"[.\-/]", "", raw)
