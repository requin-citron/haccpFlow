from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class GeneratedDocument(TimestampMixin, Base):
    """A PDF generated from a template, with the values used to render it."""

    __tablename__ = "generated_documents"
    __table_args__ = (Index("ix_generated_documents_created_at", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    #: SET NULL keeps the history readable if a template is ever removed; the
    #: template name is snapshotted below.
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("latex_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    template_name: Mapped[str] = mapped_column(String(120), nullable=False)
    generated_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    #: Resolved static and local values, as strings, for audit purposes.
    values: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
