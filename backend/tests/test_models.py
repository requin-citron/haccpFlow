from __future__ import annotations

from sqlalchemy import Enum as SAEnum

from app.models.user import User, UserRole


def test_user_role_persists_enum_values_not_member_names() -> None:
    """The database enum labels must match the member values ("admin")."""

    column_type = User.__table__.c.role.type

    assert isinstance(column_type, SAEnum)
    assert column_type.enums == ["admin", "operator"]
    assert [str(member.value) for member in UserRole] == ["admin", "operator"]


def test_user_email_is_unique_and_hashed_password_is_required() -> None:
    columns = User.__table__.c

    assert columns.email.unique is True
    assert columns.hashed_password.nullable is False
    assert columns.role.nullable is False
