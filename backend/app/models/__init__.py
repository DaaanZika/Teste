"""Import every model so `Base.metadata` is fully populated for Alembic and `create_all`."""
from app.models.audit import AuditLog
from app.models.campaign import Campaign
from app.models.category import Category
from app.models.compliance import ComplianceAlert, ComplianceRule
from app.models.document import Document, DocumentItem
from app.models.expense import Expense
from app.models.gmail_suggestion import GmailSuggestion
from app.models.integration_connection import IntegrationConnection
from app.models.organization import Organization
from app.models.processing_job import ProcessingJob
from app.models.revenue import Revenue
from app.models.session import Session
from app.models.supplier import Supplier
from app.models.transaction import Transaction
from app.models.user import User

__all__ = [
    "AuditLog",
    "Campaign",
    "Category",
    "ComplianceAlert",
    "ComplianceRule",
    "Document",
    "DocumentItem",
    "Expense",
    "GmailSuggestion",
    "IntegrationConnection",
    "Organization",
    "ProcessingJob",
    "Revenue",
    "Session",
    "Supplier",
    "Transaction",
    "User",
]
