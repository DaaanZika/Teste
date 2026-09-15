from app.core.rbac import Permission, role_has_permission, user_has_permission
from app.models.enums import Role


def test_admin_has_every_permission_except_platform_manage():
    # platform.manage is exclusive to SUPER_ADMIN (PROMPT 4) — ADMIN (an
    # organization-scoped role) gets everything else, same as before.
    for permission in Permission:
        expected = permission is not Permission.PLATFORM_MANAGE
        assert role_has_permission(Role.ADMIN, permission) is expected


def test_owner_has_every_permission_except_platform_manage():
    # OWNER (PROMPT 4) is the multi-tenant equivalent of ADMIN — same ceiling.
    for permission in Permission:
        expected = permission is not Permission.PLATFORM_MANAGE
        assert role_has_permission(Role.OWNER, permission) is expected


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


def test_only_admin_and_owner_manage_users_and_rules():
    # ADMIN (single-org, PROMPT 3) and OWNER (multi-tenant equivalent,
    # PROMPT 4) are the only roles with a fixed permission set that manages
    # users/rules — CUSTOM is deliberately excluded here: its capabilities
    # come from per-user grants, not the role-only check this test uses.
    for role in Role:
        if role in (Role.ADMIN, Role.OWNER, Role.CUSTOM):
            continue
        assert not role_has_permission(role, Permission.MANAGE_USERS)
        assert not role_has_permission(role, Permission.MANAGE_RULES)


def test_super_admin_bypasses_the_permission_matrix_entirely():
    """SUPER_ADMIN is not "a role with every permission" — it is
    structurally outside ROLE_PERMISSIONS (role_has_permission knows
    nothing about it), and only `user_has_permission` (used by every real
    route dependency) grants it everything, unconditionally."""

    class _FakeSuperAdmin:
        role = Role.SUPER_ADMIN
        id = "fake-super-admin"

    assert role_has_permission(Role.SUPER_ADMIN, Permission.MANAGE_USERS) is False
    for permission in Permission:
        assert user_has_permission(db=None, user=_FakeSuperAdmin(), permission=permission) is True


def test_custom_role_uses_per_user_grants_not_a_fixed_set():
    """CUSTOM has no view-beyond-view capability from its role alone — a
    granted permission must come from the user_permissions table, checked
    through user_has_permission (never role_has_permission, which cannot
    see per-user state)."""
    from app.models.user_permission import UserPermission

    class _FakeQuery:
        def __init__(self, granted: bool):
            self._granted = granted

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return object() if self._granted else None

    class _FakeDb:
        def __init__(self, granted: bool):
            self._granted = granted

        def query(self, model):
            assert model is UserPermission
            return _FakeQuery(self._granted)

    class _FakeCustomUser:
        role = Role.CUSTOM
        id = "fake-custom-user"

    assert not role_has_permission(Role.CUSTOM, Permission.MANAGE_FINANCE)
    assert user_has_permission(db=_FakeDb(granted=False), user=_FakeCustomUser(), permission=Permission.MANAGE_FINANCE) is False
    assert user_has_permission(db=_FakeDb(granted=True), user=_FakeCustomUser(), permission=Permission.MANAGE_FINANCE) is True
    # The view-only baseline never needs the per-user table.
    assert user_has_permission(db=_FakeDb(granted=False), user=_FakeCustomUser(), permission=Permission.VIEW_FINANCE) is True
