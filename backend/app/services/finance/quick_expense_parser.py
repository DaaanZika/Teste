"""Parses free-text quick expense entries like:

    "R$ 850 gráfica ABC"
    "Gasolina 230 reais ontem"
    "Aluguel comitê 3500 dia 10"
    "Uber 86,40"

Only fields actually present in the text are returned; nothing is
invented. `category` is a best-effort keyword match against common
campaign expense types and is left `None` when nothing matches — it is a
convenience, not an authoritative classification.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.utils.text import parse_date, parse_money

_DATE_SPAN_PATTERNS = (
    re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"),
    re.compile(r"\b\d{4}-\d{1,2}-\d{1,2}\b"),
    re.compile(r"\bdia\s+\d{1,2}\b", re.IGNORECASE),
    re.compile(r"\bhoje\b", re.IGNORECASE),
    re.compile(r"\bontem\b", re.IGNORECASE),
    re.compile(r"\banteontem\b", re.IGNORECASE),
)

_MONEY_SPAN_PATTERNS = (
    re.compile(r"R\$\s*\d{1,3}(?:\.\d{3})*(?:,\d{2})?", re.IGNORECASE),
    re.compile(r"\d{1,3}(?:\.\d{3})*(?:,\d{2})?\s*reais", re.IGNORECASE),
)

_BARE_NUMBER_RE = re.compile(r"\b\d+(?:[.,]\d{1,2})?\b")

_CATEGORY_KEYWORDS: dict[str, str] = {
    "gasolina": "Combustível",
    "combustivel": "Combustível",
    "combustível": "Combustível",
    "etanol": "Combustível",
    "diesel": "Combustível",
    "uber": "Transporte",
    "taxi": "Transporte",
    "táxi": "Transporte",
    "99": "Transporte",
    "passagem": "Transporte",
    "grafica": "Material Gráfico",
    "gráfica": "Material Gráfico",
    "impressao": "Material Gráfico",
    "impressão": "Material Gráfico",
    "panfleto": "Material Gráfico",
    "santinho": "Material Gráfico",
    "aluguel": "Aluguel",
    "comite": "Aluguel",
    "comitê": "Aluguel",
    "sede": "Aluguel",
    "alimentacao": "Alimentação",
    "alimentação": "Alimentação",
    "lanche": "Alimentação",
    "almoco": "Alimentação",
    "almoço": "Alimentação",
    "cartorio": "Cartório",
    "cartório": "Cartório",
    "internet": "Serviços",
    "telefone": "Serviços",
}


@dataclass
class QuickExpenseFields:
    descricao: str | None = None
    valor: Decimal | None = None
    data: date | None = None
    fornecedor: str | None = None
    categoria: str | None = None
    fields_found: list[str] | None = None


def _strip_first_match(text: str, patterns: tuple[re.Pattern, ...]) -> tuple[str, bool]:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return (text[: match.start()] + " " + text[match.end() :]).strip(), True
    return text, False


def parse_quick_expense(text: str) -> QuickExpenseFields:
    result = QuickExpenseFields()
    if not text or not text.strip():
        result.fields_found = []
        return result

    remaining = text.strip()

    result.data = parse_date(remaining)
    remaining, _ = _strip_first_match(remaining, _DATE_SPAN_PATTERNS)

    result.valor = parse_money(remaining)
    remaining_after_money, money_stripped = _strip_first_match(remaining, _MONEY_SPAN_PATTERNS)
    if money_stripped:
        remaining = remaining_after_money
    elif result.valor is None:
        bare_match = _BARE_NUMBER_RE.search(remaining)
        if bare_match:
            raw = bare_match.group(0).replace(".", "").replace(",", ".")
            try:
                result.valor = Decimal(raw).quantize(Decimal("0.01"))
                remaining = (remaining[: bare_match.start()] + " " + remaining[bare_match.end() :]).strip()
            except Exception:
                pass

    remaining = re.sub(r"\s+", " ", remaining).strip(" ,.-")

    lowered_original = text.lower()
    for keyword, category in _CATEGORY_KEYWORDS.items():
        if re.search(rf"\b{re.escape(keyword)}\b", lowered_original):
            result.categoria = category
            break

    if remaining:
        result.descricao = remaining
        result.fornecedor = remaining

    found = []
    for attr in ("descricao", "valor", "data", "fornecedor", "categoria"):
        if getattr(result, attr) is not None:
            found.append(attr)
    result.fields_found = found

    return result
