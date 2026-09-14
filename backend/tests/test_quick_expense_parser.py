from datetime import date, timedelta
from decimal import Decimal

from app.services.finance.quick_expense_parser import parse_quick_expense


def test_currency_prefixed_amount_and_description():
    result = parse_quick_expense("R$ 850 gráfica ABC")
    assert result.valor == Decimal("850.00")
    assert "gráfica ABC" in (result.descricao or "")


def test_reais_suffix_amount_and_relative_date():
    result = parse_quick_expense("Gasolina 230 reais ontem")
    assert result.valor == Decimal("230.00")
    assert result.data == date.today() - timedelta(days=1)
    assert result.categoria == "Combustível"


def test_day_of_month_date_and_bare_amount():
    result = parse_quick_expense("Aluguel comitê 3500 dia 10")
    assert result.valor == Decimal("3500.00")
    assert result.data is not None and result.data.day == 10
    assert result.categoria == "Aluguel"


def test_bare_decimal_comma_amount():
    result = parse_quick_expense("Uber 86,40")
    assert result.valor == Decimal("86.40")
    assert result.categoria == "Transporte"


def test_amount_word_order_variations():
    for text in ("R$ 500 gasolina", "500 reais gasolina", "gasolina 500"):
        result = parse_quick_expense(text)
        assert result.valor == Decimal("500.00"), f"failed for: {text}"
        assert result.categoria == "Combustível"


def test_empty_text_returns_all_none():
    result = parse_quick_expense("")
    assert result.valor is None
    assert result.data is None
    assert result.descricao is None
    assert result.fields_found == []


def test_never_invents_a_supplier_when_nothing_left_over():
    result = parse_quick_expense("R$ 100")
    assert result.valor == Decimal("100.00")
    assert result.fornecedor is None
    assert result.descricao is None
