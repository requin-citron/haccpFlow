from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.api.deps import require_role
from app.core.errors import ApiError
from app.models.user import UserRole


def _user(role: UserRole) -> SimpleNamespace:
    return SimpleNamespace(role=role)


def test_admin_role_is_allowed() -> None:
    dependency = require_role(UserRole.ADMIN)
    admin = _user(UserRole.ADMIN)

    assert dependency(admin) is admin


def test_operator_role_is_rejected() -> None:
    dependency = require_role(UserRole.ADMIN)

    with pytest.raises(ApiError) as excinfo:
        dependency(_user(UserRole.OPERATOR))

    assert excinfo.value.status_code == 403
    assert excinfo.value.code == "insufficient_role"


def test_several_roles_can_be_allowed() -> None:
    dependency = require_role(UserRole.ADMIN, UserRole.OPERATOR)

    assert dependency(_user(UserRole.OPERATOR)).role is UserRole.OPERATOR
