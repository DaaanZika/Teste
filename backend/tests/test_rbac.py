from app.core.rbac import Permission, role_has_permission
from app.models.enums import Role


def test_admin_has_every_permission():
    for permission in Permission:
        assert role_has_permission(Role.ADMIN, permission)


def test_viewer_can_only_view():
    for permission in Permission:
        expected = permission.name.startswith("VIEW_")
        assert role_has_permission(Role.VIEWER, permission) is expected


def test_viewer_cannot_manage_finance_or_documents_or_users():
    assert not role_has_permission(Role.VIEWER, Permission.MANAGE_FINANCE)
    assert not role_has_permission(Role.VIEWER, Permission.MANAGE_DOCUMENTS)
    assert not role_has_permission(Role.VIEWER, Permission.MANAGE_USERS)
    assert not role_has_permission(Role.VIEWER, Permission.MANAGE_CAMPAIGNS)
    assert not role_has_permission(Role.VIEWER, Permission.MANAGE_RULES)


def test_financial_can_manage_finance_and_documents_but_not_users_or_campaigns():
    assert role_has_permission(Role.FINANCIAL, Permission.MANAGE_FINANCE)
    assert role_has_permission(Role.FINANCIAL, Permission.MANAGE_DOCUMENTS)
    assert not role_has_permission(Role.FINANCIAL, Permission.MANAGE_USERS)
    assert not role_has_permission(Role.FINANCIAL, Permission.MANAGE_CAMPAIGNS)
    assert not role_has_permission(Role.FINANCIAL, Permission.MANAGE_RULES)


def test_accountant_can_manage_documents_but_not_originate_finance_entries():
    assert role_has_permission(Role.ACCOUNTANT, Permission.MANAGE_DOCUMENTS)
    assert not role_has_permission(Role.ACCOUNTANT, Permission.MANAGE_FINANCE)


def test_campaign_manager_cannot_manage_users_or_rules():
    assert role_has_permission(Role.CAMPAIGN_MANAGER, Permission.MANAGE_FINANCE)
    assert role_has_permission(Role.CAMPAIGN_MANAGER, Permission.MANAGE_CAMPAIGNS)
    assert not role_has_permission(Role.CAMPAIGN_MANAGER, Permission.MANAGE_USERS)
    assert not role_has_permission(Role.CAMPAIGN_MANAGER, Permission.MANAGE_RULES)


def test_only_admin_manages_users_and_rules():
    for role in Role:
        if role is Role.ADMIN:
            continue
        assert not role_has_permission(role, Permission.MANAGE_USERS)
        assert not role_has_permission(role, Permission.MANAGE_RULES)
