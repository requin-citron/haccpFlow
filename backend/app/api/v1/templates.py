from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException

from app.api.deps import DbSession, SettingsDep, require_role
from app.core.errors import ApiError
from app.models.latex_template import LatexTemplate
from app.models.user import User, UserRole
from app.schemas.latex_template import LatexTemplateRead
from app.services.latex_template import (
    MULTIPART_OVERHEAD_BYTES,
    decode_template,
    download_filename,
    get_template,
    list_templates,
    normalize_name,
    read_upload,
    sanitize_filename,
    save_template,
    template_file_path,
    validate_extension,
)

router = APIRouter(prefix="/templates", tags=["templates"])

AdminUser = Annotated[User, Depends(require_role(UserRole.ADMIN))]

_UPLOAD_OPENAPI = {
    "requestBody": {
        "required": True,
        "content": {
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "required": ["file"],
                    "properties": {
                        "file": {"type": "string", "format": "binary"},
                        "name": {"type": "string", "maxLength": 120},
                    },
                }
            }
        },
    }
}


def _read(template: LatexTemplate, uploaded_by_email: str | None) -> LatexTemplateRead:
    return LatexTemplateRead(
        id=template.id,
        name=template.name,
        original_filename=template.original_filename,
        size_bytes=template.size_bytes,
        sha256=template.sha256,
        uploaded_by_email=uploaded_by_email,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.get("", response_model=list[LatexTemplateRead])
async def list_latex_templates(
    db: DbSession,
    _: AdminUser,
) -> list[LatexTemplateRead]:
    return [_read(template, email) for template, email in await list_templates(db)]


@router.post(
    "",
    response_model=LatexTemplateRead,
    status_code=201,
    openapi_extra=_UPLOAD_OPENAPI,
)
async def upload_latex_template(
    request: Request,
    db: DbSession,
    user: AdminUser,
    settings: SettingsDep,
) -> LatexTemplateRead:
    max_bytes = settings.template_max_upload_bytes
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            declared = int(content_length)
        except ValueError:
            declared = 0
        if declared > max_bytes + MULTIPART_OVERHEAD_BYTES:
            raise ApiError(
                413,
                "template_too_large",
                f"The file must be at most {max_bytes} bytes",
            )

    try:
        form = await request.form(
            max_files=1,
            max_fields=1,
            max_part_size=max_bytes + MULTIPART_OVERHEAD_BYTES,
        )
    except MultiPartException as exc:
        if "maximum size" in str(exc).lower():
            raise ApiError(
                413,
                "template_too_large",
                f"The file must be at most {max_bytes} bytes",
            ) from exc
        raise ApiError(
            422,
            "template_invalid_multipart",
            "Invalid multipart upload",
        ) from exc

    upload = form.get("file")
    if not isinstance(upload, UploadFile):
        raise ApiError(422, "template_file_required", "A .tex file is required")

    raw_name = form.get("name")
    if raw_name is not None and not isinstance(raw_name, str):
        raise ApiError(422, "template_name_invalid", "The template name is invalid")

    try:
        filename = sanitize_filename(upload.filename)
        validate_extension(filename)
        data = await read_upload(upload, max_bytes)
    finally:
        await upload.close()

    display_name = normalize_name(raw_name or "", filename)
    source = decode_template(data)
    template = await save_template(
        db,
        uploader=user,
        settings=settings,
        filename=filename,
        display_name=display_name,
        source=source,
    )
    return _read(template, user.email)


@router.get("/{template_id}/download")
async def download_latex_template(
    template_id: uuid.UUID,
    db: DbSession,
    _: AdminUser,
    settings: SettingsDep,
) -> FileResponse:
    template = await get_template(db, template_id)
    path = template_file_path(settings, template)
    return FileResponse(
        path,
        media_type="text/plain; charset=utf-8",
        filename=download_filename(template),
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
