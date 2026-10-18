from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse

from app.api.deps import DbSession, SettingsDep, require_role
from app.models.generated_document import GeneratedDocument
from app.models.user import User, UserRole
from app.schemas.generated_document import GeneratedDocumentRead
from app.services.documents import document_file_path, get_document, list_documents

router = APIRouter(prefix="/documents", tags=["documents"])

AnyUser = Annotated[User, Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR))]


def _read(document: GeneratedDocument, generated_by_email: str | None) -> GeneratedDocumentRead:
    return GeneratedDocumentRead(
        id=document.id,
        template_id=document.template_id,
        template_name=document.template_name,
        generated_by_email=generated_by_email,
        values=document.values,
        filename=document.filename,
        size_bytes=document.size_bytes,
        sha256=document.sha256,
        created_at=document.created_at,
    )


@router.get("", response_model=list[GeneratedDocumentRead])
async def list_generated_documents(
    db: DbSession,
    _: AnyUser,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    template_id: uuid.UUID | None = Query(default=None),
) -> list[GeneratedDocumentRead]:
    rows = await list_documents(db, limit=limit, offset=offset, template_id=template_id)
    return [_read(document, email) for document, email in rows]


@router.get("/{document_id}/download")
async def download_generated_document(
    document_id: uuid.UUID,
    db: DbSession,
    _: AnyUser,
    settings: SettingsDep,
) -> FileResponse:
    document = await get_document(db, document_id)
    path = document_file_path(settings, document)
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=document.filename,
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
