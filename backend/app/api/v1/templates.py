from __future__ import annotations

import asyncio
import hashlib
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, PlainTextResponse
from starlette.datastructures import FormData, UploadFile
from starlette.formparsers import MultiPartException

from app.api.deps import DbSession, SettingsDep, require_role
from app.config import Settings
from app.core.errors import ApiError
from app.models.generated_document import GeneratedDocument
from app.models.latex_template import LatexTemplate
from app.models.template_variable import TemplateVariable
from app.models.user import User, UserRole
from app.schemas.generated_document import GeneratedDocumentRead, GenerateTemplateRequest
from app.schemas.latex_template import LatexTemplateRead, LatexTemplateRename
from app.schemas.template_variable import (
    TemplateVariableImageRead,
    TemplateVariableRead,
    TemplateVariableWrite,
)
from app.services.documents import save_document
from app.services.latex_template import (
    MULTIPART_OVERHEAD_BYTES,
    decode_template,
    download_filename,
    get_template,
    list_templates,
    normalize_name,
    read_upload,
    rename_template,
    sanitize_filename,
    save_template,
    template_file_path,
    validate_extension,
)
from app.services.pdf_generator import compile_pdf
from app.services.storage import delete_file, storage_path, write_atomic
from app.services.template_render import (
    collect_assets,
    render_source,
    used_variable_names,
)
from app.services.template_variables import (
    create_variable,
    delete_variable,
    delete_variable_asset,
    get_variable,
    image_asset_path,
    list_variables,
    read_image_upload,
    sanitize_image_filename,
    save_variable_image,
    serialize_variable_value,
    update_variable,
)

router = APIRouter(prefix="/templates", tags=["templates"])

AdminUser = Annotated[User, Depends(require_role(UserRole.ADMIN))]
AnyUser = Annotated[User, Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR))]

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


async def _source(template: LatexTemplate, settings: Settings) -> str:
    path = template_file_path(settings, template)
    return await asyncio.to_thread(path.read_text, encoding="utf-8")


def _variable_read(
    variable: TemplateVariable,
    used: set[str],
) -> TemplateVariableRead:
    image = (
        TemplateVariableImageRead(
            filename=variable.asset.original_filename,
            content_type=variable.asset.content_type,
            size_bytes=variable.asset.size_bytes,
            sha256=variable.asset.sha256,
            updated_at=variable.asset.updated_at,
        )
        if variable.asset is not None
        else None
    )
    return TemplateVariableRead(
        id=variable.id,
        template_id=variable.template_id,
        name=variable.name,
        label=variable.label,
        description=variable.description,
        kind=variable.kind,
        value_type=variable.value_type,
        value=serialize_variable_value(variable),
        image=image,
        used_in_template=variable.name in used,
        created_at=variable.created_at,
        updated_at=variable.updated_at,
    )


def _document_read(
    document: GeneratedDocument,
    generated_by_email: str | None,
) -> GeneratedDocumentRead:
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


async def _tex_form(request: Request, settings: Settings) -> tuple[FormData, UploadFile]:
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
    return form, upload


async def _read_tex(upload: UploadFile, settings: Settings) -> tuple[str, str]:
    try:
        filename = sanitize_filename(upload.filename)
        validate_extension(filename)
        data = await read_upload(upload, settings.template_max_upload_bytes)
    finally:
        await upload.close()
    return filename, decode_template(data)


async def _image_form(request: Request, settings: Settings) -> UploadFile:
    max_bytes = settings.template_image_max_upload_bytes
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            declared = int(content_length)
        except ValueError:
            declared = 0
        if declared > max_bytes + MULTIPART_OVERHEAD_BYTES:
            raise ApiError(
                413,
                "template_image_too_large",
                f"The image must be at most {max_bytes} bytes",
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
                "template_image_too_large",
                f"The image must be at most {max_bytes} bytes",
            ) from exc
        raise ApiError(
            422,
            "template_invalid_multipart",
            "Invalid multipart upload",
        ) from exc

    upload = form.get("file")
    if not isinstance(upload, UploadFile):
        raise ApiError(422, "template_file_required", "An image file is required")
    return upload


@router.get("", response_model=list[LatexTemplateRead])
async def list_latex_templates(
    db: DbSession,
    _: AnyUser,
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
    form, upload = await _tex_form(request, settings)
    raw_name = form.get("name")
    if raw_name is not None and not isinstance(raw_name, str):
        raise ApiError(422, "template_name_invalid", "The template name is invalid")

    filename, source = await _read_tex(upload, settings)
    display_name = normalize_name(raw_name or "", filename)
    template = await save_template(
        db,
        uploader=user,
        settings=settings,
        filename=filename,
        display_name=display_name,
        source=source,
    )
    return _read(template, user.email)


@router.put("/{template_id}", response_model=LatexTemplateRead)
async def replace_latex_template(
    template_id: uuid.UUID,
    request: Request,
    db: DbSession,
    _: AdminUser,
    settings: SettingsDep,
) -> LatexTemplateRead:
    template = await get_template(db, template_id)
    _form, upload = await _tex_form(request, settings)
    filename, source = await _read_tex(upload, settings)

    path = storage_path(settings.template_storage_dir, template.storage_key)
    old_data = await asyncio.to_thread(path.read_bytes) if path.is_file() else None
    new_data = source.encode("utf-8")
    await asyncio.to_thread(write_atomic, path, new_data)

    template.original_filename = filename
    template.size_bytes = len(new_data)
    template.sha256 = hashlib.sha256(new_data).hexdigest()
    try:
        await db.commit()
    except BaseException:
        await db.rollback()
        if old_data is None:
            await asyncio.to_thread(delete_file, path)
        else:
            await asyncio.to_thread(write_atomic, path, old_data)
        raise

    await db.refresh(template)
    uploader = await db.get(User, template.uploaded_by_id) if template.uploaded_by_id else None
    return _read(template, uploader.email if uploader else None)


@router.patch("/{template_id}", response_model=LatexTemplateRead)
async def rename_latex_template(
    template_id: uuid.UUID,
    payload: LatexTemplateRename,
    db: DbSession,
    _: AdminUser,
) -> LatexTemplateRead:
    template = await get_template(db, template_id)
    renamed = await rename_template(db, template, payload.name)
    uploader = await db.get(User, renamed.uploaded_by_id) if renamed.uploaded_by_id else None
    return _read(renamed, uploader.email if uploader else None)


@router.get("/{template_id}/variables", response_model=list[TemplateVariableRead])
async def list_template_variables(
    template_id: uuid.UUID,
    db: DbSession,
    _: AnyUser,
    settings: SettingsDep,
) -> list[TemplateVariableRead]:
    template = await get_template(db, template_id)
    variables = await list_variables(db, template_id)
    used = used_variable_names(await _source(template, settings))
    return [_variable_read(variable, used) for variable in variables]


@router.post(
    "/{template_id}/variables",
    response_model=TemplateVariableRead,
    status_code=201,
)
async def create_template_variable(
    template_id: uuid.UUID,
    payload: TemplateVariableWrite,
    db: DbSession,
    _: AdminUser,
    settings: SettingsDep,
) -> TemplateVariableRead:
    template = await get_template(db, template_id)
    used = used_variable_names(await _source(template, settings))
    variable = await create_variable(db, template_id, payload)
    return _variable_read(variable, used)


@router.put(
    "/{template_id}/variables/{variable_id}",
    response_model=TemplateVariableRead,
)
async def update_template_variable(
    template_id: uuid.UUID,
    variable_id: uuid.UUID,
    payload: TemplateVariableWrite,
    db: DbSession,
    _: AdminUser,
    settings: SettingsDep,
) -> TemplateVariableRead:
    template = await get_template(db, template_id)
    used = used_variable_names(await _source(template, settings))
    variable = await update_variable(db, template_id, variable_id, payload)
    return _variable_read(variable, used)


@router.delete("/{template_id}/variables/{variable_id}", status_code=204)
async def delete_template_variable(
    template_id: uuid.UUID,
    variable_id: uuid.UUID,
    db: DbSession,
    _: AdminUser,
    settings: SettingsDep,
) -> None:
    await get_template(db, template_id)
    await delete_variable(db, template_id, variable_id, settings)


@router.put(
    "/{template_id}/variables/{variable_id}/image",
    response_model=TemplateVariableImageRead,
)
async def upload_template_variable_image(
    template_id: uuid.UUID,
    variable_id: uuid.UUID,
    request: Request,
    db: DbSession,
    user: AdminUser,
    settings: SettingsDep,
) -> TemplateVariableImageRead:
    await get_template(db, template_id)
    variable = await get_variable(db, template_id, variable_id)
    upload = await _image_form(request, settings)
    try:
        filename = sanitize_image_filename(upload.filename)
        data = await read_image_upload(upload, settings.template_image_max_upload_bytes)
    finally:
        await upload.close()

    asset = await save_variable_image(
        db,
        variable=variable,
        uploader_id=user.id,
        settings=settings,
        filename=filename,
        data=data,
    )
    return TemplateVariableImageRead(
        filename=asset.original_filename,
        content_type=asset.content_type,
        size_bytes=asset.size_bytes,
        sha256=asset.sha256,
        updated_at=asset.updated_at,
    )


@router.get("/{template_id}/variables/{variable_id}/image")
async def download_template_variable_image(
    template_id: uuid.UUID,
    variable_id: uuid.UUID,
    db: DbSession,
    _: AdminUser,
    settings: SettingsDep,
) -> FileResponse:
    await get_template(db, template_id)
    variable = await get_variable(db, template_id, variable_id)
    if variable.asset is None:
        raise ApiError(404, "template_image_not_found", "This variable has no image")
    path = image_asset_path(settings, variable.asset)
    return FileResponse(
        path,
        media_type=variable.asset.content_type,
        filename=variable.asset.original_filename,
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.delete("/{template_id}/variables/{variable_id}/image", status_code=204)
async def delete_template_variable_image(
    template_id: uuid.UUID,
    variable_id: uuid.UUID,
    db: DbSession,
    _: AdminUser,
    settings: SettingsDep,
) -> None:
    await get_template(db, template_id)
    variable = await get_variable(db, template_id, variable_id)
    await delete_variable_asset(db, variable, settings)


@router.post("/{template_id}/preview", response_class=PlainTextResponse)
async def preview_template(
    template_id: uuid.UUID,
    payload: GenerateTemplateRequest,
    db: DbSession,
    _: AdminUser,
    settings: SettingsDep,
) -> PlainTextResponse:
    template = await get_template(db, template_id)
    variables = await list_variables(db, template_id)
    rendered, _snapshot = render_source(
        await _source(template, settings),
        variables,
        payload.values,
    )
    collect_assets(variables, settings)
    return PlainTextResponse(rendered, media_type="text/plain; charset=utf-8")


@router.post(
    "/{template_id}/generate",
    response_model=GeneratedDocumentRead,
    status_code=201,
)
async def generate_document(
    template_id: uuid.UUID,
    payload: GenerateTemplateRequest,
    db: DbSession,
    user: AnyUser,
    settings: SettingsDep,
) -> GeneratedDocumentRead:
    template = await get_template(db, template_id)
    variables = await list_variables(db, template_id)
    rendered, snapshot = render_source(
        await _source(template, settings),
        variables,
        payload.values,
    )
    assets = collect_assets(variables, settings)
    pdf = await compile_pdf(rendered, settings, assets)
    document = await save_document(
        db,
        template=template,
        uploader=user,
        values=snapshot,
        pdf=pdf,
        settings=settings,
    )
    return _document_read(document, user.email)


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
