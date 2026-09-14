from datetime import date
from decimal import Decimal

from app.services.ocr.confidence import score_confidence
from app.services.ocr.extractor import extract_fields
from app.models.enums import OCRConfidence


def test_extract_fields_finds_known_values():
    text = """
    MERCADO CENTRAL LTDA
    CNPJ: 12.345.678/0001-90
    Data: 05/03/2024
    Total: R$ 123,45
    Forma de pagamento: PIX
    Numero: 000123
    """
    fields = extract_fields(text)

    assert fields.data == date(2024, 3, 5)
    assert fields.valor == Decimal("123.45")
    assert fields.cnpj == "12345678000190"
    assert fields.forma_pagamento == "PIX"
    assert fields.numero_documento == "000123"


def test_extract_fields_never_invents_missing_data():
    fields = extract_fields("texto sem nenhum campo reconhecivel")
    assert fields.valor is None
    assert fields.data is None
    assert fields.cnpj is None
    assert fields.cpf is None


def test_extract_fields_empty_text_returns_all_none():
    fields = extract_fields("")
    assert fields.valor is None
    assert fields.data is None
    assert fields.fornecedor is None
    assert fields.fields_found == []


def test_extract_fields_cpf_not_confused_with_cnpj():
    text = "Comprador CPF: 123.456.789-09"
    fields = extract_fields(text)
    assert fields.cpf == "12345678909"
    assert fields.cnpj is None


def test_confidence_high_requires_critical_fields_and_multiple_matches():
    fields = extract_fields(
        "LOJA XYZ\nCNPJ 11.222.333/0001-44\nData 01/01/2024\nTotal R$ 50,00\nForma PIX"
    )
    confidence = score_confidence(engine_available=True, mean_ocr_confidence=90.0, extracted=fields)
    assert confidence == OCRConfidence.HIGH


def test_confidence_low_when_no_fields_found():
    fields = extract_fields("xxxxx yyyyy zzzzz")
    confidence = score_confidence(engine_available=True, mean_ocr_confidence=20.0, extracted=fields)
    assert confidence == OCRConfidence.LOW


def test_confidence_none_when_engine_unavailable():
    fields = extract_fields("qualquer coisa")
    confidence = score_confidence(engine_available=False, mean_ocr_confidence=None, extracted=fields)
    assert confidence == OCRConfidence.NONE
