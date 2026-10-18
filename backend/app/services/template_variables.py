from __future__ import annotations

import asyncio
import hashlib
import json
import re
import uuid
from collections.abc import Sequence
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import cast

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.datastructures import UploadFile

from app.config import Settings
from app.core.errors import ApiError
from app.models.template_variable import (
    TemplateVariable,
    TemplateVariableAsset,
    TemplateVariableKind,
    TemplateVariableValueType,
)
from app.schemas.template_variable import ProductRow, TemplateVariableWrite
from app.services.storage import delete_file, storage_path, write_atomic

MAX_TEXT_VALUE_LENGTH = 10_000
MAX_NUMBER_LENGTH = 64
MAX_PRODUCT_ROWS = 100
MAX_PRODUCT_DESIGNATION = 200
MAX_PRODUCT_POTS = 1_000_000
MAX_PRODUCT_PRICE = Decimal("1000000")
_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}

#: C0 controls except tab, newline and carriage return.
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_VARIABLE_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")

#: Jinja keywords and literals cannot be used as variable identifiers.
_JINJA_RESERVED = frozenset(
    {
        "and",
        "as",
        "autoescape",
        "block",
        "break",
        "call",
        "continue",
        "do",
        "elif",
        "else",
        "endautoescape",
        "endblock",
        "endcall",
        "endfilter",
        "endfor",
        "endif",
        "endmacro",
        "endraw",
        "endset",
        "endtrans",
        "endverbatim",
        "extends",
        "false",
        "filter",
        "for",
        "from",
        "if",
        "import",
        "in",
        "include",
        "is",
        "macro",
        "none",
        "not",
        "or",
        "pluralize",
        "raw",
        "set",
        "trans",
        "true",
        "verbatim",
        "while",
        "with",
        "without",
    }
)


def _invalid(field: str, message: str) -> ApiError:
    return ApiError(422, "template_variable_invalid", message, context={"field": field})


def validate_variable_name(raw_name: str) -> str:
    name = raw_name.strip()
    if not _VARIABLE_NAME.fullmatch(name) or name.lower() in _JINJA_RESERVED:
        raise _invalid(
            "name",
            "The variable name must be a Jinja identifier (letters, digits, underscore)",
        )
    return name


def validate_label(raw_label: str) -> str:
    label = " ".join(raw_label.split())
    if not label:
        raise _invalid("label", "The label is required")
    if _CONTROL_CHARS.search(raw_label):
        raise _invalid("label", "The label contains invalid characters")
    return label


def validate_description(raw_description: str | None) -> str | None:
    if raw_description is None:
        return None
    if _CONTROL_CHARS.search(raw_description):
        raise _invalid("description", "The description contains invalid characters")
    description = raw_description.strip()
    return description or None


def validate_value(
    raw_value: str | Sequence[ProductRow | dict[str, object]] | None,
    value_type: TemplateVariableValueType,
    *,
    required: bool,
) -> str | None:
    """Validate and normalize a static value or a local default."""

    if value_type is TemplateVariableValueType.IMAGE:
        if raw_value is not None:
            raise ApiError(
                422,
                "template_value_invalid",
                "Image variables do not take a text value",
                context={"field": "value"},
            )
        return None

    if raw_value is None:
        if required:
            raise ApiError(
                422,
                "template_value_invalid",
                "A static variable requires a value",
                context={"field": "value"},
            )
        return None

    if value_type is TemplateVariableValueType.PRODUCTS:
        if isinstance(raw_value, str):
            raise ApiError(
                422,
                "template_value_invalid",
                "The value must be a list of product rows",
                context={"field": "value"},
            )
        if not isinstance(raw_value, Sequence):
            raise ApiError(
                422,
                "template_value_invalid",
                "The value must be a list of product rows",
                context={"field": "value"},
            )
        rows = _normalize_product_rows(cast("Sequence[ProductRow | dict[str, object]]", raw_value))
        return json.dumps(rows, ensure_ascii=False, separators=(",", ":"))

    if not isinstance(raw_value, str):
        raise ApiError(
            422,
            "template_value_invalid",
            "The value must be a string",
            context={"field": "value"},
        )

    if _CONTROL_CHARS.search(raw_value):
        raise ApiError(
            422,
            "template_value_invalid",
            "The value contains invalid control characters",
            context={"field": "value"},
        )

    if value_type is TemplateVariableValueType.TEXT:
        if len(raw_value) > MAX_TEXT_VALUE_LENGTH:
            raise ApiError(
                422,
                "template_value_invalid",
                f"The value must be at most {MAX_TEXT_VALUE_LENGTH} characters",
                context={"field": "value"},
            )
        return raw_value

    stripped = raw_value.strip()
    if not stripped:
        raise ApiError(
            422,
            "template_value_invalid",
            "The value must not be blank",
            context={"field": "value"},
        )

    if value_type is TemplateVariableValueType.NUMBER:
        if len(stripped) > MAX_NUMBER_LENGTH:
            raise ApiError(
                422,
                "template_value_invalid",
                "The number is too long",
                context={"field": "value"},
            )
        normalized = stripped.replace(",", ".")
        try:
            number = Decimal(normalized)
        except InvalidOperation as exc:
            raise ApiError(
                422,
                "template_value_invalid",
                "The value must be a number",
                context={"field": "value"},
            ) from exc
        if not number.is_finite():
            raise ApiError(
                422,
                "template_value_invalid",
                "The number must be finite",
                context={"field": "value"},
            )
        return normalized

    try:
        parsed = date.fromisoformat(stripped)
    except ValueError as exc:
        raise ApiError(
            422,
            "template_value_invalid",
            "The value must be an ISO date (YYYY-MM-DD)",
            context={"field": "value"},
        ) from exc
    return parsed.isoformat()


def _normalize_product_rows(
    rows: Sequence[ProductRow | dict[str, object]],
) -> list[dict[str, object]]:
    if len(rows) > MAX_PRODUCT_ROWS:
        raise ApiError(
            422,
            "template_value_invalid",
            f"A products variable may contain at most {MAX_PRODUCT_ROWS} rows",
            context={"field": "value"},
        )

    normalized: list[dict[str, object]] = []
    for index, raw_row in enumerate(rows):
        try:
            row = raw_row if isinstance(raw_row, ProductRow) else ProductRow.model_validate(raw_row)
        except ValidationError as exc:
            raise ApiError(
                422,
                "template_value_invalid",
                "Each product row is invalid",
                context={"field": "value", "row": index},
            ) from exc
        designation = row.designation.strip()
        if not designation or _CONTROL_CHARS.search(row.designation):
            raise ApiError(
                422,
                "template_value_invalid",
                "Each product row needs a valid designation",
                context={"field": "value", "row": index},
            )
        if len(designation) > MAX_PRODUCT_DESIGNATION:
            raise ApiError(
                422,
                "template_value_invalid",
                f"Product designations must be at most {MAX_PRODUCT_DESIGNATION} characters",
                context={"field": "value", "row": index},
            )
        if not 0 <= row.pots <= MAX_PRODUCT_POTS:
            raise ApiError(
                422,
                "template_value_invalid",
                "Product quantities must be positive integers",
                context={"field": "value", "row": index},
            )

        price_text = row.prix.strip().replace(",", ".")
        try:
            price = Decimal(price_text)
        except InvalidOperation as exc:
            raise ApiError(
                422,
                "template_value_invalid",
                "Product prices must be numbers",
                context={"field": "value", "row": index},
            ) from exc
        if not price.is_finite() or price < 0 or price > MAX_PRODUCT_PRICE:
            raise ApiError(
                422,
                "template_value_invalid",
                "Product prices must be positive and finite",
                context={"field": "value", "row": index},
            )
        normalized.append(
            {
                "designation": designation,
                "pots": row.pots,
                "prix": str(price.quantize(Decimal("0.01"))),
            }
        )
    return normalized


def parse_product_rows(value: str | None) -> list[dict[str, object]] | None:
    """Read the JSON stored in a products variable; malformed data is rejected."""

    if value is None:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ApiError(
            422,
            "template_value_invalid",
            "The products value is not valid JSON",
        ) from exc
    if not isinstance(parsed, list):
        raise ApiError(
            422,
            "template_value_invalid",
            "The products value must be a list",
        )
    return parsed


def serialize_variable_value(
    variable: TemplateVariable,
) -> str | list[dict[str, object]] | None:
    """Value returned by the API: a list for products, a string otherwise."""

    if variable.value_type is TemplateVariableValueType.PRODUCTS:
        return parse_product_rows(variable.value)
    return variable.value


def sanitize_image_filename(raw: str | None) -> str:
    name = Path((raw or "").replace("\\", "/")).name
    name = _CONTROL_CHARS.sub("", name).strip()
    if not name or Path(name).suffix.lower() not in _IMAGE_EXTENSIONS:
        raise ApiError(
            415,
            "template_image_type_not_allowed",
            "Only .jpg, .jpeg and .png images are accepted",
        )
    return name[:255]


def detect_image(data: bytes) -> tuple[str, str]:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png", "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg", "image/jpeg"
    raise ApiError(
        415,
        "template_image_type_not_allowed",
        "Only JPEG and PNG images are accepted",
    )


async def read_image_upload(upload: UploadFile, max_bytes: int) -> bytes:
    data = await upload.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ApiError(
            413,
            "template_image_too_large",
            f"The image must be at most {max_bytes} bytes",
        )
    return data


async def save_variable_image(
    db: AsyncSession,
    *,
    variable: TemplateVariable,
    uploader_id: uuid.UUID,
    settings: Settings,
    filename: str,
    data: bytes,
) -> TemplateVariableAsset:
    if variable.value_type is not TemplateVariableValueType.IMAGE:
        raise ApiError(422, "template_variable_invalid", "This variable is not an image")
    if variable.kind is not TemplateVariableKind.STATIC:
        raise ApiError(422, "template_variable_invalid", "Image variables must be static")

    original_filename = sanitize_image_filename(filename)
    extension, content_type = detect_image(data)
    suffix = Path(original_filename).suffix.lower().lstrip(".")
    if (suffix == "jpeg" and extension != "jpg") or (suffix != "jpeg" and suffix != extension):
        raise ApiError(
            415,
            "template_image_type_not_allowed",
            "The image extension does not match its content",
        )
    if len(data) > settings.template_image_max_upload_bytes:
        raise ApiError(413, "template_image_too_large", "The image is too large")

    storage_key = f"{uuid.uuid4()}.{extension}"
    path = storage_path(settings.template_storage_dir / "assets", storage_key)
    await asyncio.to_thread(write_atomic, path, data)
    digest = hashlib.sha256(data).hexdigest()
    existing = variable.asset

    if existing is not None:
        previous_key = existing.storage_key
        existing.storage_key = storage_key
        existing.original_filename = original_filename
        existing.content_type = content_type
        existing.size_bytes = len(data)
        existing.sha256 = digest
        existing.uploaded_by_id = uploader_id
        try:
            await db.commit()
        except BaseException:
            await db.rollback()
            await asyncio.to_thread(delete_file, path)
            raise

        previous_path = storage_path(
            settings.template_storage_dir / "assets",
            previous_key,
        )
        await asyncio.to_thread(delete_file, previous_path)
        await db.refresh(existing)
        return existing

    asset = TemplateVariableAsset(
        variable_id=variable.id,
        storage_key=storage_key,
        original_filename=original_filename,
        content_type=content_type,
        size_bytes=len(data),
        sha256=digest,
        uploaded_by_id=uploader_id,
    )
    db.add(asset)
    try:
        await db.commit()
    except BaseException:
        await db.rollback()
        await asyncio.to_thread(delete_file, path)
        raise

    await db.refresh(asset)
    return asset


def image_asset_path(settings: Settings, asset: TemplateVariableAsset) -> Path:
    path = storage_path(settings.template_storage_dir / "assets", asset.storage_key)
    if not path.is_file():
        raise ApiError(404, "template_image_not_found", "The image file is missing")
    return path


async def delete_variable_asset(
    db: AsyncSession,
    variable: TemplateVariable,
    settings: Settings,
) -> bool:
    asset = variable.asset
    if asset is None:
        return False
    path = storage_path(settings.template_storage_dir / "assets", asset.storage_key)
    await db.delete(asset)
    await db.commit()
    await asyncio.to_thread(delete_file, path)
    return True


def _validated_fields(payload: TemplateVariableWrite) -> dict[str, object]:
    if (
        payload.value_type is TemplateVariableValueType.IMAGE
        and payload.kind is TemplateVariableKind.LOCAL
    ):
        raise _invalid("kind", "Image variables must be static")
    return {
        "name": validate_variable_name(payload.name),
        "label": validate_label(payload.label),
        "description": validate_description(payload.description),
        "kind": payload.kind,
        "value_type": payload.value_type,
        "value": validate_value(
            payload.value,
            payload.value_type,
            required=payload.kind is TemplateVariableKind.STATIC,
        ),
    }


async def list_variables(
    db: AsyncSession,
    template_id: uuid.UUID,
) -> list[TemplateVariable]:
    result = await db.scalars(
        select(TemplateVariable)
        .options(selectinload(TemplateVariable.asset))
        .where(TemplateVariable.template_id == template_id)
        .order_by(TemplateVariable.name)
    )
    return list(result)


async def _name_is_taken(
    db: AsyncSession,
    template_id: uuid.UUID,
    name: str,
    *,
    exclude_id: uuid.UUID | None = None,
) -> bool:
    query = select(TemplateVariable.id).where(
        TemplateVariable.template_id == template_id,
        TemplateVariable.name == name,
    )
    if exclude_id is not None:
        query = query.where(TemplateVariable.id != exclude_id)
    return await db.scalar(query) is not None


async def create_variable(
    db: AsyncSession,
    template_id: uuid.UUID,
    payload: TemplateVariableWrite,
) -> TemplateVariable:
    fields = _validated_fields(payload)
    name = str(fields["name"])
    if await _name_is_taken(db, template_id, name):
        raise ApiError(
            409,
            "template_variable_name_taken",
            "A variable with this name already exists on this template",
        )

    variable = TemplateVariable(template_id=template_id, **fields)
    db.add(variable)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ApiError(
            409,
            "template_variable_name_taken",
            "A variable with this name already exists on this template",
        ) from exc

    return await get_variable(db, template_id, variable.id)


async def get_variable(
    db: AsyncSession,
    template_id: uuid.UUID,
    variable_id: uuid.UUID,
) -> TemplateVariable:
    variable = await db.scalar(
        select(TemplateVariable)
        .options(selectinload(TemplateVariable.asset))
        .where(
            TemplateVariable.id == variable_id,
            TemplateVariable.template_id == template_id,
        )
    )
    if variable is None:
        raise ApiError(404, "template_variable_not_found", "Template variable not found")
    return variable


async def update_variable(
    db: AsyncSession,
    template_id: uuid.UUID,
    variable_id: uuid.UUID,
    payload: TemplateVariableWrite,
) -> TemplateVariable:
    variable = await get_variable(db, template_id, variable_id)
    fields = _validated_fields(payload)
    name = str(fields["name"])
    if name != variable.name and await _name_is_taken(
        db,
        template_id,
        name,
        exclude_id=variable_id,
    ):
        raise ApiError(
            409,
            "template_variable_name_taken",
            "A variable with this name already exists on this template",
        )

    for field, value in fields.items():
        setattr(variable, field, value)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ApiError(
            409,
            "template_variable_name_taken",
            "A variable with this name already exists on this template",
        ) from exc

    return await get_variable(db, template_id, variable.id)


async def delete_variable(
    db: AsyncSession,
    template_id: uuid.UUID,
    variable_id: uuid.UUID,
    settings: Settings,
) -> None:
    variable = await get_variable(db, template_id, variable_id)
    asset = variable.asset
    asset_path = (
        storage_path(settings.template_storage_dir / "assets", asset.storage_key)
        if asset is not None
        else None
    )
    await db.delete(variable)
    await db.commit()
    if asset_path is not None:
        await asyncio.to_thread(delete_file, asset_path)
