"""Cross-organization isolation (PROMPT 4's explicit, non-negotiable rule):
a user in Org A must never see, edit, or delete Org B's data, and this
must be enforced in the backend, never assumed from frontend filtering.
Every test here creates two REAL, separate organizations and proves one
cannot reach the other's data — not "code review says it can't."
"""
from __future__ import annotations

import uuid

import pytest

from app.api.deps import get_current_user
from app.main import app as fastapi_app
from app.models.campaign import Campaign
from app.models.enums import Role
from app.models.organization import Organization
from app.models.user import User


@pytest.fixture()
def two_orgs(db_session):
    """Org A (with a campaign) and Org B (with its own OWNER), fully
    independent tenants."""
    unique = uuid.uuid4().hex[:8]
    org_a = Organization(name=f"Org A {unique}", slug=f"org-a-{unique}")
    org_b = Organization(name=f"Org B {unique}", slug=f"org-b-{unique}")
    db_session.add_all([org_a, org_b])
    db_session.flush()

    campaign_a = Campaign(name="Campanha A", organization_id=org_a.id)
    db_session.add(campaign_a)

    owner_a = User(
        name="Owner A", email=f"owner-a-{unique}@example.com", role=Role.OWNER, active=True, organization_id=org_a.id
    )
    owner_b = User(
        name="Owner B", email=f"owner-b-{unique}@example.com", role=Role.OWNER, active=True, organization_id=org_b.id
    )
    db_session.add_all([owner_a, owner_b])
    db_session.commit()
    for obj in (org_a, org_b, campaign_a, owner_a, owner_b):
        db_session.refresh(obj)
    return org_a, org_b, campaign_a, owner_a, owner_b


def _act_as(user: User) -> None:
    fastapi_app.dependency_overrides[get_current_user] = lambda: user


@pytest.fixture(autouse=True)
def _cleanup_override():
    yield
    fastapi_app.dependency_overrides.pop(get_current_user, None)


def test_user_b_cannot_list_org_a_campaign(client, two_orgs):
    org_a, org_b, campaign_a, owner_a, owner_b = two_orgs
    _act_as(owner_b)
    response = client.get("/campaigns")
    assert response.status_code == 200
    assert all(c["id"] != campaign_a.id for c in response.json())


def test_user_b_cannot_get_org_a_campaign_by_id(client, two_orgs):
    org_a, org_b, campaign_a, owner_a, owner_b = two_orgs
    _act_as(owner_b)
    response = client.get(f"/campaigns/{campaign_a.id}")
    assert response.status_code == 404


def test_user_b_cannot_update_org_a_campaign(client, two_orgs):
    org_a, org_b, campaign_a, owner_a, owner_b = two_orgs
    _act_as(owner_b)
    response = client.put(f"/campaigns/{campaign_a.id}", json={"name": "Hijacked"})
    assert response.status_code == 404


def test_created_campaign_is_forced_into_callers_own_org_not_client_supplied(client, two_orgs):
    org_a, org_b, campaign_a, owner_a, owner_b = two_orgs
    _act_as(owner_b)
    response = client.post("/campaigns", json={"name": "Nova Campanha B"})
    assert response.status_code == 200
    created_id = response.json()["id"]

    # Owner A must never see it.
    _act_as(owner_a)
    listing = client.get("/campaigns")
    assert all(c["id"] != created_id for c in listing.json())


def test_user_b_cannot_see_org_a_users(client, two_orgs):
    org_a, org_b, campaign_a, owner_a, owner_b = two_orgs
    _act_as(owner_b)
    response = client.get("/users")
    assert response.status_code == 200
    assert all(u["id"] != owner_a.id for u in response.json())


def test_user_b_cannot_edit_org_a_user(client, two_orgs):
    org_a, org_b, campaign_a, owner_a, owner_b = two_orgs
    _act_as(owner_b)
    response = client.patch(f"/users/{owner_a.id}", json={"active": False})
    assert response.status_code == 404


def test_created_user_lands_in_callers_own_org_never_a_client_supplied_one(client, two_orgs, db_session):
    org_a, org_b, campaign_a, owner_a, owner_b = two_orgs
    _act_as(owner_b)
    response = client.post(
        "/users",
        json={
            "name": "Nova Pessoa",
            "email": f"nova-{uuid.uuid4().hex[:8]}@example.com",
            "password": "SenhaForte123!",
            "role": "VISUALIZADOR",
            # Attempting to smuggle a different org id — must be ignored.
            "organization_id": org_a.id,
        },
    )
    assert response.status_code == 200
    created = db_session.get(User, response.json()["id"])
    assert created.organization_id == org_b.id


def test_user_a_cannot_create_super_admin(client, two_orgs):
    org_a, org_b, campaign_a, owner_a, owner_b = two_orgs
    _act_as(owner_a)
    response = client.post(
        "/users",
        json={
            "name": "Tentativa",
            "email": f"escalate-{uuid.uuid4().hex[:8]}@example.com",
            "password": "SenhaForte123!",
            "role": "SUPER_ADMIN",
        },
    )
    assert response.status_code == 403


def test_org_a_owner_cannot_reach_admin_area(client, two_orgs):
    org_a, org_b, campaign_a, owner_a, owner_b = two_orgs
    _act_as(owner_a)
    response = client.get("/admin/metrics")
    assert response.status_code == 403
    response = client.get("/admin/organizations")
    assert response.status_code == 403


def test_own_organization_endpoint_only_ever_returns_callers_own_org(client, two_orgs):
    org_a, org_b, campaign_a, owner_a, owner_b = two_orgs
    _act_as(owner_a)
    response = client.get("/organization")
    assert response.status_code == 200
    assert response.json()["id"] == org_a.id

    _act_as(owner_b)
    response = client.get("/organization")
    assert response.json()["id"] == org_b.id


def test_super_admin_without_organization_gets_403_on_regular_org_routes(client, db_session):
    unique = uuid.uuid4().hex[:8]
    super_admin = User(
        name="Platform Admin", email=f"su-{unique}@example.com", role=Role.SUPER_ADMIN, active=True
    )
    db_session.add(super_admin)
    db_session.commit()
    db_session.refresh(super_admin)

    _act_as(super_admin)
    response = client.get("/campaigns")
    assert response.status_code == 403
    response = client.get("/organization")
    assert response.status_code == 403


# --- Documents/expenses/revenues/finance/reports/compliance/audit --------
# The spec's own explicit examples: User A reaching Org B's document,
# editing Org B's expense, and so on. Each test below creates the target
# resource for real in Org A, then proves Org B's user cannot reach it.


@pytest.fixture()
def expense_in_org_a(db_session, two_orgs):
    from app.models.enums import ExpenseStatus
    from app.models.expense import Expense

    org_a, org_b, campaign_a, owner_a, owner_b = two_orgs
    expense = Expense(campaign_id=campaign_a.id, description="Despesa A", status=ExpenseStatus.PENDING_INFORMATION)
    db_session.add(expense)
    db_session.commit()
    db_session.refresh(expense)
    return expense


@pytest.fixture()
def revenue_in_org_a(db_session, two_orgs):
    from app.models.enums import RevenueStatus
    from app.models.revenue import Revenue

    org_a, org_b, campaign_a, owner_a, owner_b = two_orgs
    revenue = Revenue(campaign_id=campaign_a.id, source_type="doacao", status=RevenueStatus.PENDING_INFORMATION)
    db_session.add(revenue)
    db_session.commit()
    db_session.refresh(revenue)
    return revenue


@pytest.fixture()
def document_in_org_a(db_session, two_orgs):
    from app.models.document import Document

    org_a, org_b, campaign_a, owner_a, owner_b = two_orgs
    document = Document(
        campaign_id=campaign_a.id,
        original_filename="nota.pdf",
        mime_type="application/pdf",
        file_extension="pdf",
        file_size_bytes=10,
        sha256_hash=uuid.uuid4().hex,
        original_path="originals/nota.pdf",
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)
    return document


def test_user_b_cannot_view_org_a_document(client, two_orgs, document_in_org_a):
    _, _, _, _, owner_b = two_orgs
    _act_as(owner_b)
    response = client.get(f"/documents/{document_in_org_a.id}")
    assert response.status_code == 404


def test_user_b_cannot_list_org_a_document(client, two_orgs, document_in_org_a):
    _, _, _, _, owner_b = two_orgs
    _act_as(owner_b)
    response = client.get("/documents")
    assert response.status_code == 200
    assert all(d["id"] != document_in_org_a.id for d in response.json())


def test_user_b_cannot_view_org_a_expense(client, two_orgs, expense_in_org_a):
    _, _, _, _, owner_b = two_orgs
    _act_as(owner_b)
    response = client.get(f"/expenses/{expense_in_org_a.id}")
    assert response.status_code == 404


def test_user_b_cannot_edit_org_a_expense(client, two_orgs, expense_in_org_a):
    _, _, _, _, owner_b = two_orgs
    _act_as(owner_b)
    response = client.put(f"/expenses/{expense_in_org_a.id}", json={"description": "Hijacked"})
    assert response.status_code == 404


def test_user_b_cannot_view_org_a_revenue(client, two_orgs, revenue_in_org_a):
    _, _, _, _, owner_b = two_orgs
    _act_as(owner_b)
    response = client.get(f"/revenues/{revenue_in_org_a.id}")
    assert response.status_code == 404


def test_org_a_expense_invisible_in_org_b_listing(client, two_orgs, expense_in_org_a):
    _, _, _, _, owner_b = two_orgs
    _act_as(owner_b)
    response = client.get("/expenses")
    assert response.status_code == 200
    assert all(e["id"] != expense_in_org_a.id for e in response.json())


def test_created_expense_lands_in_callers_own_campaign_not_client_supplied(client, two_orgs, db_session):
    """Even if the payload names a campaign_id belonging to Org A, Org B's
    caller must never be able to attach an expense to it."""
    org_a, org_b, campaign_a, owner_a, owner_b = two_orgs
    _act_as(owner_b)
    response = client.post("/expenses", json={"campaign_id": campaign_a.id, "description": "Tentativa"})
    assert response.status_code == 404


def test_finance_summary_never_aggregates_across_organizations(client, two_orgs, expense_in_org_a, db_session):
    from decimal import Decimal

    org_a, org_b, campaign_a, owner_a, owner_b = two_orgs
    expense_in_org_a.amount = Decimal("1000.00")
    db_session.commit()

    from app.services.finance.ledger import sync_transaction_for_expense

    sync_transaction_for_expense(db_session, expense_in_org_a)
    db_session.commit()

    _act_as(owner_b)
    response = client.get("/finance/summary")
    assert response.status_code == 200
    assert float(response.json()["total_expenses"]) == 0.0


def test_reports_never_leak_org_a_expenses_to_org_b(client, two_orgs, expense_in_org_a):
    _, _, _, _, owner_b = two_orgs
    _act_as(owner_b)
    response = client.get("/reports/expenses")
    assert response.status_code == 200
    assert all(row["id"] != expense_in_org_a.id for row in response.json())


def test_audit_entity_lookup_across_orgs_404s(client, two_orgs, expense_in_org_a):
    _, _, _, _, owner_b = two_orgs
    _act_as(owner_b)
    response = client.get("/audit", params={"entity": "expense", "entity_id": expense_in_org_a.id})
    assert response.status_code == 404


def test_compliance_alerts_scoped_to_own_org(client, two_orgs, db_session):
    from app.models.compliance import ComplianceAlert
    from app.models.enums import AlertType

    org_a, org_b, campaign_a, owner_a, owner_b = two_orgs
    alert = ComplianceAlert(
        campaign_id=campaign_a.id, type=AlertType.WARNING, title="Alerta A", message="msg"
    )
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)

    _act_as(owner_b)
    response = client.get("/compliance/alerts")
    assert response.status_code == 200
    assert all(a["id"] != alert.id for a in response.json())
