from __future__ import annotations

import enum
import uuid

from sqlalchemy import CheckConstraint, Enum, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, enum_values


class TemplateVariableKind(enum.StrEnum):
    STATIC = "static"
    LOCAL = "local"


class TemplateVariableValueType(enum.StrEnum):
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    PRODUCTS = "products"


class TemplateVariable(TimestampMixin, Base):
    """A variable declared on one template.

    Static variables carry a fixed value set by an administrator. Local
    variables are supplied (or defaulted) at generation time.
    """

    __tablename__ = "template_variables"
    __table_args__ = (
        UniqueConstraint("template_id", "name", name="uq_template_variables_template_name"),
        CheckConstraint(
            "kind <> 'static' OR value IS NOT NULL",
            name="ck_template_variables_static_value",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("latex_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    kind: Mapped[TemplateVariableKind] = mapped_column(
        Enum(
            TemplateVariableKind,
            name="template_variable_kind",
            native_enum=True,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    value_type: Mapped[TemplateVariableValueType] = mapped_column(
        Enum(
            TemplateVariableValueType,
            name="template_variable_value_type",
            native_enum=True,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    #: Static value, or default value for a local variable. Null means the
    #: local variable is required at generation time.
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
