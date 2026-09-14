"""Extracts structured fields from raw OCR text.

Absolute rule: a field that cannot be confidently located in the text is
`None`. Nothing here guesses or infers a value that isn't actually present
in the OCR output — see PROMPT 1 section 8: "campo não encontrado = null".
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.utils.text import find_cnpj, find_cpf, normalize_whitespace, parse_date, parse_money

_PAYMENT_KEYWORDS = {
    "pix": "PIX",
    "dinheiro": "DINHEIRO",
    "cartao de credito": "CARTAO_CREDITO",
    "cartão de crédito": "CARTAO_CREDITO",
    "cartao de debito": "CARTAO_DEBITO",
    "cartão de débito": "CARTAO_DEBITO",
    "cartao credito": "CARTAO_CREDITO",
    "cartao debito": "CARTAO_DEBITO",
    "boleto": "BOLETO",
    "cheque": "CHEQUE",
    "transferencia": "TRANSFERENCIA",
    "transferência": "TRANSFERENCIA",
    "ted": "TRANSFERENCIA",
    "doc": "TRANSFERENCIA",
}

_DOCUMENT_NUMBER_RE = re.compile(
    r"(?:n[uú]mero|n[ºo°\.]{1,2}|nf-?e|cupom fiscal|nota fiscal)\s*[:\-]?\s*(\d{2,15})",
    re.IGNORECASE,
)

_RAZAO_SOCIAL_RE = re.compile(r"raz[aã]o\s+social\s*[:\-]?\s*(.{3,120})", re.IGNORECASE)

_QUANTITY_RE = re.compile(r"\b(\d{1,4})\s*(?:un|unid|unidade|unidades|x)\b", re.IGNORECASE)


@dataclass
class ExtractedItem:
    description: str | None = None
    quantity: Decimal | None = None
    unit_value: Decimal | None = None
    total_value: Decimal | None = None


@dataclass
class ExtractedFields:
    data: date | None = None
    valor: Decimal | None = None
    fornecedor: str | None = None
    razao_social: str | None = None
    cnpj: str | None = None
    cpf: str | None = None
    descricao: str | None = None
    numero_documento: str | None = None
    quantidade: Decimal | None = None
    forma_pagamento: str | None = None
    itens: list[ExtractedItem] = field(default_factory=list)
    fields_found: list[str] = field(default_factory=list)
    fields_total: int = 10


def extract_fields(ocr_text: str) -> ExtractedFields:
    if not ocr_text or not ocr_text.strip():
        return ExtractedFields()

    text = normalize_whitespace(ocr_text)
    lines = [normalize_whitespace(l) for l in ocr_text.splitlines() if l.strip()]

    result = ExtractedFields()

    result.data = parse_date(text)
    result.valor = parse_money(text)
    result.cnpj = find_cnpj(text)
    result.cpf = find_cpf(text)

    doc_number_match = _DOCUMENT_NUMBER_RE.search(text)
    if doc_number_match:
        result.numero_documento = doc_number_match.group(1)

    razao_match = _RAZAO_SOCIAL_RE.search(text)
    if razao_match:
        result.razao_social = normalize_whitespace(razao_match.group(1)).rstrip(".,;")[:120]

    if lines:
        # Best-effort heuristic: the first non-trivial line of a receipt is
        # usually the trade name (fornecedor). Only used when it looks like
        # text, not a lone number/date/code.
        for candidate in lines[:3]:
            if len(candidate) >= 3 and not re.fullmatch(r"[\d\W]+", candidate):
                result.fornecedor = candidate[:255]
                break

    lowered = text.lower()
    for keyword, normalized in _PAYMENT_KEYWORDS.items():
        if keyword in lowered:
            result.forma_pagamento = normalized
            break

    quantity_match = _QUANTITY_RE.search(text)
    if quantity_match:
        result.quantidade = Decimal(quantity_match.group(1))

    if lines:
        result.descricao = lines[0][:500]

    found = []
    for attr in (
        "data", "valor", "fornecedor", "razao_social", "cnpj", "cpf",
        "descricao", "numero_documento", "quantidade", "forma_pagamento",
    ):
        if getattr(result, attr) is not None:
            found.append(attr)
    result.fields_found = found

    return result
