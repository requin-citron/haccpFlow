from __future__ import annotations

import enum
import uuid

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, enum_values


class TemplateVariableKind(enum.StrEnum):
    STATIC = "static"
    LOCAL = "local"


class TemplateVariableValueType(enum.StrEnum):
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    PRODUCTS = "products"
    IMAGE = "image"


class TemplateVariableAsset(TimestampMixin, Base):
    """The single image attached to a static image variable."""

    __tablename__ = "template_variable_assets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    variable_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("template_variables.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    storage_key: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(32), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    uploaded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    variable: Mapped[TemplateVariable] = relationship(back_populates="asset")


class TemplateVariable(TimestampMixin, Base):
    """A variable declared on one template.

    Static variables carry a fixed value set by an administrator. Local
    variables are supplied (or defaulted) at generation time.
    """

    __tablename__ = "template_variables"
    __table_args__ = (
        UniqueConstraint("template_id", "name", name="uq_template_variables_template_name"),
        CheckConstraint(
            "kind <> 'static' OR value IS NOT NULL OR value_type::text = 'image'",
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
    asset: Mapped[TemplateVariableAsset | None] = relationship(
        back_populates="variable",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )
