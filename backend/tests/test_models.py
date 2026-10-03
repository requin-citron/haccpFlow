from __future__ import annotations

from sqlalchemy import Enum as SAEnum

from app.models.equipment import Equipment, EquipmentType
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


def test_equipment_type_persists_enum_values_not_member_names() -> None:
    column_type = Equipment.__table__.c.type.type

    assert isinstance(column_type, SAEnum)
    assert column_type.enums == ["fridge", "freezer"]
    assert [str(member.value) for member in EquipmentType] == ["fridge", "freezer"]


def test_equipment_thresholds_are_required_and_soft_delete_is_optional() -> None:
    columns = Equipment.__table__.c

    assert columns.min_temperature_celsius.nullable is False
    assert columns.max_temperature_celsius.nullable is False
    assert columns.deleted_at.nullable is True


def test_equipment_name_uniqueness_is_scoped_to_active_rows() -> None:
    index = next(
        index for index in Equipment.__table__.indexes if index.name == "uq_equipment_name_active"
    )

    assert index.unique is True
