from __future__ import annotations

import asyncio
import hashlib
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.core.errors import ApiError
from app.models.generated_document import GeneratedDocument
from app.models.latex_template import LatexTemplate
from app.models.user import User
from app.services.storage import delete_file, storage_path, write_atomic


def _safe_name_part(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-._")
    return slug[:80] or "document"


def build_download_name(template_name: str, generated_at: datetime) -> str:
    return f"{_safe_name_part(template_name)}-{generated_at:%Y%m%d-%H%M%S}.pdf"


async def save_document(
    db: AsyncSession,
    *,
    template: LatexTemplate,
    uploader: User,
    values: dict[str, object],
    pdf: bytes,
    settings: Settings,
) -> GeneratedDocument:
    generated_at = datetime.now(UTC)
    storage_key = f"{uuid.uuid4()}.pdf"
    path = storage_path(settings.template_document_storage_dir, storage_key)
    await asyncio.to_thread(write_atomic, path, pdf)

    document = GeneratedDocument(
        template_id=template.id,
        template_name=template.name,
        generated_by_id=uploader.id,
        values=values,
        filename=build_download_name(template.name, generated_at),
        storage_key=storage_key,
        size_bytes=len(pdf),
        sha256=hashlib.sha256(pdf).hexdigest(),
        created_at=generated_at,
    )
    db.add(document)
    try:
        await db.commit()
    except BaseException:
        await db.rollback()
        await asyncio.to_thread(delete_file, path)
        raise

    await db.refresh(document)
    return document


async def list_documents(
    db: AsyncSession,
    *,
    limit: int,
    offset: int,
    template_id: uuid.UUID | None = None,
) -> list[tuple[GeneratedDocument, str | None]]:
    query = (
        select(GeneratedDocument, User.email)
        .outerjoin(User, GeneratedDocument.generated_by_id == User.id)
        .order_by(GeneratedDocument.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if template_id is not None:
        query = query.where(GeneratedDocument.template_id == template_id)
    rows = await db.execute(query)
    return [(document, email) for document, email in rows.all()]


async def get_document(db: AsyncSession, document_id: uuid.UUID) -> GeneratedDocument:
    document = await db.get(GeneratedDocument, document_id)
    if document is None:
        raise ApiError(404, "document_not_found", "Generated document not found")
    return document


def document_file_path(settings: Settings, document: GeneratedDocument) -> Path:
    path = storage_path(settings.template_document_storage_dir, document.storage_key)
    if not path.is_file():
        raise ApiError(404, "document_file_missing", "The generated PDF is missing from storage")
    return path
