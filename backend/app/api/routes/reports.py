from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.core.exceptions import ValidationFailedError
from app.core.rbac import Permission
from app.services.reports import report_service
from app.services.reports.export_service import EXPORTERS, Column

router = APIRouter(prefix="/reports", tags=["reports"], dependencies=[Depends(require_permission(Permission.VIEW_REPORTS))])


@router.get("/summary")
def reports_summary(campaign_id: str | None = None, db: Session = Depends(get_db)) -> dict:
    return report_service.summary_report(db, campaign_id=campaign_id)


@router.get("/expenses")
def reports_expenses(campaign_id: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    return report_service.expenses_report(db, campaign_id=campaign_id)


@router.get("/revenues")
def reports_revenues(campaign_id: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    return report_service.revenues_report(db, campaign_id=campaign_id)


@router.get("/documents")
def reports_documents(campaign_id: str | None = None, db: Session = Depends(get_db)) -> dict:
    return report_service.documents_report(db, campaign_id=campaign_id)


# --- Export (PROMPT 3 FASE J) --------------------------------------------
#
# Every exported file is a "RELATÓRIO AUXILIAR" — the disclaimer is baked
# into the file itself (export_service.DISCLAIMER), not just shown in the
# UI, so it survives the file being downloaded or forwarded. None of this
# claims to be, or follow the layout of, an official TSE/CONTA+JE filing.

_EXPENSE_COLUMNS: list[Column] = [
    ("date", "Data"),
    ("supplier_name", "Fornecedor"),
    ("amount", "Valor (R$)"),
    ("category", "Categoria"),
    ("status", "Status"),
    ("document_status", "Documento"),
]

_REVENUE_COLUMNS: list[Column] = [
    ("date", "Data"),
    ("source_type", "Origem"),
    ("amount", "Valor (R$)"),
    ("status", "Status"),
    ("document_status", "Documento"),
]

_SUMMARY_LABELS = {
    "total_revenues": "Total de receitas (R$)",
    "total_expenses": "Total de despesas (R$)",
    "balance": "Saldo (R$)",
    "pending_information_expenses": "Despesas com informação pendente",
    "pending_information_revenues": "Receitas com informação pendente",
}

_DOCUMENTS_LABELS = {
    "total": "Total de documentos",
    "processed": "Processados",
    "pending": "Pendentes",
    "human_review": "Aguardando revisão humana",
    "duplicated": "Possível duplicidade",
    "failed": "Falharam no processamento",
}

_KV_COLUMNS: list[Column] = [("field", "Campo"), ("value", "Valor")]


def _as_kv_rows(data: dict, labels: dict[str, str]) -> list[dict]:
    return [{"field": labels.get(key, key), "value": value} for key, value in data.items()]


def _export_response(export_format: str, rows: list[dict], *, columns: list[Column], title: str, filename: str) -> Response:
    if export_format not in EXPORTERS:
        raise ValidationFailedError(f"Formato '{export_format}' não suportado. Use csv, xlsx ou pdf.")
    exporter, media_type, extension = EXPORTERS[export_format]
    content = exporter(rows, columns=columns, title=title)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}.{extension}"'},
    )


@router.get("/summary/export")
def export_summary(format: str = "csv", campaign_id: str | None = None, db: Session = Depends(get_db)) -> Response:
    data = report_service.summary_report(db, campaign_id=campaign_id)
    rows = _as_kv_rows(data, _SUMMARY_LABELS)
    return _export_response(format, rows, columns=_KV_COLUMNS, title="Resumo Financeiro (Relatório Auxiliar)", filename="resumo")


@router.get("/expenses/export")
def export_expenses(format: str = "csv", campaign_id: str | None = None, db: Session = Depends(get_db)) -> Response:
    rows = report_service.expenses_report(db, campaign_id=campaign_id)
    return _export_response(
        format, rows, columns=_EXPENSE_COLUMNS, title="Despesas (Relatório Auxiliar)", filename="despesas"
    )


@router.get("/revenues/export")
def export_revenues(format: str = "csv", campaign_id: str | None = None, db: Session = Depends(get_db)) -> Response:
    rows = report_service.revenues_report(db, campaign_id=campaign_id)
    return _export_response(
        format, rows, columns=_REVENUE_COLUMNS, title="Receitas (Relatório Auxiliar)", filename="receitas"
    )


@router.get("/documents/export")
def export_documents(format: str = "csv", campaign_id: str | None = None, db: Session = Depends(get_db)) -> Response:
    data = report_service.documents_report(db, campaign_id=campaign_id)
    rows = _as_kv_rows(data, _DOCUMENTS_LABELS)
    return _export_response(
        format, rows, columns=_KV_COLUMNS, title="Documentos (Relatório Auxiliar)", filename="documentos"
    )
