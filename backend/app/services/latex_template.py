from __future__ import annotations

import asyncio
import hashlib
import re
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import UploadFile

from app.config import Settings
from app.core.errors import ApiError
from app.models.latex_template import LatexTemplate
from app.models.user import User
from app.services.storage import delete_file, storage_path, write_atomic
from app.services.template_render import validate_template_syntax

ALLOWED_SUFFIX = ".tex"
MAX_NAME_LENGTH = 120
MAX_FILENAME_LENGTH = 255
#: Room for multipart boundaries and part headers when checking Content-Length.
MULTIPART_OVERHEAD_BYTES = 64 * 1024

#: C0 controls except tab, newline and carriage return.
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_filename(raw: str | None) -> str:
    """Keep the basename only: the uploaded name is metadata, never a path."""

    name = Path((raw or "").replace("\\", "/")).name
    name = _CONTROL_CHARS.sub("", name).strip()
    if not name or name in {".", ".."}:
        raise ApiError(422, "template_filename_invalid", "A file name is required")
    return name[:MAX_FILENAME_LENGTH]


def validate_extension(filename: str) -> None:
    if Path(filename).suffix.lower() != ALLOWED_SUFFIX:
        raise ApiError(
            415,
            "template_type_not_allowed",
            "Only .tex files are accepted",
        )


def normalize_name(raw_name: str, fallback_filename: str) -> str:
    """Return the display name, falling back to the file stem when blank."""

    candidate = raw_name if raw_name.strip() else Path(fallback_filename).stem
    if _CONTROL_CHARS.search(candidate):
        raise ApiError(422, "template_name_invalid", "The template name is invalid")
    name = " ".join(candidate.split())
    if not name:
        raise ApiError(422, "template_name_invalid", "A template name is required")
    if len(name) > MAX_NAME_LENGTH:
        raise ApiError(
            422,
            "template_name_invalid",
            f"The template name must be at most {MAX_NAME_LENGTH} characters",
        )
    return name


def name_key(name: str) -> str:
    """Case-insensitive uniqueness key."""

    return name.casefold()


def decode_template(data: bytes) -> str:
    """Validate the source and return it without a UTF-8 BOM."""

    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ApiError(
            422,
            "template_invalid_encoding",
            "The template must be UTF-8 text",
        ) from exc
    if _CONTROL_CHARS.search(text):
        raise ApiError(
            422,
            "template_invalid_content",
            "The template contains binary control characters",
        )
    if not text.strip():
        raise ApiError(422, "template_empty", "The template is empty")
    validate_template_syntax(text)
    return text


async def read_upload(upload: UploadFile, max_bytes: int) -> bytes:
    """Read one byte more than allowed, so oversized files fail without guessing."""

    data = await upload.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ApiError(
            413,
            "template_too_large",
            f"The file must be at most {max_bytes} bytes",
        )
    return data


async def template_name_is_taken(db: AsyncSession, key: str) -> bool:
    found = await db.scalar(select(LatexTemplate.id).where(LatexTemplate.name_key == key))
    return found is not None


async def save_template(
    db: AsyncSession,
    *,
    uploader: User,
    settings: Settings,
    filename: str,
    display_name: str,
    source: str,
) -> LatexTemplate:
    """Store the source on disk then commit its metadata."""

    key = name_key(display_name)
    if await template_name_is_taken(db, key):
        raise ApiError(
            409,
            "template_name_taken",
            "A template with this name already exists",
        )

    storage_key = f"{uuid.uuid4()}{ALLOWED_SUFFIX}"
    path = storage_path(settings.template_storage_dir, storage_key)
    data = source.encode("utf-8")
    await asyncio.to_thread(write_atomic, path, data)

    template = LatexTemplate(
        name=display_name,
        name_key=key,
        original_filename=filename,
        storage_key=storage_key,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        uploaded_by_id=uploader.id,
    )
    db.add(template)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        await asyncio.to_thread(delete_file, path)
        raise ApiError(
            409,
            "template_name_taken",
            "A template with this name already exists",
        ) from exc
    except BaseException:
        await db.rollback()
        await asyncio.to_thread(delete_file, path)
        raise

    await db.refresh(template)
    return template


async def list_templates(db: AsyncSession) -> list[tuple[LatexTemplate, str | None]]:
    rows = await db.execute(
        select(LatexTemplate, User.email)
        .outerjoin(User, LatexTemplate.uploaded_by_id == User.id)
        .order_by(LatexTemplate.name_key)
    )
    return [(template, email) for template, email in rows.all()]


async def get_template(db: AsyncSession, template_id: uuid.UUID) -> LatexTemplate:
    template = await db.get(LatexTemplate, template_id)
    if template is None:
        raise ApiError(404, "template_not_found", "Template not found")
    return template


def template_file_path(settings: Settings, template: LatexTemplate) -> Path:
    path = storage_path(settings.template_storage_dir, template.storage_key)
    if not path.is_file():
        raise ApiError(404, "template_file_missing", "The template file is missing from storage")
    return path


def download_filename(template: LatexTemplate) -> str:
    """Never let a stored name inject a header value."""

    cleaned = (
        template.original_filename.replace('"', "").replace("\r", "").replace("\n", "").strip()
    )
    return cleaned or "template.tex"
